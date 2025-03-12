use crate::{args::Args, listener};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_yaml::Value;
use toolshed_runner::{config, log, EmptyResult};

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct Config {
    #[serde(flatten)]
    pub base: config::BaseConfig,
    #[serde(default = "listener::Config::default_listener")]
    pub listener: listener::Config,
}

#[async_trait]
impl config::Factory<Config> for Config {
    async fn override_config(
        args: config::ArcSafeArgs,
        mut config: Box<Config>,
    ) -> Result<Box<Config>, config::SafeError> {
        Self::override_config_log(args.clone(), &mut config)?;
        Self::override_config_listener(args, &mut config)?;
        Ok(config)
    }
}

impl config::Provider for Config {
    fn serialized(&self) -> Option<Value> {
        serde_yaml::to_value(self.clone()).ok()
    }

    fn set_log(&mut self, level: log::Level) -> EmptyResult {
        if let Some(log) = self.base.log.as_mut() {
            log.level = level;
        }
        Ok(())
    }
}

impl Config {
    fn override_config_listener(args: config::ArcSafeArgs, config: &mut Box<Self>) -> EmptyResult {
        if let Some(args) = args.as_any().downcast_ref::<Args>() {
            if let Some(host) = args.host.clone() {
                config.listener.host = host.parse()?;
            }
            if let Some(port) = args.port {
                config.listener.port = port;
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test::patch::Patch;
    use as_any::AsAny;
    use guerrilla::{patch0, patch1, patch2};
    use mockall::mock;
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use std::{any::Any, net::IpAddr, sync::Arc};
    use toolshed_runner::{
        args,
        config::{Factory as _, Provider as _},
        test::{
            patch::{Patch as RunnerPatch, Patches},
            spy::Spy,
            Tests,
        },
    };

    static PATCHES: Lazy<Patches> = Lazy::new(Patches::new);
    static SPY: Lazy<Spy> = Lazy::new(Spy::new);
    static TESTS: Lazy<Tests> = Lazy::new(|| Tests::new(&SPY, &PATCHES));

    mock! {
        #[derive(Clone, Debug, Parser, PartialEq)]
        pub ArgsProvider {}
        #[async_trait]
        impl args::Provider for ArgsProvider {
            fn config(&self) -> String;
            fn log_level(&self) -> Option<String>;
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_default() {
        let test = TESTS
            .test("config_default")
            .expecting(vec!["listener::Config::default_listener(true)"])
            .with_patches(vec![patch0(listener::Config::default_listener, || {
                Patch::default_listener(TESTS.get("config_default").unwrap())
            })]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        assert_eq!(config.base.log.as_ref().unwrap().level, log::Level::Info);
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_config_override() {
        let test = TESTS.test("config_override")
            .expecting(vec![
                "listener::Config::default_listener(true)",
                "Config::override_config_log(true): MockArgsProvider, Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listener: Config { host: 7.7.7.7, port: 2323 } }",
                "Config::override_config_listener(true): MockArgsProvider, Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listener: Config { host: 7.7.7.7, port: 2323 } }"])
            .with_patches(vec![
            patch0(listener::Config::default_listener, || {
                Patch::default_listener(TESTS.get("config_override").unwrap())
            }),
            patch2(Config::override_config_log, |args, config| {
                RunnerPatch::override_config_log(TESTS.get("config_override").unwrap(), args, config)

            }),
            patch2(Config::override_config_listener, |args, config| {
                Patch::override_config_listener(TESTS.get("config_override").unwrap(), args, config)
            }),

            ]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let mut mock_args = MockArgsProvider::new();
        mock_args.expect_log_level().returning(|| None);
        let args_boxed: config::SafeArgs = Box::new(mock_args);
        let result = Config::override_config(Arc::new(args_boxed), Box::new(config)).await;
        assert!(result.is_ok());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_serialized() {
        let test = TESTS.test("config_serialized")
            .expecting(vec![
                "serde_yaml::to_value(true): Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listener: Config { host: 127.0.0.1, port: 8787 } }"])
            .with_patches(vec![patch1(serde_yaml::to_value::<Config>, |thing| {
                RunnerPatch::serde_to_value(TESTS.get("config_serialized").unwrap(), Box::new(thing))
            })]);
        defer! {
            test.drop();
        }

        let config = &mut serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        assert_eq!(
            config.serialized(),
            Some(serde_yaml::Value::String("SERIALIZED".to_string()))
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_set_log() {
        let test = TESTS
            .test("config_set_log")
            .expecting(vec!["listener::Config::default_listener(true)"])
            .with_patches(vec![patch0(listener::Config::default_listener, || {
                Patch::default_listener(TESTS.get("config_set_log").unwrap())
            })]);
        defer! {
            test.drop();
        }

        let config = &mut serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let result = config.set_log(log::Level::Trace);
        assert!(result.is_ok());
        assert_eq!(config.base.log.as_ref().unwrap().level, log::Level::Trace);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_config_listener() {
        let test = TESTS
            .test("config_override_config_listener")
            .expecting(vec![
                "listener::Config::default_listener(true)",
                "Args::as_any(true)",
                "Any::downcast_ref::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(listener::Config::default_listener, || {
                    Patch::default_listener(TESTS.get("config_override_config_listener").unwrap())
                }),
                patch1(Args::as_any, |s| {
                    Patch::args_as_any(TESTS.get("config_override_config_listener").unwrap(), s)
                }),
                patch1(<dyn Any>::downcast_ref, |s| {
                    Patch::args_downcast_ref(
                        TESTS.get("config_override_config_listener").unwrap(),
                        s,
                    )
                }),
            ]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let mock_args = Args {
            base: args::BaseArgs {
                config: "/foo.yaml".to_string(),
                log_level: Some("trace".to_string()),
            },
            host: Some("8.8.8.8".to_string()),
            port: Some(7373),
        };
        let args_boxed: config::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        let result = Config::override_config_listener(Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(
            config_boxed.listener.host,
            "8.8.8.8".to_string().parse::<IpAddr>().unwrap()
        );
        assert_eq!(config_boxed.listener.port, 7373);
    }
}
