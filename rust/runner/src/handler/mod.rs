use crate::command::Command;
use std::fmt;
use toolshed_core as core;

pub trait Factory<T>: Send + Sync
where
    T: Command + Sized,
{
    fn new(command: T) -> Self;
}

pub trait Handler: fmt::Debug + Send + Sync {
    fn get_command(&self) -> Box<&dyn Command>;

    fn config(&self, key: &str) -> Option<core::Primitive> {
        self.get_command().get_config().get(key)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        config::Provider as _,
        test::{
            dummy::{Dummy, DummyCommand, DummyConfig, DummyHandler},
            patch::Patch,
        },
    };
    use guerrilla::{patch1, patch2};
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use toolshed_test as ttest;

    static PATCHES: Lazy<ttest::Patches> = Lazy::new(ttest::Patches::new);
    static SPY: Lazy<ttest::Spy> = Lazy::new(ttest::Spy::new);
    static TESTS: Lazy<ttest::Tests> = Lazy::new(|| ttest::Tests::new(&SPY, &PATCHES));

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_config() {
        let test = TESTS
            .test("runner_config")
            .expecting(vec![
                "Handler::get_command(true)",
                "Command::get_config(true)",
                "Config::get(true): \"SOME.KEY.PATH\"",
            ])
            .with_patches(vec![
                patch1(DummyHandler::get_command, |_self| {
                    Patch::handler_command(TESTS.get("runner_config"), _self)
                }),
                patch1(DummyCommand::get_config, |_self| {
                    Patch::command_config(TESTS.get("runner_config"), _self)
                }),
                patch2(DummyConfig::get, |_self, key| {
                    Patch::config_get(TESTS.get("runner_config"), _self, key)
                }),
            ]);
        defer! {
            test.drop()
        }

        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let handler = Dummy::handler(command.clone()).unwrap();
        let mut failure = "";

        if let Some(core::Primitive::String(result)) = handler.config("SOME.KEY.PATH") {
            assert_eq!(result, "BOOM");
        } else {
            failure = "Expected a Primitive::String, but got something else.";
        }
        assert_eq!(failure, "");
    }
}
