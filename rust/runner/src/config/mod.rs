use crate::{args, log};
use as_any::AsAny;
use async_trait::async_trait;
use serde::{de::DeserializeOwned, Deserialize, Serialize};
use serde_yaml::Value;
use std::{any::Any, error::Error, fmt, fmt::Debug, path::Path, sync::Arc};
use toolshed_core as core;

pub type SafeError = Box<dyn Error + Send + Sync>;

#[macro_export]
macro_rules! config_override {
    ($args:expr, $field:ident, $env_var:expr) => {
        $args
            .$field
            .clone()
            .or_else(|| std::env::var($env_var).ok().and_then(|p| p.parse().ok()))
    };
}

pub trait Provider: Any + AsAny + Debug + Send + Sync {
    fn get(&self, key: &str) -> Option<core::Primitive> {
        let keys: Vec<&str> = key.split('.').collect();
        let serialized = self.serialized()?;
        let result = self.resolve(&serialized, &keys)?;
        match result {
            Value::Bool(b) => Some(core::Primitive::Bool(b)),
            Value::Number(num) => match num {
                n if n.is_f64() && !n.as_f64().unwrap().is_nan() => {
                    let f = n.as_f64().unwrap();
                    Some(core::Primitive::F64(f))
                }
                n if n.is_u64() => {
                    let u = n.as_u64().unwrap();
                    if u <= u32::MAX as u64 {
                        Some(core::Primitive::U32(u as u32))
                    } else {
                        Some(core::Primitive::U64(u))
                    }
                }
                n if n.is_i64() => {
                    let i = n.as_i64().unwrap();
                    if i >= i32::MAX as i64 || i <= i32::MIN as i64 {
                        Some(core::Primitive::I64(i))
                    } else {
                        Some(core::Primitive::I32(i as i32))
                    }
                }
                _ => None,
            },
            Value::String(string) => Some(core::Primitive::String(string)),
            _ => None,
        }
    }

    fn resolve(&self, current: &Value, keys: &[&str]) -> Option<Value> {
        if keys.is_empty() {
            return Some(current.clone());
        }
        match current {
            Value::Mapping(map) => map.get(keys[0]).and_then(|v| self.resolve(v, &keys[1..])),
            Value::Sequence(seq) => {
                if let Ok(idx) = keys[0].parse::<usize>() {
                    seq.get(idx).and_then(|v| self.resolve(v, &keys[1..]))
                } else {
                    None
                }
            }
            _ => None,
        }
    }

    fn set_log(&mut self, _level: log::Level) -> Result<(), SafeError> {
        Err("Not implemented".into())
    }

    fn serialized(&self) -> Option<Value>;
}

#[async_trait]
pub trait Factory<T>
where
    T: Provider + DeserializeOwned + 'static + Send + Sync,
{
    async fn from_yaml(args: args::SafeArgs) -> Result<Box<T>, SafeError> {
        let args = Arc::new(args);
        let yaml_result = Self::read_yaml(Arc::clone(&args)).await?;
        let config = Self::override_config(&args, yaml_result).await?;
        Ok(config)
    }

    fn log_level_override(args: &args::ArcSafeArgs) -> Result<Option<log::Level>, SafeError> {
        match args.log_level().or_else(|| std::env::var("LOG_LEVEL").ok()) {
            Some(lvl) => match serde_yaml::from_str::<log::Level>(&lvl) {
                Ok(level) => Ok(Some(level)),
                Err(e) => Err(Box::new(e)),
            },
            None => Ok(None),
        }
    }

    fn override_log(args: &args::ArcSafeArgs, config: &mut Box<T>) -> core::EmptyResult {
        if let Some(level) = Self::log_level_override(args)? {
            config.set_log(level)?;
        }
        Ok(())
    }

    async fn override_config(
        args: &args::ArcSafeArgs,
        mut config: Box<T>,
    ) -> Result<Box<T>, SafeError> {
        Self::override_log(args, &mut config)?;
        Ok(config)
    }

    async fn read_yaml(args: args::ArcSafeArgs) -> Result<Box<T>, SafeError> {
        let config_str = args.config();
        let path = Path::new(&config_str);
        if !path.exists() {
            return Err(format!("Path does not exist: {}", path.display()).into());
        }
        let file = std::fs::File::open(path)
            .map_err(|e| format!("Failed to open {}: {}", path.display(), e))?;
        let config: T = serde_yaml::from_reader(file)
            .map_err(|e| format!("Failed to parse YAML({}): {}", path.display(), e))?;
        Ok(Box::new(config))
    }
}

