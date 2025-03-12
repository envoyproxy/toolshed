use crate::{
    args::Args,
    command::Command,
    config::Config,
    handler::{EchoHandler, Handler},
    listener::{Endpoint, Listener},
};
use async_trait::async_trait;
use axum::{routing::any, Router};
use clap::Parser;
use serde::{Deserialize, Serialize};
use std::net::IpAddr;
use toolshed_runner::{command, config, config::Factory, runner, runner::Runner as _, EmptyResult};

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Runner {
    pub command: Command,
}

#[async_trait]
trait EchoRunner: toolshed_runner::runner::Runner {
    fn router(&self) -> Result<Router, Box<dyn std::error::Error + Send + Sync>> {
        Ok(Router::new()
            .route("/", any(EchoHandler::handle_root))
            .route("/{*path}", any(EchoHandler::handle_path)))
    }

    async fn cmd_start(&self) -> EmptyResult {
        self.start(self.endpoint()?).await?;
        Ok(())
    }

    async fn start(
        &self,
        endpoint: Endpoint,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        Ok(axum::serve(endpoint.bind().await, self.router()?)
            .with_graceful_shutdown(runner::ctrl_c())
            .await?)
    }

    fn endpoint(&self) -> Result<Endpoint, Box<dyn std::error::Error + Send + Sync>>;

    fn listener_host(&self) -> Result<IpAddr, Box<dyn std::error::Error + Send + Sync>> {
        match self.config("listener.host") {
            Some(config::Primitive::String(addr)) => match addr.parse::<IpAddr>() {
                Ok(ip) => Ok(ip),
                Err(e) => Err(format!("Invalid host '{}': {}", addr, e).into()),
            },
            Some(other) => Err(format!("Unexpected type for 'listener.host': {:?}", other).into()),
            None => Err("Missing 'listener.host' config".into()),
        }
    }

    fn listener_port(&self) -> Result<u16, Box<dyn std::error::Error + Send + Sync>> {
        match self.config("listener.port") {
            Some(config::Primitive::U32(port)) => Ok(port as u16),
            Some(other) => Err(format!("Unexpected type for 'listener.port': {:?}", other).into()),
            None => Err("Missing 'listener.port' config".into()),
        }
    }
}

impl Runner {}

#[async_trait]
impl EchoRunner for Runner {
    fn endpoint(&self) -> Result<Endpoint, Box<dyn std::error::Error + Send + Sync>> {
        Ok(Endpoint {
            host: self.listener_host()?,
            port: self.listener_port()?,
        })
    }
}

impl runner::Factory<Runner, Command> for Runner {
    fn new(command: Command) -> Self {
        Self { command }
    }
}

#[async_trait]
impl runner::Runner for Runner {
    runner!(
    command,
    {
        "start" => Self::cmd_start,
    });

    async fn handle(&self) -> EmptyResult {
        self.resolve_command().unwrap()(&(Box::new(self.clone()) as Box<dyn runner::Runner>)).await
    }
}

