use crate::{args::Args, listener, DEFAULT_HOSTNAME};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_yaml::Value;
use std::{collections::HashMap, net::IpAddr};
use toolshed_core as core;
use toolshed_runner as runner;

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct Config {
    #[serde(flatten)]
    pub base: runner::config::BaseConfig,
    #[serde(default = "Config::default_listeners")]
    pub listeners: HashMap<String, listener::Config>,
    #[serde(default = "Config::default_hostname")]
    pub hostname: String,
}

impl Config {
    pub fn default_hostname() -> String {
        DEFAULT_HOSTNAME.to_string()
    }

    pub fn default_listeners() -> HashMap<String, listener::Config> {
        let mut map = HashMap::new();
        map.insert(
            "http".to_string(),
            listener::Config {
                host: Self::default_host(),
                port: Self::default_port(),
            },
        );
        map
    }

    fn default_host() -> IpAddr {
        crate::DEFAULT_HTTP_HOST.to_string().parse().unwrap()
    }

    fn default_port() -> u16 {
        crate::DEFAULT_HTTP_PORT
    }

    fn override_config_hostname(
        args: &runner::config::ArcSafeArgs,
        config: &mut Box<Self>,
    ) -> core::EmptyResult {
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

    fn override_config_http_host(
        args: &runner::config::ArcSafeArgs,
        config: &mut Box<Self>,
    ) -> core::EmptyResult {
        if let Some(args) = args.as_any().downcast_ref::<Args>() {
            if let Some(host) = args.http_host.clone() {
                if let Some(listener) = config.listeners.get_mut("http") {
                    listener.host = host.parse()?;
                }
            }
        }
        Ok(())
    }

    fn override_config_http_port(
        args: &runner::config::ArcSafeArgs,
        config: &mut Box<Self>,
    ) -> core::EmptyResult {
        if let Some(args) = args.as_any().downcast_ref::<Args>() {
            if let Some(port) = args.http_port {
                if let Some(listener) = config.listeners.get_mut("http") {
                    listener.port = port;
                }
            }
        }
        Ok(())
    }
}

#[async_trait]
impl runner::config::Factory<Config> for Config {
    async fn override_config(
        args: &runner::config::ArcSafeArgs,
        mut config: Box<Config>,
    ) -> Result<Box<Config>, runner::config::SafeError> {
        Self::override_config_log(args, &mut config)?;
        Self::override_config_hostname(args, &mut config)?;
        Self::override_config_http_host(args, &mut config)?;
        Self::override_config_http_port(args, &mut config)?;
        Ok(config)
    }
}

impl runner::config::Provider for Config {
    fn serialized(&self) -> Option<Value> {
        serde_yaml::to_value(self.clone()).ok()
    }

