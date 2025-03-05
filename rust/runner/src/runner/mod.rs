use crate::request::Request;
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
    R: Request + Sized,
{
    fn new(request: R) -> Self;
}

#[macro_export]
macro_rules! runner {
    ($request:ident, { $( $cmd_name:literal => $cmd_fn:expr ),* $(,)? }) => {
        // Requires:
        //
        // use as_any::Downcast;
        //
        // in the calling module

        fn get_request(&self) -> &dyn toolshed_runner::request::Request {
            &self.$request
        }

        fn get_commands(&self) -> toolshed_runner::runner::CommandsFn {
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
    fn get_commands(&self) -> CommandsFn;
    fn get_request(&self) -> &dyn Request;
    async fn handle(&self) -> EmptyResult;

    fn config(&self, key: &str) -> Option<config::Primitive> {
        self.get_request().get_config().get(key)
    }

    fn get_command(&self) -> Result<CommandFn, CommandError> {
        let name = self.get_request().get_name();
        let commands = self.get_commands();
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
    use crate::test_helpers::{Dummy, DummyConfig, DummyRequest, DummyRunner, Patched, Spy};
    use config::Provider;
    use scopeguard::defer;
    use serial_test::serial;

    static SPY: once_cell::sync::Lazy<Spy> = once_cell::sync::Lazy::new(Spy::new);

    #[test]
    #[serial(my_global_lock)]
    fn test_runner_config() {
        let testid = "runner_config";
        let expected = vec![
            "Runner::get_request(true)",
            "Request::get_config(true)",
            "Config::get(true): \"SOME.KEY.PATH\"",
        ];
        let config = Dummy::config().unwrap();
        let request = Dummy::request(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(request).unwrap();
        let guards = [
            guerrilla::patch1(DummyRunner::get_request, |_self| {
                Patched::runner_request(&SPY, "runner_config", true, _self)
            }),
            guerrilla::patch1(DummyRequest::get_config, |_self| {
                Patched::request_config(&SPY, "runner_config", true, _self)
            }),
            guerrilla::patch2(DummyConfig::get, |_self, key| {
                Patched::config_get(&SPY, "runner_config", true, _self, key)
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
    async fn test_runner_get_command() {
        let testid = "runner_get_command";
        let expected = vec![
            "Runner::get_request(true)",
            "Request::get_name(true)",
            "Runner::get_commands(true)",
            "Runner::configured_command(true)",
        ];
        let config = Dummy::config().unwrap();
        let request = Dummy::request(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(request).unwrap();
        let guards = [
            guerrilla::patch1(DummyRunner::get_request, |_self| {
                Patched::runner_request(&SPY, "runner_get_command", true, _self)
            }),
            guerrilla::patch1(DummyRequest::get_name, |_self| {
                Patched::request_get_name(&SPY, "runner_get_command", true, _self)
            }),
            guerrilla::patch1(DummyRunner::get_commands, |_self| {
                Patched::runner_get_commands(&SPY, "runner_get_command", true, _self)
            }),
        ];
        defer! {
            let calls = SPY.get(testid);
            drop(guards);
            SPY.clear(testid);
            assert_eq!(*calls, expected);
        }
        let command = runner.get_command().unwrap();
        let _ = command(&(Box::new(runner.clone()) as Box<dyn Runner>)).await;
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(my_global_lock)]
    async fn test_runner_get_commands() {
        let config = Dummy::config().unwrap();
        let request = Dummy::request(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(request.clone()).unwrap();
        let commands = runner.get_commands();
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
    fn test_runner_get_command_bad_name() {
        let testid = "runner_get_command_bad_name";
        let expected = vec![
            "Runner::get_request(true)",
            "Request::get_name(true)",
            "Runner::get_commands(true)",
        ];
        let config = Dummy::config().unwrap();
        let request = Dummy::request(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(request).unwrap();
        let guards = [
            guerrilla::patch1(DummyRunner::get_request, |_self| {
                Patched::runner_request(&SPY, "runner_get_command_bad_name", true, _self)
            }),
            guerrilla::patch1(DummyRequest::get_name, |_self| {
                Patched::request_get_name_bad(&SPY, "runner_get_command_bad_name", true, _self)
            }),
            guerrilla::patch1(DummyRunner::get_commands, |_self| {
                Patched::runner_get_commands(&SPY, "runner_get_command_bad_name", true, _self)
            }),
        ];
        defer! {
            let calls = SPY.get(testid);
            drop(guards);
            SPY.clear(testid);
            assert_eq!(*calls, expected);
        }
        let result = runner.get_command();
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
    fn test_runner_get_request() {
        let config = Dummy::config().unwrap();
        let request = Dummy::request(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(request.clone()).unwrap();
        assert_eq!(runner.get_request().get_name(), request.get_name());
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(my_global_lock)]
    async fn test_runner_handle() {
        let testid = "runner_handle";
        let expected = vec![
            "Runner::get_command(true)",
            "Runner::configured_command(true)",
        ];
        let config = Dummy::config().unwrap();
        let request = Dummy::request(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(request).unwrap();
        let guards = vec![guerrilla::patch1(DummyRunner::get_command, |_self| {
            Patched::runner_get_command(&SPY, "runner_handle", true, _self)
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
        let request = Dummy::request(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(request).unwrap();
        let guards = vec![
            guerrilla::patch1(DummyRunner::start_log, |_self| {
                Patched::runner_start_log(&SPY, "runner_run", true, _self)
            }),
            guerrilla::patch1(DummyRunner::handle, |_self| {
                Box::pin(Patched::runner_handle(&SPY, "runner_run", true, _self))
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
        let request = Dummy::request(config, "stars".to_string()).unwrap();
        let runner = Dummy::runner(request).unwrap();
        let guards = vec![
            guerrilla::patch2(DummyRunner::config, |_self, key| {
                Patched::runner_config(&SPY, "runner_startlog", true, _self, key)
            }),
            guerrilla::patch0(Builder::new, || {
                Patched::log_new(&SPY, "runner_startlog", true)
            }),
            guerrilla::patch3(Builder::filter, |_self, other, level| {
                Patched::log_filter(&SPY, "runner_startlog", true, _self, other, level)
            }),
            guerrilla::patch1(Builder::init, |_self| {
                Patched::log_init(&SPY, "runner_startlog", true, _self)
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
