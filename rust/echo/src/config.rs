use crate::{args::Args, listener};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_yaml::Value;
use toolshed_runner::config::Provider;
use toolshed_runner::{config, log, EmptyResult};

#[derive(Clone, Debug, Deserialize, Serialize)]
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
        mut config: Box<Self>,
    ) -> Result<Box<Config>, config::SafeError> {
        if let Some(level) = Self::log_level_override(args.clone())? {
            config.set_log(level)?;
        }
        Self::override_config_address(args, &mut config)?;
        Ok(config)
    }
}

impl config::Provider for Config {
    fn serialized(&self) -> Option<Value> {
        serde_yaml::to_value(self).ok()
    }

    fn set_log(&mut self, level: log::Level) -> EmptyResult {
        if let Some(log) = self.base.log.as_mut() {
            log.level = level;
        }
        Ok(())
    }
}

impl Config {
    fn override_config_address(args: config::ArcSafeArgs, config: &mut Box<Self>) -> EmptyResult {
        if let Some(echo_args) = args.as_any().downcast_ref::<Args>() {
            if let Some(address) = echo_args.address.clone() {
                config.listener.address = address.parse()?;
            }
            if let Some(port) = echo_args.port {
                config.listener.port = port as u16;
            }
        }
        Ok(())
    }
}
