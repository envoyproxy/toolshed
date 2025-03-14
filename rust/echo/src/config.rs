use crate::{args::Args, listener, DEFAULT_HOSTNAME};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_yaml::Value;
use toolshed_runner as runner;

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct Config {
    #[serde(flatten)]
    pub base: runner::config::BaseConfig,
    #[serde(default = "listener::Config::default_listener")]
    pub listener: listener::Config,
    #[serde(default = "Config::default_hostname")]
    pub hostname: String,
}

#[async_trait]
impl runner::config::Factory<Config> for Config {
    async fn override_config(
        args: runner::config::ArcSafeArgs,
        mut config: Box<Config>,
    ) -> Result<Box<Config>, runner::config::SafeError> {
        Self::override_config_log(args.clone(), &mut config)?;
        Self::override_config_listener(args.clone(), &mut config)?;
        Self::override_config_hostname(args, &mut config)?;
        Ok(config)
    }
}

impl runner::config::Provider for Config {
    fn serialized(&self) -> Option<Value> {
        serde_yaml::to_value(self.clone()).ok()
    }

    fn set_log(&mut self, level: runner::log::Level) -> runner::EmptyResult {
        if let Some(log) = self.base.log.as_mut() {
            log.level = level;
        }
        Ok(())
    }
}

impl Config {
    pub fn default_hostname() -> String {
        DEFAULT_HOSTNAME.to_string()
    }

    fn override_config_hostname(
        args: runner::config::ArcSafeArgs,
        config: &mut Box<Self>,
    ) -> runner::EmptyResult {
        if let Some(args) = args.as_any().downcast_ref::<Args>() {
            if let Some(hostname) = args
                .hostname
                .clone()
                .or_else(|| std::env::var("ECHO_HOSTNAME").ok())
            {
                config.hostname = hostname;
            }
        }
        Ok(())
    }

    fn override_config_listener(
        args: runner::config::ArcSafeArgs,
        config: &mut Box<Self>,
    ) -> runner::EmptyResult {
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
    use guerrilla::{patch0, patch1};
    use mockall::mock;
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use std::{any::Any, net::IpAddr, sync::Arc};
    use toolshed_runner::{
        config::Provider as _,
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
        impl runner::args::Provider for ArgsProvider {
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
        assert_eq!(
            config.base.log.as_ref().unwrap().level,
            runner::log::Level::Info
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_serialized() {
        let test = TESTS.test("config_serialized")
            .expecting(vec![
                "serde_yaml::to_value(true): Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listener: Config { host: 127.0.0.1, port: 8787 }, hostname: \"echo\" }"
            ])
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
        let result = config.set_log(runner::log::Level::Trace);
        assert!(result.is_ok());
        assert_eq!(
            config.base.log.as_ref().unwrap().level,
            runner::log::Level::Trace
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_config_hostname() {
        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let mut config_boxed = Box::new(config);

        let mock_args = Args {
            base: runner::args::BaseArgs {
                config: "/foo.yaml".to_string(),
                log_level: Some("trace".to_string()),
            },
            host: Some("8.8.8.8".to_string()),
            hostname: Some("HOSTNAME SET BY ARGS".to_string()),
            port: Some(7373),
        };
        let args_boxed: runner::config::SafeArgs = Box::new(mock_args);

        let test = TESTS
            .test("config_override_config_hostname")
            .expecting(vec![
                "Args::as_any(true)",
                "Any::downcast_ref::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_hostname, || {
                    Patch::default_hostname(TESTS.get("config_override_config_hostname").unwrap())
                }),
                patch1(Args::as_any, |s| {
                    Patch::args_as_any(TESTS.get("config_override_config_hostname").unwrap(), s)
                }),
                patch1(<dyn Any>::downcast_ref, |s| {
                    Patch::args_downcast_ref(
                        TESTS.get("config_override_config_hostname").unwrap(),
                        s,
                    )
                }),
                patch1(std::env::var, |name| {
                    Patch::env_var(TESTS.get("config_override_config_hostname").unwrap(), name)
                }),
            ]);
        defer! {
            test.drop();
        }

        let result = Config::override_config_hostname(Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.hostname, "HOSTNAME SET BY ARGS");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_config_hostname_env() {
        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let mock_args = Args {
            base: runner::args::BaseArgs {
                config: "/foo.yaml".to_string(),
                log_level: Some("trace".to_string()),
            },
            host: Some("8.8.8.8".to_string()),
            hostname: None,
            port: Some(7373),
        };
        let args_boxed: runner::config::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);

        let test = TESTS
            .test("config_override_config_hostname_env")
            .expecting(vec![
                "Args::as_any(true)",
                "Any::downcast_ref::<Args>(true)",
                "std::env::var(true): \"ECHO_HOSTNAME\"",
            ])
            .with_patches(vec![
                patch0(Config::default_hostname, || {
                    Patch::default_hostname(
                        TESTS.get("config_override_config_hostname_env").unwrap(),
                    )
                }),
                patch1(Args::as_any, |s| {
                    Patch::args_as_any(TESTS.get("config_override_config_hostname_env").unwrap(), s)
                }),
                patch1(<dyn Any>::downcast_ref, |s| {
                    Patch::args_downcast_ref(
                        TESTS.get("config_override_config_hostname_env").unwrap(),
                        s,
                    )
                }),
                patch1(std::env::var, |name| {
                    Patch::env_var(
                        TESTS.get("config_override_config_hostname_env").unwrap(),
                        name,
                    )
                }),
            ]);
        defer! {
            test.drop();
        }

        let result = Config::override_config_hostname(Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.hostname, "SOMEVAR");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_config_hostname_none() {
        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let mock_args = Args {
            base: runner::args::BaseArgs {
                config: "/foo.yaml".to_string(),
                log_level: Some("trace".to_string()),
            },
            host: Some("8.8.8.8".to_string()),
            hostname: None,
            port: Some(7373),
        };
        let args_boxed: runner::config::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);

        let test = TESTS
            .test("config_override_config_hostname_env")
            .expecting(vec![
                "Args::as_any(true)",
                "Any::downcast_ref::<Args>(true)",
                "std::env::var(true): \"ECHO_HOSTNAME\"",
            ])
            .with_patches(vec![
                patch0(Config::default_hostname, || {
                    Patch::default_hostname(
                        TESTS.get("config_override_config_hostname_env").unwrap(),
                    )
                }),
                patch1(Args::as_any, |s| {
                    Patch::args_as_any(TESTS.get("config_override_config_hostname_env").unwrap(), s)
                }),
                patch1(<dyn Any>::downcast_ref, |s| {
                    Patch::args_downcast_ref(
                        TESTS.get("config_override_config_hostname_env").unwrap(),
                        s,
                    )
                }),
                patch1(std::env::var, |name| {
                    let _ = Patch::env_var(
                        TESTS.get("config_override_config_hostname_env").unwrap(),
                        name,
                    );
                    Err(std::env::VarError::NotPresent)
                }),
            ]);
        defer! {
            test.drop();
        }

        let result = Config::override_config_hostname(Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.hostname, DEFAULT_HOSTNAME);
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
            base: runner::args::BaseArgs {
                config: "/foo.yaml".to_string(),
                log_level: Some("trace".to_string()),
            },
            host: Some("8.8.8.8".to_string()),
            hostname: Some("HOSTNAME".to_string()),
            port: Some(7373),
        };
        let args_boxed: runner::config::SafeArgs = Box::new(mock_args);
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
