use crate::{args::Args, listener, tls, DEFAULT_HOSTNAME};
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
    pub tls: Option<tls::Config>,
}

impl Config {
    pub fn default_hostname() -> String {
        DEFAULT_HOSTNAME.to_string()
    }

    pub fn default_listeners() -> HashMap<String, listener::Config> {
        let mut map = HashMap::new();
        map.insert(
            "http".to_string(),
            listener::Config::new(Self::default_http_host(), Self::default_http_port()),
        );
        map
    }

    fn default_http_host() -> IpAddr {
        crate::DEFAULT_HTTP_HOST.to_string().parse().unwrap()
    }

    fn default_http_port() -> u16 {
        crate::DEFAULT_HTTP_PORT
    }

    fn override_hostname(
        args: &runner::args::ArcSafeArgs,
        config: &mut Box<Self>,
    ) -> core::EmptyResult {
        if let Some(hostname) =
            runner::config_override!(core::downcast::<Args>(&***args)?, hostname, "ECHO_HOSTNAME")
        {
            config.hostname = hostname;
        }
        Ok(())
    }

    fn override_http_host(
        args: &runner::args::ArcSafeArgs,
        config: &mut Box<Self>,
    ) -> core::EmptyResult {
        let host = runner::config_override!(
            core::downcast::<Args>(&***args)?,
            http_host,
            "ECHO_HTTP_HOST"
        );
        if let (Some(host), Some(listener)) = (host, config.listeners.get_mut("http")) {
            listener.host = host.parse()?;
        }
        Ok(())
    }

    fn override_http_port(
        args: &runner::args::ArcSafeArgs,
        config: &mut Box<Self>,
    ) -> core::EmptyResult {
        let port = runner::config_override!(
            core::downcast::<Args>(&***args)?,
            http_port,
            "ECHO_HTTP_PORT"
        );
        if let (Some(port), Some(listener)) = (port, config.listeners.get_mut("http")) {
            listener.port = port;
        }
        Ok(())
    }

    fn override_https(
        args: &runner::args::ArcSafeArgs,
        config: &mut Box<Self>,
    ) -> core::EmptyResult {
        if config.tls.is_none() {
            return Ok(());
        }
        let args = core::downcast::<Args>(&***args)?;
        let port = runner::config_override!(args, https_port, "ECHO_HTTPS_PORT");
        let host = runner::config_override!(args, https_host, "ECHO_HTTPS_HOST");
        if (host.is_none() && port.is_none())
            || (config.listeners.get("https").is_none() && (port.is_none() || host.is_none()))
        {
            return Ok(());
        }

        if let Some(listener) = config.listeners.get_mut("https") {
            if let Some(host) = host {
                listener.host = host.parse()?;
            }
            if let Some(port) = port {
                listener.port = port;
            }
        } else {
            config.listeners.insert(
                "https".to_string(),
                listener::Config::new(host.unwrap().parse()?, port.unwrap()),
            );
        }
        Ok(())
    }

    fn override_tls(args: &runner::args::ArcSafeArgs, config: &mut Box<Self>) -> core::EmptyResult {
        let args = core::downcast::<Args>(&***args)?;
        let tls_cert = runner::config_override!(args, tls_cert, "ECHO_TLS_CERT");
        let tls_key = runner::config_override!(args, tls_key, "ECHO_TLS_KEY");
        if tls_cert.is_none() && tls_key.is_none() {
            return Ok(());
        }
        if let Some(tls) = &mut config.tls {
            if let Some(cert) = tls_cert {
                tls.cert = cert;
            }
            if let Some(key) = tls_key {
                tls.key = key;
            }
        } else {
            if let (Some(cert), Some(key)) = (&tls_cert, &tls_key) {
                config.tls = Some(tls::Config::new(cert.to_string(), key.to_string()));
            } else {
                if tls_cert.is_some() {
                    eprintln!("TLS certificate override ignored because no existing TLS configuration and no key provided");
                }
                if tls_key.is_some() {
                    eprintln!("TLS key override ignored because no existing TLS configuration and no certificate provided");
                }
            }
        }
        Ok(())
    }
}

