use crate::config::Config;
use serde::{Deserialize, Serialize};
use toolshed_runner as runner;

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct Command {
    pub config: Config,
    #[serde(default = "Command::default_name")]
    pub name: String,
}

impl Command {
    fn default_name() -> String {
        "start".to_string()
    }
}

impl runner::command::Factory<Command, Config> for Command {
    fn new(config: Config, name: Option<String>) -> Self {
        let name = match name {
            Some(name) => name,
            _ => Self::default_name(),
        };
        Self { config, name }
    }
}

impl runner::command::Command for Command {
    fn get_name(&self) -> &str {
        &self.name
    }

    fn get_config(&self) -> Box<&dyn runner::config::Provider> {
        Box::new(&self.config)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test::patch::Patch;
    use guerrilla::patch0;
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use toolshed_runner::command::Command as _;
    use toolshed_test as ttest;

    static PATCHES: Lazy<ttest::Patches> = Lazy::new(ttest::Patches::new);
    static SPY: Lazy<ttest::Spy> = Lazy::new(ttest::Spy::new);
    static TESTS: Lazy<ttest::Tests> = Lazy::new(|| ttest::Tests::new(&SPY, &PATCHES));

    #[test]
    #[serial(toolshed_lock)]
    fn test_command_new() {
        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "somecommand".to_string();
        let command: Command =
            runner::command::Factory::<Command, Config>::new(config.clone(), Some(name));
        assert_eq!(command.name, "somecommand");
        assert_eq!(command.config, config);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_command_new_default() {
        let test = TESTS
            .test("command_default_name")
            .expecting(vec!["Command::default_name(true)"])
            .with_patches(vec![patch0(Command::default_name, || {
                Patch::command_default_name(TESTS.get("command_default_name"))
            })]);
        defer! {
            test.drop();
        }

        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let command: Command =
            runner::command::Factory::<Command, Config>::new(config.clone(), None);
        assert_eq!(command.name, "DEFAULT_NAME");
        assert_eq!(command.config, config);
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_command_get_name() {
        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "TEST COMMAND NAME".to_string();
        let command: Command = Command { config, name };
        assert_eq!(command.get_name(), "TEST COMMAND NAME");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_command_get_config() {
        let config = serde_yaml::from_str::<Config>("").expect("Unable to parse yaml");
        let name = "TEST COMMAND NAME".to_string();
        let command: Command = Command {
            config: config.clone(),
            name,
        };
        assert_eq!(
            command.get_config().as_any().downcast_ref::<Config>(),
            Some(&config)
        );
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_command_default_name() {
        assert_eq!(Command::default_name(), "start".to_string());
    }
}