impl LogConfig {
    fn default_log_level() -> log::Level {
        log::Level::Info
    }

    fn default_log() -> Option<LogConfig> {
        Some(LogConfig {
            level: Self::default_log_level(),
        })
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct LogConfig {
    #[serde(default = "LogConfig::default_log_level")]
    pub level: log::Level,
}

impl fmt::Display for LogConfig {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", serde_yaml::to_string(&self).ok().unwrap())
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct BaseConfig {
    #[serde(default = "LogConfig::default_log")]
    pub log: Option<LogConfig>,
}

impl BaseConfig {
    pub fn log_level(&self) -> log::Level {
        self.log.as_ref().map(|log| log.level).unwrap()
    }
}

impl Provider for BaseConfig {
    fn serialized(&self) -> Option<Value> {
        serde_yaml::to_value(self.clone()).ok()
    }
}

impl fmt::Display for BaseConfig {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", serde_yaml::to_string(&self).ok().unwrap())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test::{
        data::{TEST_YAML0, TEST_YAML1},
        dummy::{DummyConfig, DummyConfig2},
        patch::Patch,
    };
    use guerrilla::{patch1, patch2, patch3};
    use mockall::mock;
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use toolshed_test as ttest;

    static PATCHES: Lazy<ttest::Patches> = Lazy::new(ttest::Patches::new);
    static SPY: Lazy<ttest::Spy> = Lazy::new(ttest::Spy::new);
    static TESTS: Lazy<ttest::Tests> = Lazy::new(|| ttest::Tests::new(&SPY, &PATCHES));

    mock! {
        #[derive(Debug)]
        pub ArgsProvider {}
        #[async_trait]
        impl args::Provider for ArgsProvider {
            fn config(&self) -> String;
            fn log_level(&self) -> Option<String>;
        }
    }

    struct DummyFactory;

    #[async_trait]
    impl Factory<DummyConfig> for DummyFactory {}

    async fn _read_yaml_test() -> Result<Box<DummyConfig>, SafeError> {
        let mut mock_args = MockArgsProvider::new();
        mock_args
            .expect_config()
            .returning(|| "tests/config.yaml".to_string());
        mock_args.expect_log_level().returning(|| None);
        let args_boxed: args::SafeArgs = Box::new(mock_args);
        DummyFactory::read_yaml(Arc::new(args_boxed)).await
    }

    // TESTS

    #[test]
    fn test_logconfig_yaml() {
        let yaml = "
level: warning
        ";
        let config = serde_yaml::from_str::<LogConfig>(yaml).expect("Unable to parse yaml");
        let display = format!("{}", config);
        assert_eq!(display.trim(), yaml.trim());
        assert_eq!(config.level, log::Level::Warning);
    }

    #[test]
    fn test_logconfig_yaml_default() {
        let yaml = "
        ";
        let expected = "
level: info
        ";
        let config = serde_yaml::from_str::<LogConfig>(yaml).expect("Unable to parse yaml");
        let display = format!("{}", config);
        assert_eq!(display.trim(), expected.trim());
        assert_eq!(config.level, log::Level::Info);
    }

    #[test]
    fn test_baseconfig_yaml() {
        let yaml = "
log:
  level: error
        ";
        let config = serde_yaml::from_str::<BaseConfig>(yaml).expect("Unable to parse yaml");
        let display = format!("{}", config);
        assert_eq!(display.trim(), yaml.trim());
        assert_eq!(config.log.unwrap().level, log::Level::Error);
    }

    #[test]
    fn test_baseconfig_yaml_default() {
        let config = serde_yaml::from_str::<BaseConfig>("").expect("Unable to parse yaml");
        assert_eq!(config.log.as_ref().unwrap().level, log::Level::Info);
        assert_eq!(config.log_level(), log::Level::Info);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_baseconfig_serialized() {
        let test = TESTS
            .test("baseconfig_serialized")
            .expecting(vec![
                "serde_yaml::to_value(true): BaseConfig { log: Some(LogConfig { level: Info }) }",
            ])
            .with_patches(vec![patch1(serde_yaml::to_value::<BaseConfig>, |thing| {
                Patch::serde_to_value(TESTS.get("baseconfig_serialized"), Box::new(thing))
            })]);
        defer! {
            test.drop()
        }

        let config = serde_yaml::from_str::<BaseConfig>("").expect("Unable to parse yaml");
        let result = config.serialized();
        assert_eq!(result, Some(serde_yaml::from_str("SERIALIZED").unwrap()));
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_factory_from_yaml() {
        let test = TESTS.test("from_yaml")
            .expecting(vec![
                "Config::read_yaml(true): MockArgsProvider",
                "Config::override_config(true): MockArgsProvider, DummyConfig { log: LogConfig { level: Trace } }"])
            .with_patches(vec![
                patch1(DummyFactory::read_yaml, |args| {
                    Box::pin(Patch::read_yaml(TESTS.get("from_yaml"), args))
                }),
                patch2(DummyFactory::override_config, |args, config| {
                    Box::pin(Patch::override_config(TESTS.get("from_yaml"), args, config))
                }),
            ]);
        defer! {
            test.drop()
        }

        let mut mock_args = MockArgsProvider::new();
        mock_args
            .expect_config()
            .returning(|| "tests/config.yaml".to_string());
        mock_args.expect_log_level().returning(|| None);
        let args_boxed: args::SafeArgs = Box::new(mock_args);
        let result: Result<Box<DummyConfig>, SafeError> = DummyFactory::from_yaml(args_boxed).await;
        assert!(result.is_ok());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_factory_log_level_override_arg() {
        let test = TESTS
            .test("factory_log_level_override_arg")
            .expecting(vec!["serde_yaml::from_str(true): \"debug\""])
            .with_patches(vec![
                patch1(std::env::var, |name| {
                    Patch::env_var(TESTS.get("factory_log_level_override_arg"), name)
                }),
                patch1(serde_yaml::from_str::<log::Level>, |string| {
                    Patch::serde_from_str::<DummyConfig>(
                        TESTS.get("factory_log_level_override_arg"),
                        string,
                    )
                }),
            ]);
        defer! {
            test.drop()
        }

        let mut mock_args = MockArgsProvider::new();
        mock_args
            .expect_log_level()
            .returning(|| Some("debug".to_string()));
        let args_boxed: args::SafeArgs = Box::new(mock_args);
        let result = DummyFactory::log_level_override(&Arc::new(args_boxed));
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), Some(log::Level::Trace));
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_factory_log_level_override_env() {
        let test = TESTS
            .test("factory_log_level_override_env")
            .expecting(vec![
                "std::env::var(true): \"LOG_LEVEL\"",
                "serde_yaml::from_str(true): \"info\"",
            ])
            .with_patches(vec![
                patch1(std::env::var, |name| {
                    Patch::env_var(TESTS.get("factory_log_level_override_env"), name)
                }),
                patch1(serde_yaml::from_str::<log::Level>, |string| {
                    Patch::serde_from_str::<DummyConfig>(
                        TESTS.get("factory_log_level_override_env"),
                        string,
                    )
                }),
            ]);
        defer! {
            test.drop()
        }

        let mut mock_args = MockArgsProvider::new();
        mock_args.expect_log_level().returning(|| None);
        let args_boxed: args::SafeArgs = Box::new(mock_args);
        let result = DummyFactory::log_level_override(&Arc::new(args_boxed));
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), Some(log::Level::Trace));
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_factory_log_level_override_none() {
        let test = TESTS
            .test("factory_log_level_override_none")
            .expecting(vec!["std::env::var(false): \"LOG_LEVEL\""])
            .with_patches(vec![
                patch1(std::env::var, |name| {
                    let test = TESTS.get("factory_log_level_override_none");
                    test.lock().unwrap().fail();
                    Patch::env_var(test, name)
                }),
                patch1(serde_yaml::from_str::<log::Level>, |string| {
                    Patch::serde_from_str::<DummyConfig>(
                        TESTS.get("factory_log_level_override_none"),
                        string,
                    )
                }),
            ]);
        defer! {
            test.drop()
        }

        let mut mock_args = MockArgsProvider::new();
        mock_args.expect_log_level().returning(|| None);
        let args_boxed: args::SafeArgs = Box::new(mock_args);
        let result = DummyFactory::log_level_override(&Arc::new(args_boxed));
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), None);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_factory_log_level_override_err() {
        let test = TESTS
            .test("factory_log_level_override_err")
            .expecting(vec![
                "std::env::var(true): \"LOG_LEVEL\"",
                "serde_yaml::from_str(false): \"info\"",
            ])
            .with_patches(vec![
                patch1(std::env::var, |name| {
                    Patch::env_var(TESTS.get("factory_log_level_override_err"), name)
                }),
                patch1(serde_yaml::from_str::<log::Level>, |string| {
                    let test = TESTS.get("factory_log_level_override_err");
                    test.lock().unwrap().fail();
                    Patch::serde_from_str::<DummyConfig>(test, string)
                }),
            ]);
        defer! {
            test.drop()
        }

        let mut mock_args = MockArgsProvider::new();
        mock_args.expect_log_level().returning(|| None);
        let args_boxed: args::SafeArgs = Box::new(mock_args);
        let result = DummyFactory::log_level_override(&Arc::new(args_boxed));
        assert!(result.is_err());
        let err_msg = result.unwrap_err().to_string();
        assert!(
            err_msg.contains("invalid type: string \"invalid\", expected i32"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_factory_override_config() {
        let test = TESTS
            .test("factory_override_config")
            .expecting(vec![
                "Factory::log_level_override(true/true): MockArgsProvider",
                "Config::set_log(true): Trace",
            ])
            .with_patches(vec![
                patch1(DummyFactory::log_level_override, |args| {
                    Ok(Patch::log_level_override(
                        TESTS.get("factory_override_config"),
                        true,
                        args,
                    )?)
                }),
                patch2(DummyConfig::set_log, |_self, level| {
                    Patch::set_log(TESTS.get("factory_override_config"), _self, level)
                }),
            ]);
        defer! {
            test.drop()
        }

        let mock_args = MockArgsProvider::new();
        let args_boxed: args::SafeArgs = Box::new(mock_args);
        let config: DummyConfig = serde_yaml::from_str(TEST_YAML0).expect("Unable to parse yaml");
        assert!(
            DummyFactory::override_config(&Arc::new(args_boxed), Box::new(config))
                .await
                .is_ok()
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_factory_override_nolog() {
        let test = TESTS
            .test("factory_override_nolog")
            .expecting(vec![
                "Factory::log_level_override(true/false): MockArgsProvider",
            ])
            .with_patches(vec![
                patch1(DummyFactory::log_level_override, |args| {
                    Ok(Patch::log_level_override(
                        TESTS.get("factory_override_nolog"),
                        false,
                        args,
                    )?)
                }),
                patch2(DummyConfig::set_log, |_self, level| {
                    Patch::set_log(TESTS.get("factory_override_nolog"), _self, level)
                }),
            ]);
        defer! {
            test.drop()
        }

        let mock_args = MockArgsProvider::new();
        let args_boxed: args::SafeArgs = Box::new(mock_args);
        let config: DummyConfig = serde_yaml::from_str(TEST_YAML0).expect("Unable to parse yaml");
        assert!(
            DummyFactory::override_config(&Arc::new(args_boxed), Box::new(config))
                .await
                .is_ok()
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_factory_override_get_err() {
        let test = TESTS
            .test("factory_override_get_err")
            .expecting(vec![
                "Factory::log_level_override(false/true): MockArgsProvider",
            ])
            .with_patches(vec![
                patch1(DummyFactory::log_level_override, |args| {
                    let test = TESTS.get("factory_override_get_err");
                    test.lock().unwrap().fail();
                    Patch::log_level_override(test, true, args)
                }),
                patch2(DummyConfig::set_log, |_self, level| {
                    Patch::set_log(TESTS.get("factory_override_get_err"), _self, level)
                }),
            ]);
        defer! {
            test.drop()
        }

        let mock_args = MockArgsProvider::new();
        let args_boxed: args::SafeArgs = Box::new(mock_args);
        let config: DummyConfig = serde_yaml::from_str(TEST_YAML0).expect("Unable to parse yaml");
        let result = DummyFactory::override_config(&Arc::new(args_boxed), Box::new(config)).await;
        assert!(result.is_err());
        let err_msg = result.unwrap_err().to_string();
        assert!(
            err_msg.contains("Failed getting log level override"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_factory_override_set_err() {
        let test = TESTS
            .test("factory_override_set_err")
            .expecting(vec![
                "Factory::log_level_override(true/true): MockArgsProvider",
                "Config::set_log(false): Trace",
            ])
            .with_patches(vec![
                patch1(DummyFactory::log_level_override, |args| {
                    Patch::log_level_override(TESTS.get("factory_override_set_err"), true, args)
                }),
                patch2(DummyConfig::set_log, |_self, level| {
                    let test = TESTS.get("factory_override_set_err");
                    test.lock().unwrap().fail();
                    Patch::set_log(test, _self, level)
                }),
            ]);
        defer! {
            test.drop()
        }

        let mock_args = MockArgsProvider::new();
        let args_boxed: args::SafeArgs = Box::new(mock_args);
        let config: DummyConfig = serde_yaml::from_str(TEST_YAML0).expect("Unable to parse yaml");
        let result = DummyFactory::override_config(&Arc::new(args_boxed), Box::new(config)).await;
        assert!(result.is_err());
        let err_msg = result.unwrap_err().to_string();
        assert!(
            err_msg.contains("Error setting log"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_factory_read_yaml() {
        let test = TESTS
            .test("read_yaml")
            .expecting(vec![
                "Path.exists(true): \"tests/config.yaml\"",
                "File::open(true): \"tests/config.yaml\"",
                "serde_yaml::from_reader(true): true",
            ])
            .with_patches(vec![
                patch1(Path::exists, |_self| {
                    Patch::path_exists(TESTS.get("read_yaml"), _self)
                }),
                patch1(std::fs::File::open, |path| {
                    Patch::file_open(TESTS.get("read_yaml"), path)
                }),
                patch1(
                    serde_yaml::from_reader::<std::fs::File, DummyConfig>,
                    |file| Patch::serde_from_reader(TESTS.get("read_yaml"), &file),
                ),
            ]);
        defer! {
            test.drop()
        }

        let result = _read_yaml_test().await;
        assert!(result.is_ok());
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_factory_read_yaml_no_exist() {
        let test = TESTS
            .test("read_yaml_no_exist")
            .expecting(vec!["Path.exists(false): \"tests/config.yaml\""])
            .with_patches(vec![
                patch1(Path::exists, |_self| {
                    let test = TESTS.get("read_yaml_no_exist");
                    test.lock().unwrap().fail();
                    Patch::path_exists(test, _self)
                }),
                patch1(std::fs::File::open, |path| {
                    Patch::file_open(TESTS.get("read_yaml_no_exist"), path)
                }),
                patch1(
                    serde_yaml::from_reader::<std::fs::File, DummyConfig>,
                    |file| Patch::serde_from_reader(TESTS.get("read_yaml_no_exist"), &file),
                ),
            ]);
        defer! {
            test.drop()
        }

        let result = _read_yaml_test().await;
        assert!(result.is_err());
        let err_msg = result.unwrap_err().to_string();
        assert!(
            err_msg.contains("Path does not exist"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_factory_read_yaml_fail_open() {
        let test = TESTS
            .test("read_yaml_fail_open")
            .expecting(vec![
                "Path.exists(true): \"tests/config.yaml\"",
                "File::open(false): \"tests/config.yaml\"",
            ])
            .with_patches(vec![
                patch1(Path::exists, |_self| {
                    Patch::path_exists(TESTS.get("read_yaml_fail_open"), _self)
                }),
                patch1(std::fs::File::open, |path| {
                    let test = TESTS.get("read_yaml_fail_open");
                    test.lock().unwrap().fail();
                    Patch::file_open(test, path)
                }),
                patch1(
                    serde_yaml::from_reader::<std::fs::File, DummyConfig>,
                    |file| Patch::serde_from_reader(TESTS.get("read_yaml_fail_open"), &file),
                ),
            ]);
        defer! {
            test.drop()
        }

        let result = _read_yaml_test().await;
        assert!(result.is_err());
        let err_msg = result.unwrap_err().to_string();
        assert!(
            err_msg.contains("Some error message"),
            "Unexpected error: {}",
            err_msg
        );
        assert!(
            err_msg.contains("Failed to open"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_factory_read_yaml_bad_parse() {
        let test = TESTS
            .test("read_yaml_bad_parse")
            .expecting(vec![
                "Path.exists(true): \"tests/config.yaml\"",
                "File::open(true): \"tests/config.yaml\"",
                "serde_yaml::from_reader(false): true",
            ])
            .with_patches(vec![
                patch1(Path::exists, |_self| {
                    Patch::path_exists(TESTS.get("read_yaml_bad_parse"), _self)
                }),
                patch1(std::fs::File::open, |path| {
                    Patch::file_open(TESTS.get("read_yaml_bad_parse"), path)
                }),
                patch1(
                    serde_yaml::from_reader::<std::fs::File, DummyConfig>,
                    |file| {
                        let test = TESTS.get("read_yaml_bad_parse");
                        test.lock().unwrap().fail();
                        Patch::serde_from_reader(test, &file)
                    },
                ),
            ]);
        defer! {
            test.drop()
        }

        let result = _read_yaml_test().await;
        assert!(result.is_err());
        let err_msg = result.unwrap_err().to_string();
        assert!(
            err_msg.contains("Failed to parse YAML"),
            "Unexpected error: {}",
            err_msg
        );
        assert!(
            err_msg.contains("invalid type: string \"invalid\", expected i32"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_provider_get() {
        let test = TESTS
            .test("read_provider_get")
            .expecting(vec![
                "Provider::serialized(true)",
                "Provider::resolve(true): [\"SOME\", \"KEY\", \"PATH\"] String(\"SERIALIZED\")",
            ])
            .with_patches(vec![
                patch3(DummyConfig2::resolve, |_self, current, keys| {
                    Patch::config_resolve(TESTS.get("read_provider_get"), _self, current, keys)
                }),
                patch1(DummyConfig2::serialized, |_self| {
                    Patch::config_serialized(TESTS.get("read_provider_get"), _self)
                }),
            ]);
        defer! {
            test.drop()
        }

        let provider = DummyConfig2 {
            log: LogConfig {
                level: log::Level::Trace,
            },
        };

        if let Some(core::Primitive::String(result)) = provider.get("SOME.KEY.PATH") {
            assert_eq!(result, "RESOLVED");
        } else {
            panic!("Expected a Primitive::String, but got something else.");
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_provider_get_f64() {
        let test = TESTS
            .test("read_provider_get_f64")
            .expecting(vec![
                "Provider::serialized(true)",
                "Provider::resolve(true): [\"SOME\", \"KEY\", \"PATH\"] String(\"SERIALIZED\")",
            ])
            .with_patches(vec![
                patch3(DummyConfig2::resolve, |_self, current, keys| {
                    Patch::config_resolve_f64(
                        TESTS.get("read_provider_get_f64"),
                        _self,
                        current,
                        keys,
                    )
                }),
                patch1(DummyConfig2::serialized, |_self| {
                    Patch::config_serialized(TESTS.get("read_provider_get_f64"), _self)
                }),
            ]);
        defer! {
            test.drop()
        }

        let provider = DummyConfig2 {
            log: LogConfig {
                level: log::Level::Trace,
            },
        };

        if let Some(core::Primitive::F64(result)) = provider.get("SOME.KEY.PATH") {
            assert_eq!(result, 23.23);
        } else {
            panic!("Expected a Primitive::F64, but got something else.");
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_provider_get_i32() {
        let test = TESTS
            .test("read_provider_get_i32")
            .expecting(vec![
                "Provider::serialized(true)",
                "Provider::resolve(true): [\"SOME\", \"KEY\", \"PATH\"] String(\"SERIALIZED\")",
            ])
            .with_patches(vec![
                patch3(DummyConfig2::resolve, |_self, current, keys| {
                    Patch::config_resolve_i32(
                        TESTS.get("read_provider_get_i32"),
                        _self,
                        current,
                        keys,
                    )
                }),
                patch1(DummyConfig2::serialized, |_self| {
                    Patch::config_serialized(TESTS.get("read_provider_get_i32"), _self)
                }),
            ]);
        defer! {
            test.drop()
        }

        let provider = DummyConfig2 {
            log: LogConfig {
                level: log::Level::Trace,
            },
        };

        let result = provider.get("SOME.KEY.PATH");
        if let Some(core::Primitive::I32(result)) = result {
            assert_eq!(result, -23);
        } else {
            panic!(
                "Expected a Primitive::I32, but got something else. {:?}",
                result
            );
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_provider_get_i64() {
        let test = TESTS
            .test("read_provider_get_i64")
            .expecting(vec![
                "Provider::serialized(true)",
                "Provider::resolve(true): [\"SOME\", \"KEY\", \"PATH\"] String(\"SERIALIZED\")",
            ])
            .with_patches(vec![
                patch3(DummyConfig2::resolve, |_self, current, keys| {
                    Patch::config_resolve_i64(
                        TESTS.get("read_provider_get_i64"),
                        _self,
                        current,
                        keys,
                    )
                }),
                patch1(DummyConfig2::serialized, |_self| {
                    Patch::config_serialized(TESTS.get("read_provider_get_i64"), _self)
                }),
            ]);
        defer! {
            test.drop()
        }

        let provider = DummyConfig2 {
            log: LogConfig {
                level: log::Level::Trace,
            },
        };

        let result = provider.get("SOME.KEY.PATH");
        if let Some(core::Primitive::I64(result)) = result {
            assert_eq!(result, -2323232323);
        } else {
            panic!(
                "Expected a Primitive::I64, but got something else. {:?}",
                result
            );
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_provider_get_u32() {
        let test = TESTS
            .test("read_provider_get_u32")
            .expecting(vec![
                "Provider::serialized(true)",
                "Provider::resolve(true): [\"SOME\", \"KEY\", \"PATH\"] String(\"SERIALIZED\")",
            ])
            .with_patches(vec![
                patch3(DummyConfig2::resolve, |_self, current, keys| {
                    Patch::config_resolve_u32(
                        TESTS.get("read_provider_get_u32"),
                        _self,
                        current,
                        keys,
                    )
                }),
                patch1(DummyConfig2::serialized, |_self| {
                    Patch::config_serialized(TESTS.get("read_provider_get_u32"), _self)
                }),
            ]);
        defer! {
            test.drop()
        }

        let provider = DummyConfig2 {
            log: LogConfig {
                level: log::Level::Trace,
            },
        };

        let result = provider.get("SOME.KEY.PATH");
        if let Some(core::Primitive::U32(result)) = result {
            assert_eq!(result, 23);
        } else {
            panic!(
                "Expected a Primitive::U32, but got something else. {:?}",
                result
            );
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_provider_get_u64() {
        let test = TESTS
            .test("read_provider_get_u64")
            .expecting(vec![
                "Provider::serialized(true)",
                "Provider::resolve(true): [\"SOME\", \"KEY\", \"PATH\"] String(\"SERIALIZED\")",
            ])
            .with_patches(vec![
                patch3(DummyConfig2::resolve, |_self, current, keys| {
                    Patch::config_resolve_u64(
                        TESTS.get("read_provider_get_u64"),
                        _self,
                        current,
                        keys,
                    )
                }),
                patch1(DummyConfig2::serialized, |_self| {
                    Patch::config_serialized(TESTS.get("read_provider_get_u64"), _self)
                }),
            ]);
        defer! {
            test.drop()
        }

        let provider = DummyConfig2 {
            log: LogConfig {
                level: log::Level::Trace,
            },
        };

        let result = provider.get("SOME.KEY.PATH");
        if let Some(core::Primitive::U64(result)) = result {
            assert_eq!(result, 232323232323);
        } else {
            panic!(
                "Expected a Primitive::U64, but got something else. {:?}",
                result
            );
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_provider_get_bool() {
        let test = TESTS
            .test("read_provider_get_bool")
            .expecting(vec![
                "Provider::serialized(true)",
                "Provider::resolve(true): [\"SOME\", \"KEY\", \"PATH\"] String(\"SERIALIZED\")",
            ])
            .with_patches(vec![
                patch3(DummyConfig2::resolve, |_self, current, keys| {
                    Patch::config_resolve_bool(
                        TESTS.get("read_provider_get_bool"),
                        _self,
                        current,
                        keys,
                    )
                }),
                patch1(DummyConfig2::serialized, |_self| {
                    Patch::config_serialized(TESTS.get("read_provider_get_bool"), _self)
                }),
            ]);
        defer! {
            test.drop()
        }

        let provider = DummyConfig2 {
            log: LogConfig {
                level: log::Level::Trace,
            },
        };

        let result = provider.get("SOME.KEY.PATH");
        if let Some(core::Primitive::Bool(result)) = result {
            assert!(result);
        } else {
            panic!(
                "Expected a Primitive::Bool, but got something else. {:?}",
                result
            );
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_provider_get_bad() {
        let test = TESTS
            .test("read_provider_get_bad")
            .expecting(vec![
                "Provider::serialized(true)",
                "Provider::resolve(true): [\"SOME\", \"KEY\", \"PATH\"] String(\"SERIALIZED\")",
            ])
            .with_patches(vec![
                patch3(DummyConfig2::resolve, |_self, current, keys| {
                    Patch::config_resolve_bad(
                        TESTS.get("read_provider_get_bad"),
                        _self,
                        current,
                        keys,
                    )
                }),
                patch1(DummyConfig2::serialized, |_self| {
                    Patch::config_serialized(TESTS.get("read_provider_get_bad"), _self)
                }),
            ]);
        defer! {
            test.drop()
        }

        let provider = DummyConfig2 {
            log: LogConfig {
                level: log::Level::Trace,
            },
        };

        let result = provider.get("SOME.KEY.PATH");
        assert!(result.is_none(), "Expected None but got {:?}", result);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_provider_get_bad_type() {
        let test = TESTS
            .test("read_provider_get_bad_type")
            .expecting(vec![
                "Provider::serialized(true)",
                "Provider::resolve(true): [\"SOME\", \"KEY\", \"PATH\"] String(\"SERIALIZED\")",
            ])
            .with_patches(vec![
                patch3(DummyConfig2::resolve, |_self, current, keys| {
                    Patch::config_resolve_bad_type(
                        TESTS.get("read_provider_get_bad_type"),
                        _self,
                        current,
                        keys,
                    )
                }),
                patch1(DummyConfig2::serialized, |_self| {
                    Patch::config_serialized(TESTS.get("read_provider_get_bad_type"), _self)
                }),
            ]);
        defer! {
            test.drop()
        }

        let provider = DummyConfig2 {
            log: LogConfig {
                level: log::Level::Trace,
            },
        };

        let result = provider.get("SOME.KEY.PATH");
        assert!(result.is_none(), "Expected None but got {:?}", result);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_provider_resolve() {
        let provider = DummyConfig2 {
            log: LogConfig {
                level: log::Level::Trace,
            },
        };

        let tests = vec![
            (
                TEST_YAML0.to_string(),
                "log.level".to_string(),
                "trace".to_string(),
            ),
            (
                TEST_YAML1.to_string(),
                "dict0.subdict0.key0".to_string(),
                "value0".to_string(),
            ),
            (
                TEST_YAML1.to_string(),
                "dict0.list0.1.dictitem0.key1".to_string(),
                "value1".to_string(),
            ),
            (
                TEST_YAML1.to_string(),
                "dict0.list0.1.dictitem0.key1.does.not.exist".to_string(),
                "".to_string(),
            ),
            (
                TEST_YAML1.to_string(),
                "dict0.list0.10000".to_string(),
                "".to_string(),
            ),
            (
                TEST_YAML1.to_string(),
                "dict0.list0.NaN".to_string(),
                "".to_string(),
            ),
        ];

        for (yaml, key, expected) in tests {
            let config: serde_yaml::Value =
                serde_yaml::from_str(&yaml).expect("Unable to parse yaml");
            let keys: Vec<&str> = key.split('.').collect();
            let resolved = provider.resolve(&config, &keys);
            if expected == *"".to_string() {
                assert_eq!(resolved, None);
            } else {
                assert_eq!(resolved.unwrap().as_str().unwrap(), expected.as_str());
            }
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_provider_set_log() {
        let mut provider = DummyConfig2 {
            log: LogConfig {
                level: log::Level::Trace,
            },
        };
        let result = provider.set_log(log::Level::Warning);
        assert!(result.is_err());
        let err_msg = result.unwrap_err().to_string();
        assert!(
            err_msg.contains("Not implemented"),
            "Unexpected error: {}",
            err_msg
        );
    }
}