#[async_trait]
impl runner::config::Factory<Config> for Config {
    async fn override_config(
        args: &runner::args::ArcSafeArgs,
        mut config: Box<Config>,
    ) -> Result<Box<Config>, runner::config::SafeError> {
        Self::override_log(args, &mut config)?;
        Self::override_hostname(args, &mut config)?;
        Self::override_http_host(args, &mut config)?;
        Self::override_http_port(args, &mut config)?;

        // TLS should be resolved first
        Self::override_tls(args, &mut config)?;
        Self::override_https(args, &mut config)?;
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
    use guerrilla::{patch0, patch1, patch2};
    use mockall::mock;
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use std::{net::IpAddr, sync::Arc};
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
                "Config::override_log(true): Args { base: BaseArgs { config: \"/foo.yaml\", log_level: Some(\"trace\") }, hostname: None, http_host: Some(\"8.8.8.8\"), http_port: Some(7373), https_host: None, https_port: None, tls_cert: None, tls_key: None }, Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listeners: {\"http\": Config { host: 127.0.0.1, port: 8787 }}, hostname: \"echo\", tls: None }",
                "Config::override_hostname(true): Args { base: BaseArgs { config: \"/foo.yaml\", log_level: Some(\"trace\") }, hostname: None, http_host: Some(\"8.8.8.8\"), http_port: Some(7373), https_host: None, https_port: None, tls_cert: None, tls_key: None }, Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listeners: {\"http\": Config { host: 127.0.0.1, port: 8787 }}, hostname: \"echo\", tls: None }",
                "Config::override_http_host(true): Args { base: BaseArgs { config: \"/foo.yaml\", log_level: Some(\"trace\") }, hostname: None, http_host: Some(\"8.8.8.8\"), http_port: Some(7373), https_host: None, https_port: None, tls_cert: None, tls_key: None }, Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listeners: {\"http\": Config { host: 127.0.0.1, port: 8787 }}, hostname: \"echo\", tls: None }",
                "Config::override_http_port(true): Args { base: BaseArgs { config: \"/foo.yaml\", log_level: Some(\"trace\") }, hostname: None, http_host: Some(\"8.8.8.8\"), http_port: Some(7373), https_host: None, https_port: None, tls_cert: None, tls_key: None }, Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listeners: {\"http\": Config { host: 127.0.0.1, port: 8787 }}, hostname: \"echo\", tls: None }",
                "Config::override_tls(true): Args { base: BaseArgs { config: \"/foo.yaml\", log_level: Some(\"trace\") }, hostname: None, http_host: Some(\"8.8.8.8\"), http_port: Some(7373), https_host: None, https_port: None, tls_cert: None, tls_key: None }, Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listeners: {\"http\": Config { host: 127.0.0.1, port: 8787 }}, hostname: \"echo\", tls: None }",
                "Config::override_https(true): Args { base: BaseArgs { config: \"/foo.yaml\", log_level: Some(\"trace\") }, hostname: None, http_host: Some(\"8.8.8.8\"), http_port: Some(7373), https_host: None, https_port: None, tls_cert: None, tls_key: None }, Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listeners: {\"http\": Config { host: 127.0.0.1, port: 8787 }}, hostname: \"echo\", tls: None }",
            ])
            .with_patches(vec![
                patch2(Config::override_log, |args, config| {
                    RunnerPatch::override_log(
                        TESTS.get("config_override_config"),
                        args,
                        config,
                    )
                }),
                patch2(Config::override_hostname, |args, config| {
                    Patch::config_override_hostname(
                        TESTS.get("config_override_config"),
                        args,
                        config,
                    )
                }),
                patch2(Config::override_http_host, |args, config| {
                    Patch::config_override_http_host(
                        TESTS.get("config_override_config"),
                        args,
                        config,
                    )
                }),
                patch2(Config::override_http_port, |args, config| {
                    Patch::config_override_http_port(
                        TESTS.get("config_override_config"),
                        args,
                        config,
                    )
                }),
                patch2(Config::override_https, |args, config| {
                    Patch::config_override_https(
                        TESTS.get("config_override_config"),
                        args,
                        config,
                    )
                }),
                patch2(Config::override_tls, |args, config| {
                    Patch::config_override_tls(
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
            https_host: None,
            https_port: None,
            tls_cert: None,
            tls_key: None,
        };
        let args: Arc<runner::args::SafeArgs> = Arc::new(Box::new(mock_args));
        assert!(Config::override_config(&args, Box::new(config))
            .await
            .is_ok());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_serialized() {
        let test = TESTS.test("config_serialized")
            .expecting(vec![
                "serde_yaml::to_value(true): Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listeners: {\"http\": Config { host: 127.0.0.1, port: 8787 }}, hostname: \"echo\", tls: None }"])
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
    fn test_config_override_hostname() {
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
            https_host: None,
            https_port: None,
            tls_cert: None,
            tls_key: None,
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);

        let test = TESTS
            .test("config_override_hostname")
            .expecting(vec!["downcast::<Args>(true)"])
            .with_patches(vec![
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_hostname"), s)
                }),
                patch1(std::env::var, |name| {
                    Patch::env_var(TESTS.get("config_override_hostname"), name)
                }),
            ]);
        defer! {
            test.drop();
        }

        let result = Config::override_hostname(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.hostname, "HOSTNAME SET BY ARGS");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_hostname_env() {
        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let mock_args = Args {
            base: runner::args::BaseArgs {
                config: "/foo.yaml".to_string(),
                log_level: Some("trace".to_string()),
            },
            http_host: Some("8.8.8.8".to_string()),
            hostname: None,
            http_port: Some(7373),
            https_host: None,
            https_port: None,
            tls_cert: None,
            tls_key: None,
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);

        let test = TESTS
            .test("config_override_hostname_env")
            .expecting(vec![
                "downcast::<Args>(true)",
                "std::env::var(true): \"ECHO_HOSTNAME\"",
            ])
            .with_patches(vec![
                patch0(Config::default_hostname, || {
                    Patch::default_hostname(TESTS.get("config_override_hostname_env"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_hostname_env"), s)
                }),
                patch1(std::env::var, |name| {
                    Patch::env_var(TESTS.get("config_override_hostname_env"), name)
                }),
            ]);
        defer! {
            test.drop();
        }

        let result = Config::override_hostname(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.hostname, "SOMEVAR");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_hostname_none() {
        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let mock_args = Args {
            base: runner::args::BaseArgs {
                config: "/foo.yaml".to_string(),
                log_level: Some("trace".to_string()),
            },
            http_host: Some("8.8.8.8".to_string()),
            hostname: None,
            http_port: Some(7373),
            https_host: None,
            https_port: None,
            tls_cert: None,
            tls_key: None,
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);

        let test = TESTS
            .test("config_override_hostname_none")
            .expecting(vec![
                "downcast::<Args>(true)",
                "std::env::var(true): \"ECHO_HOSTNAME\"",
            ])
            .with_patches(vec![
                patch0(Config::default_hostname, || {
                    Patch::default_hostname(TESTS.get("config_override_hostname_none"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_hostname_none"), s)
                }),
                patch1(std::env::var, |name| {
                    let _ = Patch::env_var(TESTS.get("config_override_hostname_none"), name);
                    Err(std::env::VarError::NotPresent)
                }),
            ]);
        defer! {
            test.drop();
        }

        let result = Config::override_hostname(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.hostname, DEFAULT_HOSTNAME);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_http_host() {
        let test = TESTS
            .test("config_override_http_host")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_http_host"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_http_host"), s)
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
            https_host: None,
            https_port: None,
            tls_cert: None,
            tls_key: None,
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        let result = Config::override_http_host(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(
            config_boxed.listeners.get("http").unwrap().host,
            "8.8.8.8".to_string().parse::<IpAddr>().unwrap()
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_http_port() {
        let test = TESTS
            .test("config_override_http_port")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_http_port"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_http_port"), s)
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
            https_host: None,
            https_port: None,
            tls_cert: None,
            tls_key: None,
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        let result = Config::override_http_port(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.listeners.get("http").unwrap().port, 7373);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_tls_both_none() {
        let test = TESTS
            .test("config_override_tls_both_none")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_tls_both_none"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_tls_both_none"), s)
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
            https_host: None,
            https_port: None,
            tls_cert: None,
            tls_key: None,
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = Some(tls::Config::new(
            "old-cert.pem".to_string(),
            "old-key.pem".to_string(),
        ));
        let result = Config::override_tls(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.tls.as_ref().unwrap().cert, "old-cert.pem");
        assert_eq!(config_boxed.tls.as_ref().unwrap().key, "old-key.pem");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_tls_existing_both() {
        let test = TESTS
            .test("config_override_tls_existing_both")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_tls_existing_both"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_tls_existing_both"), s)
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
            https_host: None,
            https_port: None,
            tls_cert: Some("/path/to/cert.pem".to_string()),
            tls_key: Some("/path/to/key.pem".to_string()),
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = Some(tls::Config::new(
            "old-cert.pem".to_string(),
            "old-key.pem".to_string(),
        ));
        let result = Config::override_tls(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.tls.as_ref().unwrap().cert, "/path/to/cert.pem");
        assert_eq!(config_boxed.tls.as_ref().unwrap().key, "/path/to/key.pem");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_tls_existing_cert_only() {
        let test = TESTS
            .test("config_override_tls_existing_cert_only")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_tls_existing_cert_only"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_tls_existing_cert_only"), s)
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
            https_host: None,
            https_port: None,
            tls_cert: Some("/path/to/cert.pem".to_string()),
            tls_key: None,
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = Some(tls::Config::new(
            "old-cert.pem".to_string(),
            "old-key.pem".to_string(),
        ));
        let result = Config::override_tls(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.tls.as_ref().unwrap().cert, "/path/to/cert.pem");
        assert_eq!(config_boxed.tls.as_ref().unwrap().key, "old-key.pem");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_tls_existing_key_only() {
        let test = TESTS
            .test("config_override_tls_existing_key_only")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_tls_existing_key_only"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_tls_existing_key_only"), s)
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
            https_host: None,
            https_port: None,
            tls_cert: None,
            tls_key: Some("/path/to/key.pem".to_string()),
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = Some(tls::Config::new(
            "old-cert.pem".to_string(),
            "old-key.pem".to_string(),
        ));
        let result = Config::override_tls(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.tls.as_ref().unwrap().cert, "old-cert.pem");
        assert_eq!(config_boxed.tls.as_ref().unwrap().key, "/path/to/key.pem");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_tls_none_create_new() {
        let test = TESTS
            .test("config_override_tls_none_create_new")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_tls_none_create_new"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_tls_none_create_new"), s)
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
            https_host: None,
            https_port: None,
            tls_cert: Some("/path/to/cert.pem".to_string()),
            tls_key: Some("/path/to/key.pem".to_string()),
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = None;
        let result = Config::override_tls(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(config_boxed.tls.as_ref().unwrap().cert, "/path/to/cert.pem");
        assert_eq!(config_boxed.tls.as_ref().unwrap().key, "/path/to/key.pem");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_tls_none_cert_only() {
        let test = TESTS
            .test("config_override_tls_none_cert_only")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_tls_none_cert_only"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_tls_none_cert_only"), s)
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
            https_host: None,
            https_port: None,
            tls_cert: Some("/path/to/cert.pem".to_string()),
            tls_key: None,
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = None;
        let result = Config::override_tls(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert!(config_boxed.tls.is_none());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_tls_none_key_only() {
        let test = TESTS
            .test("config_override_tls_none_key_only")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_tls_none_key_only"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_tls_none_key_only"), s)
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
            https_host: None,
            https_port: None,
            tls_cert: None,
            tls_key: Some("/path/to/key.pem".to_string()),
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = None;
        let result = Config::override_tls(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert!(config_boxed.tls.is_none());
    }

    // ///// HTTPS /////

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_https_no_tls() {
        let test = TESTS
            .test("config_override_https_no_tls")
            .expecting(vec!["Config::default_listeners(true)"])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_https_no_tls"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_https_no_tls"), s)
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
            https_host: Some("1.1.1.1".to_string()),
            https_port: Some(8443),
            tls_cert: Some("/path/to/cert.pem".to_string()),
            tls_key: Some("/path/to/key.pem".to_string()),
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = None;
        let result = Config::override_https(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert!(config_boxed.listeners.get("https").is_none());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_https_both_none() {
        let test = TESTS
            .test("config_override_https_both_none")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_https_both_none"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_https_both_none"), s)
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
            https_host: None,
            https_port: None,
            tls_cert: Some("/path/to/cert.pem".to_string()),
            tls_key: Some("/path/to/key.pem".to_string()),
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = Some(tls::Config::new(
            "cert.pem".to_string(),
            "key.pem".to_string(),
        ));
        let result = Config::override_https(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert!(config_boxed.listeners.get("https").is_none());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_https_no_listener_port_none() {
        let test = TESTS
            .test("config_override_https_no_listener_port_none")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(
                        TESTS.get("config_override_https_no_listener_port_none"),
                    )
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_https_no_listener_port_none"), s)
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
            https_host: Some("1.1.1.1".to_string()),
            https_port: None,
            tls_cert: Some("/path/to/cert.pem".to_string()),
            tls_key: Some("/path/to/key.pem".to_string()),
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = Some(tls::Config::new(
            "cert.pem".to_string(),
            "key.pem".to_string(),
        ));
        let result = Config::override_https(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert!(config_boxed.listeners.get("https").is_none());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_https_no_listener_host_none() {
        let test = TESTS
            .test("config_override_https_no_listener_host_none")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(
                        TESTS.get("config_override_https_no_listener_host_none"),
                    )
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_https_no_listener_host_none"), s)
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
            https_host: None,
            https_port: Some(8443),
            tls_cert: Some("/path/to/cert.pem".to_string()),
            tls_key: Some("/path/to/key.pem".to_string()),
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = Some(tls::Config::new(
            "cert.pem".to_string(),
            "key.pem".to_string(),
        ));
        let result = Config::override_https(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert!(config_boxed.listeners.get("https").is_none());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_https_existing_both() {
        let test = TESTS
            .test("config_override_https_existing_both")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_https_existing_both"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_https_existing_both"), s)
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
            https_host: Some("1.1.1.1".to_string()),
            https_port: Some(8443),
            tls_cert: Some("/path/to/cert.pem".to_string()),
            tls_key: Some("/path/to/key.pem".to_string()),
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = Some(tls::Config::new(
            "cert.pem".to_string(),
            "key.pem".to_string(),
        ));
        config_boxed.listeners.insert(
            "https".to_string(),
            listener::Config::new("0.0.0.0".parse().unwrap(), 443),
        );
        let result = Config::override_https(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(
            config_boxed
                .listeners
                .get("https")
                .unwrap()
                .host
                .to_string(),
            "1.1.1.1"
        );
        assert_eq!(config_boxed.listeners.get("https").unwrap().port, 8443);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_https_existing_host_only() {
        let test = TESTS
            .test("config_override_https_existing_host_only")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_https_existing_host_only"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_https_existing_host_only"), s)
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
            https_host: Some("1.1.1.1".to_string()),
            https_port: None,
            tls_cert: Some("/path/to/cert.pem".to_string()),
            tls_key: Some("/path/to/key.pem".to_string()),
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = Some(tls::Config::new(
            "cert.pem".to_string(),
            "key.pem".to_string(),
        ));
        config_boxed.listeners.insert(
            "https".to_string(),
            listener::Config::new("0.0.0.0".parse().unwrap(), 443),
        );
        let result = Config::override_https(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(
            config_boxed
                .listeners
                .get("https")
                .unwrap()
                .host
                .to_string(),
            "1.1.1.1"
        );
        assert_eq!(config_boxed.listeners.get("https").unwrap().port, 443);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_https_existing_port_only() {
        let test = TESTS
            .test("config_override_https_existing_port_only")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_https_existing_port_only"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_https_existing_port_only"), s)
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
            https_host: None,
            https_port: Some(8443),
            tls_cert: Some("/path/to/cert.pem".to_string()),
            tls_key: Some("/path/to/key.pem".to_string()),
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = Some(tls::Config::new(
            "cert.pem".to_string(),
            "key.pem".to_string(),
        ));
        config_boxed.listeners.insert(
            "https".to_string(),
            listener::Config::new("0.0.0.0".parse().unwrap(), 443),
        );
        let result = Config::override_https(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(
            config_boxed
                .listeners
                .get("https")
                .unwrap()
                .host
                .to_string(),
            "0.0.0.0"
        );
        assert_eq!(config_boxed.listeners.get("https").unwrap().port, 8443);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_config_override_https_create_new() {
        let test = TESTS
            .test("config_override_https_create_new")
            .expecting(vec![
                "Config::default_listeners(true)",
                "downcast::<Args>(true)",
            ])
            .with_patches(vec![
                patch0(Config::default_listeners, || {
                    Patch::default_listeners(TESTS.get("config_override_https_create_new"))
                }),
                patch1(core::downcast::<Args>, |s| {
                    Patch::downcast(TESTS.get("config_override_https_create_new"), s)
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
            https_host: Some("1.1.1.1".to_string()),
            https_port: Some(8443),
            tls_cert: Some("/path/to/cert.pem".to_string()),
            tls_key: Some("/path/to/key.pem".to_string()),
        };
        let args_boxed: runner::args::SafeArgs = Box::new(mock_args);
        let mut config_boxed = Box::new(config);
        config_boxed.tls = Some(tls::Config::new(
            "cert.pem".to_string(),
            "key.pem".to_string(),
        ));
        let result = Config::override_https(&Arc::new(args_boxed), &mut config_boxed);
        assert!(result.is_ok());
        assert_eq!(
            config_boxed
                .listeners
                .get("https")
                .unwrap()
                .host
                .to_string(),
            "1.1.1.1"
        );
        assert_eq!(config_boxed.listeners.get("https").unwrap().port, 8443);
    }
}
