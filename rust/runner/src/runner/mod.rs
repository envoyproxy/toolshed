use crate::command::Command;
use crate::{config, log, EmptyResult};
use ::log::LevelFilter;
use as_any::AsAny;
use async_trait::async_trait;
use env_logger::Builder;
use std::any::Any;
use std::collections::HashMap;
use std::error::Error;
use std::fmt;
use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;

pub type CommandFn = Arc<
    dyn Fn(&Box<dyn Runner>) -> Pin<Box<dyn Future<Output = EmptyResult> + Send>> + Send + Sync,
>;
pub type CommandsFn<'a> = HashMap<&'a str, CommandFn>;

pub trait Factory<T, R>: Send + Sync
where
    T: Runner + Sized,
    R: Command + Sized,
{
    fn new(command: R) -> Self;
}

#[macro_export]
macro_rules! runner {
    ($command:ident, { $( $cmd_name:literal => $cmd_fn:expr ),* $(,)? }) => {
        // Requires:
        //
        // use as_any::Downcast;
        //
        // in the calling module

        fn get_command(&self) -> &dyn toolshed_runner::command::Command {
            &self.$command
        }

        fn commands(&self) -> toolshed_runner::runner::CommandsFn {
            let mut commands: toolshed_runner::runner::CommandsFn = std::collections::HashMap::new();
            $(
                commands.insert($cmd_name, std::sync::Arc::new(|s: &Box<dyn toolshed_runner::runner::Runner>| {
                    let s = s.as_any().downcast_ref::<Self>().expect("Some err").clone();
                    Box::pin(async move {$cmd_fn(&s).await})
                }));
            )*
            commands
        }
    };
}

pub struct CommandError {
    message: String,
}

impl fmt::Display for CommandError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "CommandError: {}", self.message)
    }
}

impl fmt::Debug for CommandError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "CommandError: {}", self.message)
    }
}

impl Error for CommandError {}

#[async_trait]
pub trait Runner: Any + AsAny + Send + Sync {
    fn commands(&self) -> CommandsFn;
    fn get_command(&self) -> &dyn Command;
    async fn handle(&self) -> EmptyResult;

    fn config(&self, key: &str) -> Option<config::Primitive> {
        self.get_command().get_config().get(key)
    }

    fn resolve_command(&self) -> Result<CommandFn, CommandError> {
        let name = self.get_command().get_name();
        let commands = self.commands();
        match commands.get(name) {
            Some(command) => Ok(command.clone()),
            None => Err(CommandError {
                message: "No such command".to_string(),
            }),
        }
    }

    async fn run(&self) -> EmptyResult {
        self.start_log().unwrap();
        self.handle().await
    }