    fn set_log(&mut self, level: runner::log::Level) -> core::EmptyResult {
        if let Some(log) = self.base.log.as_mut() {
            log.level = level;
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
        config::Factory as _, config::Provider as _, test::patch::Patch as RunnerPatch,
    };
    use toolshed_test as ttest;

    static PATCHES: Lazy<ttest::Patches> = Lazy::new(ttest::Patches::new);
    static SPY: Lazy<ttest::Spy> = Lazy::new(ttest::Spy::new);
    static TESTS: Lazy<ttest::Tests> = Lazy::new(|| ttest::Tests::new(&SPY, &PATCHES));

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
    fn test_config_constructor() {
        let test = TESTS
            .test("config_default")
            .expecting(vec!["Config::default_listeners(true)"])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_default"))
                }),
                patch2(Config::override_config, |args, config| {
                    Box::pin(Patch::config_override_config(
                        TESTS.get("config_default"),
                        args,
                        config,
                    ))
                }),
            ]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        assert_eq!(
            config.base.log.as_ref().unwrap().level,
            runner::log::Level::Info
        );
    }

    #[tokio::test]
    #[serial(toolshed_lock)]
    async fn test_config_override_config() {
        let test = TESTS
            .test("config_override_config")
            .expecting(vec![
                "Config::override_config_log(true): Args { base: BaseArgs { config: \"/foo.yaml\", log_level: Some(\"trace\") }, http_host: Some(\"8.8.8.8\"), hostname: None, http_port: Some(7373) }, Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listeners: {\"http\": Config { host: 127.0.0.1, port: 8787 }}, hostname: \"echo\" }",
                "Config::override_config_hostname(true): Args { base: BaseArgs { config: \"/foo.yaml\", log_level: Some(\"trace\") }, http_host: Some(\"8.8.8.8\"), hostname: None, http_port: Some(7373) }, Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listeners: {\"http\": Config { host: 127.0.0.1, port: 8787 }}, hostname: \"echo\" }",
                "Config::override_config_http_host(true): Args { base: BaseArgs { config: \"/foo.yaml\", log_level: Some(\"trace\") }, http_host: Some(\"8.8.8.8\"), hostname: None, http_port: Some(7373) }, Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listeners: {\"http\": Config { host: 127.0.0.1, port: 8787 }}, hostname: \"echo\" }",
                "Config::override_config_http_port(true): Args { base: BaseArgs { config: \"/foo.yaml\", log_level: Some(\"trace\") }, http_host: Some(\"8.8.8.8\"), hostname: None, http_port: Some(7373) }, Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listeners: {\"http\": Config { host: 127.0.0.1, port: 8787 }}, hostname: \"echo\" }"
            ])
            .with_patches(vec![
                patch2(Config::override_config_log, |args, config| {
                    RunnerPatch::override_config_log(
                        TESTS.get("config_override_config"),
                        args,
                        config,
                    )
                }),
                patch2(Config::override_config_hostname, |args, config| {
                    Patch::config_override_config_hostname(
                        TESTS.get("config_override_config"),
                        args,
                        config,
                    )
                }),
                patch2(Config::override_config_http_host, |args, config| {
                    Patch::config_override_config_http_host(
                        TESTS.get("config_override_config"),
                        args,
                        config,
                    )
                }),
                patch2(Config::override_config_http_port, |args, config| {
                    Patch::config_override_config_http_port(
                        TESTS.get("config_override_config"),
                        args,
                        config,
                    )
                }),
            ]);
        defer! {
            test.drop();
        }

        let config: Config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let mock_args = Args {
            base: runner::args::BaseArgs {
                config: "/foo.yaml".to_string(),
                log_level: Some("trace".to_string()),
            },
            http_host: Some("8.8.8.8".to_string()),
            hostname: None,
            http_port: Some(7373),
        };
        let args: Arc<runner::config::SafeArgs> = Arc::new(Box::new(mock_args));
        assert!(Config::override_config(&args, Box::new(config))
            .await
            .is_ok());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_serialized() {
        let test = TESTS.test("config_serialized")
            .expecting(vec![
                "serde_yaml::to_value(true): Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listeners: {\"http\": Config { host: 127.0.0.1, port: 8787 }}, hostname: \"echo\" }"])
            .with_patches(vec![patch1(serde_yaml::to_value::<Config>, |thing| {
                RunnerPatch::serde_to_value(TESTS.get("config_serialized"), Box::new(thing))
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
            .expecting(vec!["Config::default_listeners(true)"])
            .with_patches(vec![patch0(Config::default_listeners, || {
                Patch::default_listeners(TESTS.get("config_set_log"))
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
            http_host: Some("8.8.8.8".to_string()),
            hostname: Some("HOSTNAME SET BY ARGS".to_string()),
            http_port: Some(7373),
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
                    Patch::default_hostname(TESTS.get("config_override_config_hostname"))
                }),
                patch1(Args::as_any, |s| {
                    Patch::args_as_any(TESTS.get("config_override_config_hostname"), s)
                }),
                patch1(<dyn Any>::downcast_ref, |s| {
                    Patch::args_downcast_ref(TESTS.get("config_override_config_hostname"), s)
                }),
                patch1(std::env::var, |name| {
                    Patch::env_var(TESTS.get("config_override_config_hostname"), name)
                }),
            ]);
        defer! {
            test.drop();
        }

        let result = Config::override_config_hostname(&Arc::new(args_boxed), &mut config_boxed);
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
            http_host: Some("8.8.8.8".to_string()),
            hostname: None,
            http_port: Some(7373),
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
                    Patch::default_hostname(TESTS.get("config_override_config_hostname_env"))
                }),
                patch1(Args::as_any, |s| {
                    Patch::args_as_any(TESTS.get("config_override_config_hostname_env"), s)
                }),
                patch1(<dyn Any>::downcast_ref, |s| {
                    Patch::args_downcast_ref(TESTS.get("config_override_config_hostname_env"), s)
                }),
                patch1(std::env::var, |name| {
                    Patch::env_var(TESTS.get("config_override_config_hostname_env"), name)
                }),
            ]);
        defer! {
            test.drop();
        }

        let result = Config::override_config_hostname(&Arc::new(args_boxed), &mut config_boxed);
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
            http_host: Some("8.8.8.8".to_string()),
            hostname: None,
            http_port: Some(7373),
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
                    Patch::default_hostname(TESTS.get("config_override_config_hostname_env"))
                }),
                patch1(Args::as_any, |s| {
                    Patch::args_as_any(TESTS.get("config_override_config_hostname_env"), s)
                }),
                patch1(<dyn Any>::downcast_ref, |s| {
                    Patch::args_downcast_ref(TESTS.get("config_override_config_hostname_env"), s)
                }),
                patch1(std::env::var, |name| {
                    let _ = Patch::env_var(TESTS.get("config_override_config_hostname_env"), name);
                    Err(std::env::VarError::NotPresent)
                }),
            ]);
        defer! {
            test.drop();
        }

        let result = Config::override_config_hostname(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.hostname, DEFAULT_HOSTNAME);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_config_http_host() {
        let test = TESTS
            .test("config_override_config_http_host")
            .expecting(vec![
                "Config::default_listeners(true)",
                "Args::as_any(true)",
                "Any::downcast_ref::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_config_http_host"))
                }),
                patch1(Args::as_any, |s| {
                    Patch::args_as_any(TESTS.get("config_override_config_http_host"), s)
                }),
                patch1(<dyn Any>::downcast_ref, |s| {
                    Patch::args_downcast_ref(TESTS.get("config_override_config_http_host"), s)
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
            http_host: Some("8.8.8.8".to_string()),
            hostname: Some("HOSTNAME".to_string()),
            http_port: Some(7373),
        };
        let args_boxed: runner::config::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        let result = Config::override_config_http_host(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(
            config_boxed.listeners.get("http").unwrap().host,
            "8.8.8.8".to_string().parse::<IpAddr>().unwrap()
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_config_http_port() {
        let test = TESTS
            .test("config_override_config_http_port")
            .expecting(vec![
                "Config::default_listeners(true)",
                "Args::as_any(true)",
                "Any::downcast_ref::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_config_http_port"))
                }),
                patch1(Args::as_any, |s| {
                    Patch::args_as_any(TESTS.get("config_override_config_http_port"), s)
                }),
                patch1(<dyn Any>::downcast_ref, |s| {
                    Patch::args_downcast_ref(TESTS.get("config_override_config_http_port"), s)
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
            http_host: Some("8.8.8.8".to_string()),
            hostname: Some("HOSTNAME".to_string()),
            http_port: Some(7373),
        };
        let args_boxed: runner::config::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        let result = Config::override_config_http_port(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.listeners.get("http").unwrap().port, 7373);
    }
}
