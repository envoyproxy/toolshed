use crate::{
    args::Args,
    command::Command,
    config::Config,
    handler::EchoHandler,
    listener::{Endpoint, Listeners, ListenersProvider as _},
};
use async_trait::async_trait;
use clap::Parser;
use serde::{Deserialize, Serialize};
use std::net::IpAddr;
use toolshed_core as core;
use toolshed_runner::{self as runner, config::Factory as _, runner::Runner as _};

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Runner {
    pub handler: EchoHandler,
}

#[async_trait]
trait EchoRunner: runner::runner::Runner<EchoHandler> {
    async fn cmd_start(&self) -> core::EmptyResult {
        self.listeners()?.bind(self.get_handler()).await?;
        Ok(())
    }

    fn listeners(&self) -> Result<Listeners, Box<dyn std::error::Error + Send + Sync>>;

    fn http_host(&self) -> Result<IpAddr, Box<dyn std::error::Error + Send + Sync>> {
        match self.config("listeners.http.host") {
            Some(core::Primitive::String(addr)) => match addr.parse::<IpAddr>() {
                Ok(ip) => Ok(ip),
                Err(e) => Err(format!("Invalid host '{}': {}", addr, e).into()),
            },
            Some(other) => {
                Err(format!("Unexpected type for 'listeners.http.host': {:?}", other).into())
            }
            None => Err("Missing 'listeners.http.host' config".into()),
        }
    }

    fn http_port(&self) -> Result<u16, Box<dyn std::error::Error + Send + Sync>> {
        match self.config("listeners.http.port") {
            Some(core::Primitive::U32(port)) => Ok(port as u16),
            Some(other) => {
                Err(format!("Unexpected type for 'listeners.http.port': {:?}", other).into())
            }
            None => Err("Missing 'listeners.http.port' config".into()),
        }
    }
}

impl Runner {}

#[async_trait]
impl EchoRunner for Runner {
    fn listeners(&self) -> Result<Listeners, Box<dyn std::error::Error + Send + Sync>> {
        let mut listeners = Listeners::new();
        listeners.insert(Endpoint {
            name: "http".to_string(),
            host: self.http_host()?,
            port: self.http_port()?,
        });
        Ok(listeners)
    }
}

impl runner::runner::Factory<Runner, EchoHandler> for Runner {
    fn new(handler: EchoHandler) -> Self {
        Self { handler }
    }
}

#[async_trait]
impl runner::runner::Runner<EchoHandler> for Runner {
    runner::runner!(
        EchoHandler,
        {
            "start" => Self::cmd_start,
        }
    );

    fn get_handler(&self) -> &EchoHandler {
        &self.handler
    }
}

