use crate::{command::Command, handler::Handler, log};
use ::log::LevelFilter;
use as_any::AsAny;
use async_trait::async_trait;
use env_logger::Builder;
use std::{any::Any, collections::HashMap, error::Error, fmt, future::Future, pin::Pin, sync::Arc};
use toolshed_core as core;

pub trait Factory<T, R>: Send + Sync
where
    T: Runner<R> + Sized,
    R: Handler + Sized + 'static,
{
    fn new(handler: R) -> Self;
}

pub fn ctrl_c() -> std::pin::Pin<Box<dyn std::future::Future<Output = ()> + Send + 'static>> {
    Box::pin(async move {
        let _ = tokio::signal::ctrl_c().await;
    })
}

#[macro_export]
macro_rules! runner {
    ($handler_type:ty, { $( $cmd_name:literal => $cmd_fn:expr ),* $(,)? }) => {
        // Requires:
        //
        // use as_any::Downcast;
        //
        // in the calling module

        fn as_arc(&self) -> std::sync::Arc<dyn toolshed_runner::runner::Runner<$handler_type>> {
            std::sync::Arc::new(self.clone())
        }

        fn commands(&self) -> toolshed_runner::runner::CommandsFn<$handler_type> {
            let mut commands: toolshed_runner::runner::CommandsFn<$handler_type> = std::collections::HashMap::new();
            $(
                commands.insert($cmd_name, std::sync::Arc::new(|s: &std::sync::Arc<dyn toolshed_runner::runner::Runner<$handler_type>>| {
                    let s = s.as_any().downcast_ref::<Self>().expect("Downcast failed").clone();
                    Box::pin(async move { $cmd_fn(&s).await })
                }));
            )*
            commands
        }
    }
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

pub type CommandFn<T> = Arc<
    dyn Fn(&Arc<dyn Runner<T>>) -> Pin<Box<dyn Future<Output = core::EmptyResult> + Send>>
        + Send
        + Sync,
>;

pub type CommandsFn<'a, T> = HashMap<&'a str, CommandFn<T>>;

#[async_trait]
pub trait Runner<T: Handler + 'static>: Any + AsAny + Send + Sync {
    fn as_arc(&self) -> Arc<dyn Runner<T>>;
    fn commands(&self) -> CommandsFn<T>;
    fn get_handler(&self) -> &T;

    fn get_command(&self) -> Box<&dyn Command> {
        self.get_handler().get_command()
    }

    fn config(&self, key: &str) -> Option<core::Primitive> {
        self.get_command().get_config().get(key)
    }

    async fn handle(&self) -> core::EmptyResult {
        let command = self.resolve_command()?;
        command(&self.as_arc()).await
    }

    fn resolve_command(&self) -> Result<CommandFn<T>, CommandError> {
        match self.commands().get(self.get_command().get_name()) {
            Some(command) => Ok(command.clone()),
            None => Err(CommandError {
                message: "No such command".to_string(),
            }),
        }
    }

    async fn run(&self) -> core::EmptyResult {
        self.start_log().unwrap();
        self.handle().await
    }

    fn start_log(&self) -> core::EmptyResult {
        if let Some(core::Primitive::String(level_str)) = self.config("log.level") {
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
    use crate::{
        config::Provider as _,
        test::{
            dummy::{Dummy, DummyCommand, DummyConfig, DummyHandler, DummyRunner},
            patch::Patch,
        },
    };
    use guerrilla::{patch0, patch1, patch2, patch3};
    use once_cell::sync::Lazy;
    use scopeguard::defer;
    use serial_test::serial;
    use toolshed_test as ttest;

    static PATCHES: Lazy<ttest::Patches> = Lazy::new(ttest::Patches::new);
    static SPY: Lazy<ttest::Spy> = Lazy::new(ttest::Spy::new);
    static TESTS: Lazy<ttest::Tests> = Lazy::new(|| ttest::Tests::new(&SPY, &PATCHES));

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_ctrl_c() {
        let (tx, rx) = tokio::sync::oneshot::channel();
        let ctrl_c_handle = tokio::spawn(async move {
            ctrl_c().await;
            let _ = tx.send(true);
        });
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;

        unsafe {
            libc::raise(libc::SIGINT);
        }

        match tokio::time::timeout(std::time::Duration::from_secs(1), rx).await {
            Ok(channel_result) => match channel_result {
                Ok(value) => {
                    assert!(value, "Signal wasn't properly caught");
                }
                Err(_) => panic!("Channel was closed without sending a value"),
            },
            Err(_) => panic!("Timed out waiting for ctrl_c to complete"),
        }
        let _ = ctrl_c_handle.await;
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_runner_commands() {
        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let handler = Dummy::handler(command).unwrap();
        let runner = Dummy::runner(handler).unwrap();
        let commands = runner.commands();
        match commands.get("default") {
            Some(command) => command(&(Arc::new(runner.clone()) as Arc<dyn Runner<DummyHandler>>))
                .await
                .unwrap(),
            None => panic!("expected default command"),
        }
        match commands.get("other") {
            Some(command) => command(&(Arc::new(runner.clone()) as Arc<dyn Runner<DummyHandler>>))
                .await
                .unwrap(),
            None => panic!("expected other command"),
        }
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_config() {
        let test = TESTS
            .test("runner_config")
            .expecting(vec![
                "Runner::get_command(true)",
                "Command::get_config(true)",
                "Config::get(true): \"SOME.KEY.PATH\"",
            ])
            .with_patches(vec![
                patch1(DummyRunner::get_command, |_self| {
                    Box::new(Patch::runner_command(TESTS.get("runner_config"), _self))
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
        let runner = Dummy::runner(handler).unwrap();
        let mut failure = "";

        if let Some(core::Primitive::String(result)) = runner.config("SOME.KEY.PATH") {
            assert_eq!(result, "BOOM");
        } else {
            failure = "Expected a Primitive::String, but got something else.";
        }
        assert_eq!(failure, "");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_get_command() {
        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let handler = Dummy::handler(command.clone()).unwrap();
        let runner = Dummy::runner(handler).unwrap();
        assert_eq!(runner.get_command().get_name(), command.get_name());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_get_handler() {
        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let handler = Dummy::handler(command.clone()).unwrap();
        let runner = Dummy::runner(handler.clone()).unwrap();
        assert_eq!(runner.get_handler(), &handler);
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
            .with_patches(vec![patch1(DummyRunner::resolve_command, |_self| {
                Patch::runner_resolve_command::<DummyHandler>(TESTS.get("runner_handle"), _self)
            })]);
        defer! {
            test.drop()
        }

        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let handler = Dummy::handler(command).unwrap();
        let runner = Dummy::runner(handler).unwrap();
        assert!(runner.handle().await.is_ok());
    }

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_runner_resolve_command() {
        let test = TESTS
            .test("runner_resolve_command")
            .expecting(vec![
                "Runner::commands(true)",
                "Runner::get_command(true)",
                "Command::get_name(true)",
                "Runner::configured_command(true)",
            ])
            .with_patches(vec![
                patch1(DummyRunner::get_command, |_self| {
                    Box::new(Patch::runner_command(
                        TESTS.get("runner_resolve_command"),
                        _self,
                    ))
                }),
                patch1(DummyCommand::get_name, |_self| {
                    Patch::command_get_name(TESTS.get("runner_resolve_command"), _self)
                }),
                patch1(DummyRunner::commands, |_self| {
                    Patch::runner_commands(TESTS.get("runner_resolve_command"), _self)
                }),
            ]);
        defer! {
            test.drop()
        }

        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let handler = Dummy::handler(command).unwrap();
        let runner = Dummy::runner(handler).unwrap();
        let command = runner.resolve_command().unwrap();
        let _ = command(&(Arc::new(runner.clone()) as Arc<dyn Runner<DummyHandler>>)).await;
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_resolve_command_bad_name() {
        let test = TESTS
            .test("runner_resolve_command_bad_name")
            .expecting(vec![
                "Runner::commands(true)",
                "Runner::get_command(true)",
                "Command::get_name(true)",
            ])
            .with_patches(vec![
                patch1(DummyRunner::get_command, |_self| {
                    Box::new(Patch::runner_command(
                        TESTS.get("runner_resolve_command_bad_name"),
                        _self,
                    ))
                }),
                patch1(DummyCommand::get_name, |_self| {
                    Patch::command_get_name_bad(TESTS.get("runner_resolve_command_bad_name"), _self)
                }),
                patch1(DummyRunner::commands, |_self| {
                    Patch::runner_commands(TESTS.get("runner_resolve_command_bad_name"), _self)
                }),
            ]);
        defer! {
            test.drop()
        }

        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let handler = Dummy::handler(command).unwrap();
        let runner = Dummy::runner(handler).unwrap();
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

    #[tokio::test(flavor = "multi_thread")]
    #[serial(toolshed_lock)]
    async fn test_runner_run() {
        let test = TESTS
            .test("runner_run")
            .expecting(vec!["Runner::start_log(true)", "Runner::handle(true)"])
            .with_patches(vec![
                patch1(DummyRunner::start_log, |_self| {
                    Patch::runner_start_log::<DummyHandler>(TESTS.get("runner_run"), _self)
                }),
                patch1(DummyRunner::handle, |_self| {
                    Box::pin(Patch::runner_handle::<DummyHandler>(
                        TESTS.get("runner_run"),
                        _self,
                    ))
                }),
            ]);
        defer! {
            test.drop()
        }

        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let handler = Dummy::handler(command).unwrap();
        let runner = Dummy::runner(handler).unwrap();
        assert!(runner.run().await.is_ok());
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_runner_startlog() {
        let test = TESTS
            .test("runner_startlog")
            .expecting(vec![
                "Runner::config(true): \"log.level\"",
                "env_logger::Builder::new(true)",
                "env_logger::Builder::filter(true): Warn",
                "env_logger::Builder::init(true)",
            ])
            .with_patches(vec![
                patch2(DummyRunner::config, |_self, key| {
                    Patch::runner_config::<DummyHandler>(
                        TESTS.get("runner_startlog"),
                        Some(core::Primitive::String("warning".to_string())),
                        _self,
                        key,
                    )
                }),
                patch0(Builder::new, || {
                    Patch::log_new(TESTS.get("runner_startlog"))
                }),
                patch3(Builder::filter, |_self, other, level| {
                    Patch::log_filter(TESTS.get("runner_startlog"), _self, other, level)
                }),
                patch1(Builder::init, |_self| {
                    Patch::log_init(TESTS.get("runner_startlog"), _self)
                }),
            ]);
        defer! {
            test.drop()
        }

        let config = Dummy::config().unwrap();
        let command = Dummy::command(config, "stars".to_string()).unwrap();
        let handler = Dummy::handler(command).unwrap();
        let runner = Dummy::runner(handler).unwrap();
        assert!(runner.start_log().is_ok());
    }
}
