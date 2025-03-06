use crate as toolshed_runner;
use crate::{command, config, log, runner, EmptyResult};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_yaml::Mapping;
use serde_yaml::Value;
use std::error::Error;

pub trait Loggable {
    fn log(&self) -> config::LogConfig;
}

#[async_trait]
impl config::Factory<config::LogConfig> for config::LogConfig {}

#[async_trait]
impl config::Factory<config::BaseConfig> for config::BaseConfig {}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct DummyConfig {
    pub log: config::LogConfig,
}

impl Loggable for DummyConfig {
    fn log(&self) -> config::LogConfig {
        self.log.clone()
    }
}

#[async_trait]
impl config::Provider for DummyConfig {
    fn get(&self, _key: &str) -> Option<config::Primitive> {
        None
    }

    fn resolve(&self, current: &Value, _keys: &[&str]) -> Option<Value> {
        Some(current.clone())
    }

    fn serialized(&self) -> Option<Value> {
        serde_yaml::to_value(self).ok()
    }
}

#[derive(Debug, Deserialize)]
pub struct DummyConfig2 {
    #[allow(dead_code)]
    pub log: config::LogConfig,
}

#[async_trait]
impl config::Provider for DummyConfig2 {
    fn serialized(&self) -> Option<Value> {
        let mut map = Mapping::new();
        map.insert(
            Value::String("key".to_string()),
            Value::String("serialized_value".to_string()),
        );
        Some(Value::Mapping(map))
    }
}

impl config::Provider for config::LogConfig {
    fn serialized(&self) -> Option<Value> {
        serde_yaml::to_value(self).ok()
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct DummyCommand {
    pub config: DummyConfig,
    pub name: String,
}

impl command::Command for DummyCommand {
    fn get_name(&self) -> &str {
        &self.name
    }

    fn get_config(&self) -> Box<&dyn config::Provider> {
        Box::new(&self.config)
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct DummyRunner {
    pub command: DummyCommand,
}

impl DummyRunner {
    async fn cmd_default(&self) -> EmptyResult {
        Ok(())
    }

    async fn cmd_other(&self) -> EmptyResult {
        Ok(())
    }
}

pub struct Dummy {}

impl Dummy {
    pub fn config() -> Result<DummyConfig, Box<dyn Error>> {
        let level = log::Level::Trace;
        let log = config::LogConfig { level };
        Ok(DummyConfig { log })
    }

    pub fn command(config: DummyConfig, name: String) -> Result<DummyCommand, Box<dyn Error>> {
        Ok(DummyCommand { config, name })
    }

    pub fn runner(command: DummyCommand) -> Result<DummyRunner, Box<dyn Error>> {
        Ok(DummyRunner { command })
    }
}

#[async_trait]
impl runner::Runner for DummyRunner {
    runner!(
    command,
    {
        "other" => Self::cmd_other,
        "default" => Self::cmd_default,
    });

    async fn handle(&self) -> EmptyResult {
        self.resolve_command().unwrap()(&(Box::new(self.clone()) as Box<dyn runner::Runner>)).await
    }
}