    fn start_log(&self) -> EmptyResult {
        if let Some(config::Primitive::String(level_str)) = self.config("log.level") {
            if let Ok(level) = level_str.parse::<log::Level>() {
                Builder::new().filter(None, LevelFilter::from(level)).init();
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test::{
        dummy::{Dummy, DummyCommand, DummyConfig, DummyRunner},
        patch::Patch,
        spy::Spy,
    };
    use config::Provider;
    use scopeguard::defer;
    use serial_test::serial;

    static SPY: once_cell::sync::Lazy<Spy> = once_cell::sync::Lazy::new(Spy::new);

    #[test]
    #[serial(my_global_lock)]
    fn test_runner_config() {
        let testid = "runner_config";
        let expected = vec![
            "Runner::get_command(true)",
            "Command::get_config(true)",
            "Config::get(true): \"SOME.KEY.PATH\"",
        ];
        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(command).unwrap();
        let guards = [
            guerrilla::patch1(DummyRunner::get_command, |_self| {
                Patch::runner_command(&SPY, "runner_config", true, _self)
            }),
            guerrilla::patch1(DummyCommand::get_config, |_self| {
                Patch::command_config(&SPY, "runner_config", true, _self)
            }),
            guerrilla::patch2(DummyConfig::get, |_self, key| {
                Patch::config_get(&SPY, "runner_config", true, _self, key)
            }),
        ];
        defer! {
            let calls = SPY.get(testid);
            drop(guards);
            SPY.clear(testid);
            assert_eq!(*calls, expected);
        }
        let mut failure = "";

        if let Some(config::Primitive::String(result)) = runner.config("SOME.KEY.PATH") {
            assert_eq!(result, "BOOM");
        } else {
            failure = "Expected a Primitive::String, but got something else.";
        }
        assert_eq!(failure, "");
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(my_global_lock)]
    async fn test_runner_resolve_command() {
        let testid = "runner_resolve_command";
        let expected = vec![
            "Runner::get_command(true)",
            "Command::get_name(true)",
            "Runner::commands(true)",
            "Runner::configured_command(true)",
        ];
        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(command).unwrap();
        let guards = [
            guerrilla::patch1(DummyRunner::get_command, |_self| {
                Patch::runner_command(&SPY, "runner_resolve_command", true, _self)
            }),
            guerrilla::patch1(DummyCommand::get_name, |_self| {
                Patch::command_get_name(&SPY, "runner_resolve_command", true, _self)
            }),
            guerrilla::patch1(DummyRunner::commands, |_self| {
                Patch::runner_commands(&SPY, "runner_resolve_command", true, _self)
            }),
        ];
        defer! {
            let calls = SPY.get(testid);
            drop(guards);
            SPY.clear(testid);
            assert_eq!(*calls, expected);
        }
        let command = runner.resolve_command().unwrap();
        let _ = command(&(Box::new(runner.clone()) as Box<dyn Runner>)).await;
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(my_global_lock)]
    async fn test_runner_commands() {
        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(command.clone()).unwrap();
        let commands = runner.commands();
        match commands.get("default") {
            Some(command) => command(&(Box::new(runner.clone()) as Box<dyn Runner>))
                .await
                .unwrap(),
            None => panic!("expected default command"),
        }
        match commands.get("other") {
            Some(command) => command(&(Box::new(runner.clone()) as Box<dyn Runner>))
                .await
                .unwrap(),
            None => panic!("expected other command"),
        }
    }

    #[test]
    #[serial(my_global_lock)]
    fn test_runner_resolve_command_bad_name() {
        let testid = "runner_resolve_command_bad_name";
        let expected = vec![
            "Runner::get_command(true)",
            "Command::get_name(true)",
            "Runner::commands(true)",
        ];
        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(command).unwrap();
        let guards = [
            guerrilla::patch1(DummyRunner::get_command, |_self| {
                Patch::runner_command(&SPY, "runner_resolve_command_bad_name", true, _self)
            }),
            guerrilla::patch1(DummyCommand::get_name, |_self| {
                Patch::command_get_name_bad(&SPY, "runner_resolve_command_bad_name", true, _self)
            }),
            guerrilla::patch1(DummyRunner::commands, |_self| {
                Patch::runner_commands(&SPY, "runner_resolve_command_bad_name", true, _self)
            }),
        ];
        defer! {
            let calls = SPY.get(testid);
            drop(guards);
            SPY.clear(testid);
            assert_eq!(*calls, expected);
        }
        let result = runner.resolve_command();
        assert!(result.is_err());
        match result {
            Ok(_) => {
                panic!("Expected an error, but got a success.");
            }
            Err(err) => {
                assert_eq!(format!("{:?}", err), "CommandError: No such command");
                let err_msg = err.to_string();
                assert!(
                    err_msg.contains("No such command"),
                    "Unexpected error: {}",
                    err_msg
                );
            }
        }
    }

    #[test]
    fn test_runner_get_command() {
        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(command.clone()).unwrap();
        assert_eq!(runner.get_command().get_name(), command.get_name());
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(my_global_lock)]
    async fn test_runner_handle() {
        let testid = "runner_handle";
        let expected = vec![
            "Runner::resolve_command(true)",
            "Runner::configured_command(true)",
        ];
        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(command).unwrap();
        let guards = vec![guerrilla::patch1(DummyRunner::resolve_command, |_self| {
            Patch::runner_resolve_command(&SPY, "runner_handle", true, _self)
        })];
        defer! {
            let calls = SPY.get(testid);
            drop(guards);
            SPY.clear(testid);
            assert_eq!(*calls, expected);
        }
        assert!(runner.handle().await.is_ok());
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(my_global_lock)]
    async fn test_runner_run() {
        let testid = "runner_run";
        let expected = vec!["Runner::start_log(true)", "Runner::handle(true)"];
        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(command).unwrap();
        let guards = vec![
            guerrilla::patch1(DummyRunner::start_log, |_self| {
                Patch::runner_start_log(&SPY, "runner_run", true, _self)
            }),
            guerrilla::patch1(DummyRunner::handle, |_self| {
                Box::pin(Patch::runner_handle(&SPY, "runner_run", true, _self))
            }),
        ];
        defer! {
            let calls = SPY.get(testid);
            drop(guards);
            SPY.clear(testid);
            assert_eq!(*calls, expected);
        }
        assert!(runner.run().await.is_ok());
    }

    #[test]
    #[serial(my_global_lock)]
    fn test_runner_startlog() {
        let testid = "runner_startlog";
        let expected = vec![
            "Runner::config(true): \"log.level\"",
            "env_logger::Builder::new(true)",
            "env_logger::Builder::filter(true): Warn",
            "env_logger::Builder::init(true)",
        ];
        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(command).unwrap();
        let guards = vec![
            guerrilla::patch2(DummyRunner::config, |_self, key| {
                Patch::runner_config(&SPY, "runner_startlog", true, _self, key)
            }),
            guerrilla::patch0(Builder::new, || {
                Patch::log_new(&SPY, "runner_startlog", true)
            }),
            guerrilla::patch3(Builder::filter, |_self, other, level| {
                Patch::log_filter(&SPY, "runner_startlog", true, _self, other, level)
            }),
            guerrilla::patch1(Builder::init, |_self| {
                Patch::log_init(&SPY, "runner_startlog", true, _self)
            }),
        ];
        defer! {
            let calls = SPY.get(testid);
            drop(guards);
            SPY.clear(testid);
            assert_eq!(*calls, expected);
        }
        assert!(runner.start_log().is_ok());
    }
}