pub async fn main() {
    let args = Args::parse();
    match Config::from_yaml(Box::new(args)).await {
        Ok(config) => {
            let command = <Command as runner::command::Factory<Command, Config>>::new(
                *config,
                Some("start".to_string()),
            );
            let handler = <EchoHandler as runner::handler::Factory<Command>>::new(command.clone());
            let runner = <Runner as runner::runner::Factory<Runner, EchoHandler>>::new(handler);
            runner.run().await.unwrap();
        }
        Err(e) => {
            eprintln!("Error loading config:\n {}", e);
        }
    };
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{listener, test::patch::Patch};
    use guerrilla::{patch0, patch1, patch2};
    use mockall::mock;
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use std::{
        net::{IpAddr, SocketAddr},
        sync::Arc,
    };
    use toolshed_runner::test::patch::Patch as RunnerPatch;
    use toolshed_test as ttest;

    static PATCHES: Lazy<ttest::Patches> = Lazy::new(ttest::Patches::new);
    static SPY: Lazy<ttest::Spy> = Lazy::new(ttest::Spy::new);
    static TESTS: Lazy<ttest::Tests> = Lazy::new(|| ttest::Tests::new(&SPY, &PATCHES));

    mock! {
        Endpoint {}

        #[async_trait]
        impl listener::Listener for Endpoint {
            async fn bind(self: Arc<Self>, router: axum::Router);
            async fn listen(&self) -> tokio::net::TcpListener;
            fn name(&self) -> &str;
            fn socket_address(&self) -> SocketAddr;
        }
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_main() {
        let test = TESTS
            .test("echo_main")
            .expecting(vec![
                "Args::parse(true)",
                "Config::from_yaml(true)",
                "Command::new(true)",
                "Runner::new(true)",
                "Runner::run(true)",
            ])
            .with_patches(vec![
                patch0(Args::parse, || Patch::args_parse(TESTS.get("echo_main"))),
                patch1(Config::from_yaml, |args| {
                    let test = TESTS.get("echo_main");
                    test.lock().unwrap().patch_index(1);
                    Box::pin(Patch::config_from_yaml(test, args))
                }),
                patch2(
                    <Command as runner::command::Factory<Command, Config>>::new,
                    |config, command| {
                        Patch::runner_command_from_config(TESTS.get("echo_main"), config, command)
                    },
                ),
                patch1(
                    <Runner as runner::runner::Factory<Runner, EchoHandler>>::new,
                    |handler| Patch::runner_factory(TESTS.get("echo_main"), handler),
                ),
                patch1(Runner::run, |_self| {
                    Box::pin(Patch::runner_run(TESTS.get("echo_main"), _self))
                }),
            ]);
        defer! {
            test.drop();
        }
        main().await
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_main_badconfig() {
        let test = TESTS
            .test("echo_main_badconfig")
            .expecting(vec!["Args::parse(true)", "Config::from_yaml(false)"])
            .with_patches(vec![
                patch0(Args::parse, || {
                    Patch::args_parse(TESTS.get("echo_main_badconfig"))
                }),
                patch1(Config::from_yaml, |args| {
                    let test = TESTS.get("echo_main_badconfig");
                    test.lock().unwrap().fail().patch_index(1);
                    Box::pin(Patch::config_from_yaml(test, args))
                }),
                patch2(
                    <Command as runner::command::Factory<Command, Config>>::new,
                    |config, command| {
                        Patch::runner_command_from_config(
                            TESTS.get("echo_main_badconfig"),
                            config,
                            command,
                        )
                    },
                ),
                patch1(
                    <Runner as runner::runner::Factory<Runner, EchoHandler>>::new,
                    |command| Patch::runner_factory(TESTS.get("echo_main_badconfig"), command),
                ),
                patch1(Runner::run, |_self| {
                    Box::pin(Patch::runner_run(TESTS.get("echo_main_badconfig"), _self))
                }),
            ]);
        defer! {
            test.drop();
        }
        main().await
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_new() {
        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = <EchoHandler as runner::handler::Factory<Command>>::new(command.clone());
        let runner = <Runner as runner::runner::Factory<Runner, EchoHandler>>::new(handler.clone());
        assert_eq!(runner.handler, handler);
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_runner_cmd_start() {
        let test = TESTS
            .test("runner_cmd_start")
            .expecting(vec![
                "Runner::listeners(true)",
                "Runner::get_handler(true)",
                "Runner::start(true): EchoHandler { command: Command { config: Config { base: BaseConfig { log: Some(LogConfig { level: Info }) }, listeners: {\"http\": Config { host: 127.0.0.1, port: 8787 }}, hostname: \"echo\" }, name: \"somecommand\" } }"
            ])
            .with_patches(vec![
                patch1(Runner::get_handler, |_self| {
                    Patch::runner_get_handler(TESTS.get("runner_cmd_start"), _self)
                }),
                patch1(Runner::listeners, |_self| {
                    Patch::runner_listeners(TESTS.get("runner_cmd_start"), _self)
                }),
                patch2(Listeners::bind, |_self, handler| {
                    Box::pin(Patch::listeners_bind(
                        TESTS.get("runner_cmd_start"),
                        _self,
                        handler,
                    ))
                }),
            ]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let runner = Runner { handler };
        let result = runner
            .cmd_start()
            .await
            .map_err(|e| format!("TEST FAILED: {}", e));
        assert!(result.is_ok(), "{}", result.unwrap_err());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_get_handler() {
        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let runner = Runner {
            handler: handler.clone(),
        };
        assert_eq!(runner.get_handler(), &handler);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_http_host() {
        let test = TESTS
            .test("runner_http_host")
            .expecting(vec!["Runner::config(true): \"listeners.http.host\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config::<EchoHandler>(
                    TESTS.get("runner_http_host"),
                    Some(core::Primitive::String("::".to_string())),
                    _self,
                    key,
                )
            })]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let runner = Runner { handler };
        assert_eq!(
            "::".parse::<IpAddr>().unwrap(),
            runner.http_host().expect("Failed to get HTTP host")
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_http_host_noconfig() {
        let test = TESTS
            .test("runner_http_host_noconfig")
            .expecting(vec!["Runner::config(true): \"listeners.http.host\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config::<EchoHandler>(
                    TESTS.get("runner_http_host_noconfig"),
                    None,
                    _self,
                    key,
                )
            })]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let runner = Runner { handler };
        let host = runner.http_host();
        assert!(host.is_err());
        let err_msg = host.unwrap_err().to_string();
        assert!(
            err_msg.contains("Missing 'listeners.http.host' config"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_http_host_badconfig() {
        let test = TESTS
            .test("runner_http_host_badconfig")
            .expecting(vec!["Runner::config(true): \"listeners.http.host\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config::<EchoHandler>(
                    TESTS.get("runner_http_host_badconfig"),
                    Some(core::Primitive::String("NOT AN IP ADDRESS".to_string())),
                    _self,
                    key,
                )
            })]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let runner = Runner { handler };
        let host = runner.http_host();
        assert!(host.is_err());
        let err_msg = host.unwrap_err().to_string();
        assert!(
            err_msg.contains("Invalid host 'NOT AN IP ADDRESS': invalid IP address syntax"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_http_host_badconfig_type() {
        let test = TESTS
            .test("runner_http_host_badconfig_type")
            .expecting(vec!["Runner::config(true): \"listeners.http.host\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config::<EchoHandler>(
                    TESTS.get("runner_http_host_badconfig_type"),
                    Some(core::Primitive::U32(1717)),
                    _self,
                    key,
                )
            })]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let runner = Runner { handler };
        let host = runner.http_host();
        assert!(host.is_err());
        let err_msg = host.unwrap_err().to_string();
        assert!(
            err_msg.contains("Unexpected type for 'listeners.http.host': U32(1717)"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_http_port() {
        let test = TESTS
            .test("runner_http_port")
            .expecting(vec!["Runner::config(true): \"listeners.http.port\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config::<EchoHandler>(
                    TESTS.get("runner_http_port"),
                    Some(core::Primitive::U32(2323)),
                    _self,
                    key,
                )
            })]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let runner = Runner { handler };
        assert_eq!(
            2323,
            runner
                .http_port()
                .expect("Failed to get HTTP listener port")
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_http_port_noconfig() {
        let test = TESTS
            .test("runner_http_port_noconfig")
            .expecting(vec!["Runner::config(true): \"listeners.http.port\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config::<EchoHandler>(
                    TESTS.get("runner_http_port_noconfig"),
                    None,
                    _self,
                    key,
                )
            })]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let runner = Runner { handler };
        let port = runner.http_port();
        assert!(port.is_err());
        let err_msg = port.unwrap_err().to_string();
        assert!(
            err_msg.contains("Missing 'listeners.http.port' config"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_http_port_badconfig() {
        let test = TESTS
            .test("runner_http_port_badconfig")
            .expecting(vec!["Runner::config(true): \"listeners.http.port\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config::<EchoHandler>(
                    TESTS.get("runner_http_port_badconfig"),
                    Some(core::Primitive::String("NOT A PORT".to_string())),
                    _self,
                    key,
                )
            })]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let runner = Runner { handler };
        let port = runner.http_port();
        assert!(port.is_err());
        let err_msg = port.unwrap_err().to_string();
        assert!(
            err_msg.contains("Unexpected type for 'listeners.http.port': String(\"NOT A PORT\")"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_listeners() {
        let test = TESTS
            .test("runner_endpoint")
            .expecting(vec!["Runner::http_host(true)", "Runner::http_port(true)"])
            .with_patches(vec![
                patch1(Runner::http_host, |_self| {
                    Patch::runner_http_host(TESTS.get("runner_endpoint"), _self)
                }),
                patch1(Runner::http_port, |_self| {
                    Patch::runner_http_port(TESTS.get("runner_endpoint"), _self)
                }),
            ]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let runner = Runner { handler };
        let listeners = runner.listeners().unwrap();
        let http_endpoint = listeners.endpoints.get("http").unwrap();
        assert_eq!(http_endpoint.name, "http");
        assert_eq!(http_endpoint.host.to_string(), "7.7.7.7");
        assert_eq!(http_endpoint.port, 7777);
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_runner_run() {
        let test = TESTS
            .test("runner_run")
            .expecting(vec!["Runner::start_log(true)", "Runner::handle(true)"])
            .with_patches(vec![
                patch1(Runner::start_log, |_self| {
                    RunnerPatch::runner_start_log(TESTS.get("runner_run"), _self)
                }),
                patch1(Runner::handle, |_self| {
                    Box::pin(RunnerPatch::runner_handle(TESTS.get("runner_run"), _self))
                }),
            ]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let runner = Runner { handler };
        assert!(runner.run().await.is_ok());
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_runner_handle() {
        let test = TESTS
            .test("runner_handle")
            .expecting(vec![
                "Runner::resolve_command(true)",
                "Runner::configured_command(true)",
            ])
            .with_patches(vec![patch1(Runner::resolve_command, |_self| {
                RunnerPatch::runner_resolve_command(TESTS.get("runner_handle"), _self)
            })]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let runner = Runner { handler };
        assert!(runner.handle().await.is_ok());
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_runner_commands() {
        let test = TESTS
            .test("runner_commands")
            .expecting(vec!["Runner::cmd_start(true)"])
            .with_patches(vec![patch1(Runner::cmd_start, |_self| {
                Box::pin(Patch::runner_cmd_start(TESTS.get("runner_commands"), _self))
            })]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let handler = EchoHandler { command };
        let runner = Runner { handler };
        let commands = runner.commands();
        match commands.get("start") {
            Some(command) => {
                command(&(Arc::new(runner.clone()) as Arc<dyn runner::runner::Runner<EchoHandler>>))
                    .await
                    .unwrap()
            }
            None => panic!("expected default command"),
        }
    }
}
