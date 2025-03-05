use crate::config::Config;
use serde::{Deserialize, Serialize};
use toolshed_runner::{config, command};

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Command {
    pub config: Config,
    #[serde(default = "Command::default_name")]
    pub name: String,
}

impl Command {
    fn default_name() -> String {
        "default".to_string()
    }
}

impl command::Factory<Command, Config> for Command {
    fn new(config: Config, name: Option<String>) -> Self {
        if let Some(name) = name {
            Self { config, name }
        } else {
            Self {
                config,
                name: Self::default_name(),
            }
        }
    }
}

impl command::Command for Command {
    fn get_name(&self) -> &str {
        &self.name
    }

    fn get_config(&self) -> Box<&dyn config::Provider> {
        Box::new(&self.config)
    }
}