pub async fn main() {
    let args = Args::parse();
    match Config::from_yaml(Box::new(args)).await {
        Ok(config) => {
            let command = <Command as command::Factory<Command, Config>>::new(
                *config,
                Some("start".to_string()),
            );
            let runner = <Runner as runner::Factory<Runner, Command>>::new(command);
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
    use crate::listener;
    use crate::test::patch::Patch;
    use axum::Router;
    use bytes::Bytes;
    use guerrilla::{patch0, patch1, patch2, patch4, patch5};
    use http_body_util::Empty;
    use hyper::Request;
    use mockall::mock;
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use std::net::{IpAddr, SocketAddr};
    use toolshed_runner::test::{
        patch::{Patch as RunnerPatch, Patches},
        spy::Spy,
        Tests,
    };
    use tower::ServiceExt as _;

    static PATCHES: Lazy<Patches> = Lazy::new(Patches::new);
    static SPY: Lazy<Spy> = Lazy::new(Spy::new);
    static TESTS: Lazy<Tests> = Lazy::new(|| Tests::new(&SPY, &PATCHES));

    mock! {
        Endpoint {}

        #[async_trait]
        impl listener::Listener for Endpoint {
            async fn bind(&self) -> tokio::net::TcpListener;
            fn socket_address(&self) -> SocketAddr;
        }
    }

    async fn _test_request(
        service: axum::routing::RouterIntoService<http_body_util::Empty<bytes::Bytes>>,
        path: &str,
        expected: &str,
    ) {
        let request = Request::builder()
            .uri(path)
            .body(Empty::<Bytes>::new())
            .unwrap();
        let response = service.oneshot(request).await.unwrap();
        let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .unwrap();
        assert_eq!(String::from_utf8_lossy(&body_bytes), expected.to_string());
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
                patch0(Args::parse, || {
                    Patch::args_parse(TESTS.get("echo_main").unwrap())
                }),
                patch1(Config::from_yaml, |args| {
                    let test = TESTS.get("echo_main").unwrap();
                    test.lock().unwrap().patch_index(1);
                    Box::pin(Patch::config_from_yaml(test, args))
                }),
                patch2(
                    <Command as command::Factory<Command, Config>>::new,
                    |config, command| {
                        Patch::runner_command_from_config(
                            TESTS.get("echo_main").unwrap(),
                            config,
                            command,
                        )
                    },
                ),
                patch1(
                    <Runner as runner::Factory<Runner, Command>>::new,
                    |command| Patch::runner_factory(TESTS.get("echo_main").unwrap(), command),
                ),
                patch1(Runner::run, |_self| {
                    Box::pin(Patch::runner_run(TESTS.get("echo_main").unwrap(), _self))
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
                    Patch::args_parse(TESTS.get("echo_main_badconfig").unwrap())
                }),
                patch1(Config::from_yaml, |args| {
                    let test = TESTS.get("echo_main_badconfig").unwrap();
                    test.lock().unwrap().fail().patch_index(1);
                    Box::pin(Patch::config_from_yaml(test, args))
                }),
                patch2(
                    <Command as command::Factory<Command, Config>>::new,
                    |config, command| {
                        Patch::runner_command_from_config(
                            TESTS.get("echo_main_badconfig").unwrap(),
                            config,
                            command,
                        )
                    },
                ),
                patch1(
                    <Runner as runner::Factory<Runner, Command>>::new,
                    |command| {
                        Patch::runner_factory(TESTS.get("echo_main_badconfig").unwrap(), command)
                    },
                ),
                patch1(Runner::run, |_self| {
                    Box::pin(Patch::runner_run(
                        TESTS.get("echo_main_badconfig").unwrap(),
                        _self,
                    ))
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
        let runner = <Runner as runner::Factory<Runner, Command>>::new(command.clone());
        assert_eq!(runner.command, command);
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_runner_cmd_start() {
        let test = TESTS
            .test("runner_cmd_start")
            .expecting(vec![
                "Runner::endpoint(true)",
                "Runner::start(true): Endpoint { host: 0.0.0.0, port: 1717 }",
            ])
            .with_patches(vec![
                patch2(Runner::start, |_self, endpoint| {
                    Box::pin(Patch::runner_start(
                        TESTS.get("runner_cmd_start").unwrap(),
                        _self,
                        endpoint,
                    ))
                }),
                patch1(Runner::endpoint, |_self| {
                    Patch::runner_endpoint(TESTS.get("runner_cmd_start").unwrap(), _self)
                }),
            ]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let runner = Runner { command };
        let result = runner
            .cmd_start()
            .await
            .map_err(|e| format!("TEST FAILED: {}", e));
        assert!(result.is_ok(), "{}", result.unwrap_err());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_endpoint() {
        let test = TESTS
            .test("runner_endpoint")
            .expecting(vec![
                "Runner::listener_host(true)",
                "Runner::listener_port(true)",
            ])
            .with_patches(vec![
                patch1(Runner::listener_host, |_self| {
                    Patch::runner_listener_host(TESTS.get("runner_endpoint").unwrap(), _self)
                }),
                patch1(Runner::listener_port, |_self| {
                    Patch::runner_listener_port(TESTS.get("runner_endpoint").unwrap(), _self)
                }),
            ]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let runner = Runner { command };
        let endpoint = runner.endpoint().unwrap();
        assert_eq!(endpoint.host.to_string(), "7.7.7.7");
        assert_eq!(endpoint.port, 7777);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_listener_host() {
        let test = TESTS
            .test("runner_listener_host")
            .expecting(vec!["Runner::config(true): \"listener.host\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config(
                    TESTS.get("runner_listener_host").unwrap(),
                    Some(config::Primitive::String("::".to_string())),
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
        let runner = Runner { command };
        assert_eq!(
            "::".parse::<IpAddr>().unwrap(),
            runner.listener_host().expect("Failed to get listener port")
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_listener_host_noconfig() {
        let test = TESTS
            .test("runner_listener_host_noconfig")
            .expecting(vec!["Runner::config(true): \"listener.host\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config(
                    TESTS.get("runner_listener_host_noconfig").unwrap(),
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
        let runner = Runner { command };
        let host = runner.listener_host();
        assert!(host.is_err());
        let err_msg = host.unwrap_err().to_string();
        assert!(
            err_msg.contains("Missing 'listener.host' config"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_listener_host_badconfig() {
        let test = TESTS
            .test("runner_listener_host_badconfig")
            .expecting(vec!["Runner::config(true): \"listener.host\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config(
                    TESTS.get("runner_listener_host_badconfig").unwrap(),
                    Some(config::Primitive::String("NOT AN IP ADDRESS".to_string())),
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
        let runner = Runner { command };
        let host = runner.listener_host();
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
    fn test_runner_listener_host_badconfig_type() {
        let test = TESTS
            .test("runner_listener_host_badconfig_type")
            .expecting(vec!["Runner::config(true): \"listener.host\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config(
                    TESTS.get("runner_listener_host_badconfig_type").unwrap(),
                    Some(config::Primitive::U32(1717)),
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
        let runner = Runner { command };
        let host = runner.listener_host();
        assert!(host.is_err());
        let err_msg = host.unwrap_err().to_string();
        assert!(
            err_msg.contains("Unexpected type for 'listener.host': U32(1717)"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_listener_port() {
        let test = TESTS
            .test("runner_listener_port")
            .expecting(vec!["Runner::config(true): \"listener.port\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config(
                    TESTS.get("runner_listener_port").unwrap(),
                    Some(config::Primitive::U32(2323)),
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
        let runner = Runner { command };
        assert_eq!(
            2323,
            runner.listener_port().expect("Failed to get listener port")
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_listener_port_noconfig() {
        let test = TESTS
            .test("runner_listener_port_noconfig")
            .expecting(vec!["Runner::config(true): \"listener.port\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config(
                    TESTS.get("runner_listener_port_noconfig").unwrap(),
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
        let runner = Runner { command };
        let port = runner.listener_port();
        assert!(port.is_err());
        let err_msg = port.unwrap_err().to_string();
        assert!(
            err_msg.contains("Missing 'listener.port' config"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_listener_port_badconfig() {
        let test = TESTS
            .test("runner_listener_port_badconfig")
            .expecting(vec!["Runner::config(true): \"listener.port\""])
            .with_patches(vec![patch2(Runner::config, |_self, key| {
                RunnerPatch::runner_config(
                    TESTS.get("runner_listener_port_badconfig").unwrap(),
                    Some(config::Primitive::String("NOT A PORT".to_string())),
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
        let runner = Runner { command };
        let port = runner.listener_port();
        assert!(port.is_err());
        let err_msg = port.unwrap_err().to_string();
        assert!(
            err_msg.contains("Unexpected type for 'listener.port': String(\"NOT A PORT\")"),
            "Unexpected error: {}",
            err_msg
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_runner_router() {
        let test = TESTS
            .test("runner_router")
            .expecting(vec![
                "Router::new(true)",
                "Handler::handle_root(true)",
                "Handler::handle_path(true): some/path",
            ])
            .with_patches(vec![
                patch0(Router::new, || {
                    let test = TESTS.get("runner_router").unwrap();
                    test.lock().unwrap().patch_index(0);
                    Patch::router_new(test)
                }),
                patch4(EchoHandler::handle_root, |method, headers, params, body| {
                    Box::pin(Patch::runner_handle_root(
                        TESTS.get("runner_router").unwrap(),
                        method,
                        headers,
                        params,
                        body,
                    ))
                }),
                patch5(
                    EchoHandler::handle_path,
                    |method, headers, params, path, body| {
                        Box::pin(Patch::runner_handle_path(
                            TESTS.get("runner_router").unwrap(),
                            method,
                            headers,
                            params,
                            path,
                            body,
                        ))
                    },
                ),
            ]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let runner = Runner { command };
        let router = runner.router().unwrap();
        let service = router.into_service();
        _test_request(service.clone(), "/nowhere", "The future").await;
        _test_request(service.clone(), "/", "ROOT HANDLED").await;
        _test_request(service, "/some/path", "PATH HANDLED").await;
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_runner_start() {
        let test = TESTS
            .test("runner_start")
            .expecting(vec![
                "Runner::router(true)",
                "axum::serve(true)",
                "axum::serve::Serve::with_graceful_shutdown(true)",
                "ctrl_c(true)",
            ])
            .with_patches(vec![
                patch1(Runner::router, |_self| {
                    Patch::runner_router(TESTS.get("runner_start").unwrap(), _self)
                }),
                patch0(runner::ctrl_c, || {
                    Box::pin(Patch::ctrl_c(TESTS.get("runner_start").unwrap()))
                }),
                patch2(axum::serve, |listener, router| {
                    let test = TESTS.get("runner_start").unwrap();
                    test.lock().unwrap().patch_index(2);
                    Patch::axum_serve(test, listener, router)
                }),
                patch2(axum::serve::Serve::with_graceful_shutdown, |_self, fun| {
                    let test = TESTS.get("runner_start").unwrap();
                    test.lock().unwrap().patch_index(3);
                    Patch::axum_serve_with_graceful_shutdown(test, _self, Box::pin(fun))
                }),
            ]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let runner = Runner { command };
        let host: IpAddr = "127.0.0.1".parse().unwrap();
        let port = 1717;
        let endpoint = listener::Endpoint { host, port };
        assert!(runner.start(endpoint).await.is_ok());
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_runner_run() {
        let test = TESTS
            .test("runner_run")
            .expecting(vec!["Runner::start_log(true)", "Runner::handle(true)"])
            .with_patches(vec![
                patch1(Runner::start_log, |_self| {
                    RunnerPatch::runner_start_log(TESTS.get("runner_run").unwrap(), _self)
                }),
                patch1(Runner::handle, |_self| {
                    Box::pin(RunnerPatch::runner_handle(
                        TESTS.get("runner_run").unwrap(),
                        _self,
                    ))
                }),
            ]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let runner = Runner { command };
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
                RunnerPatch::runner_resolve_command(TESTS.get("runner_handle").unwrap(), _self)
            })]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let runner = Runner { command };
        assert!(runner.handle().await.is_ok());
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_runner_commands() {
        let test = TESTS
            .test("runner_commands")
            .expecting(vec!["Runner::cmd_start(true)"])
            .with_patches(vec![patch1(Runner::cmd_start, |_self| {
                Box::pin(Patch::runner_cmd_start(
                    TESTS.get("runner_commands").unwrap(),
                    _self,
                ))
            })]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command = Command { config, name };
        let runner = Runner { command };
        let commands = runner.commands();
        match commands.get("start") {
            Some(command) => command(&(Box::new(runner.clone()) as Box<dyn runner::Runner>))
                .await
                .unwrap(),
            None => panic!("expected default command"),
        }
    }
}
