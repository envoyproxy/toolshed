use crate::{args::Args, config::Config, command::Command};
use crate::{
    handler::{EchoHandler, Handler},
    listener::{Endpoint, Listener},
};
use async_trait::async_trait;
use axum::{routing::any, Router};
use clap::Parser;
use serde::{Deserialize, Serialize};
use std::net::IpAddr;
use tokio::signal;
use toolshed_runner::config::Factory;
use toolshed_runner::runner::Runner as _;
use toolshed_runner::{config, command, runner, EmptyResult};

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Runner {
    pub command: Command,
}

impl Runner {
    async fn cmd_start(&self) -> EmptyResult {
        let port = match self.config("listener.port") {
            Some(config::Primitive::U32(port)) => port as u16,
            _ => return Err("Missing or invalid 'listener.port' config".into()),
        };
        let address: IpAddr = match self.config("listener.address") {
            Some(config::Primitive::String(addr)) => addr.parse()?,
            _ => return Err("Missing or invalid 'listener.address' config".into()),
        };
        let endpoint = Endpoint { address, port };
        let app = Router::new()
            .route("/", any(EchoHandler::handle_root))
            .route("/*path", any(EchoHandler::handle_path));
        let listener = endpoint.bind().await;
        let graceful = async {
            signal::ctrl_c().await.unwrap();
        };
        let server = axum::serve(listener, app);
        tokio::select! {
            _ = server => {}
            _ = graceful => {}
        }
        Ok(())
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
    let config = match Config::from_yaml(Box::new(args)).await {
        Ok(cfg) => cfg,
        Err(e) => {
            eprintln!("Error loading config:\n {}", e);
            std::process::exit(1);
        }
    };
    let command =
        <Command as command::Factory<Command, Config>>::new(*config, Some("start".to_string()));
    let runner = <Runner as runner::Factory<Runner, Command>>::new(command);
    runner.run().await.unwrap();
}
