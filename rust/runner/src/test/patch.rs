use crate::{
    command, config, log, runner,
    test::{
        data::TEST_YAML0,
        dummy::{DummyCommand, DummyConfig, DummyRunner, Loggable},
        spy::Spy,
        Test,
    },
    EmptyResult,
};
use ::log::LevelFilter;
use env_logger::Builder;
use guerrilla::PatchGuard;
use serde_yaml::Value;
use std::{
    collections::HashMap,
    future::Future,
    path::Path,
    pin::Pin,
    sync::{Arc, Mutex},
};
use tempfile::NamedTempFile;

pub struct Patches {
    pub calls: Mutex<HashMap<String, Vec<Arc<Mutex<PatchGuard>>>>>,
}

impl Patches {
    // Constructor to create a new Patches instance
    pub fn new() -> Self {
        Self {
            calls: Mutex::new(HashMap::new()),
        }
    }

    pub fn push(&self, key: &str, guards: Vec<Arc<Mutex<PatchGuard>>>) {
        let mut calls = self.calls.lock().unwrap();
        calls.insert(key.to_string(), guards);
    }

    // Retrieve a Vec<PatchGuard> for a specific key
    pub fn get(&self, key: &str) -> Option<Vec<Arc<Mutex<PatchGuard>>>> {
        let calls = self.calls.lock().unwrap();
        calls.get(key).cloned()
    }

    pub fn clear(&self, key: &str) {
        let mut calls = self.calls.lock().unwrap();
        calls.remove(key).unwrap();
    }
}

pub struct Patch {}

impl Patch {
    pub fn command_config<'a>(
        test: Arc<Mutex<Test<'a>>>,
        _self: &'a DummyCommand,
    ) -> Box<&'a dyn config::Provider> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("Command::get_config({:?})", !test.fails),
        );
        Box::new(&_self.config)
    }

    pub fn command_get_name<'a>(test: Arc<Mutex<Test>>, _self: &'a DummyCommand) -> &'a str {
        let test = test.lock().unwrap();
        test.spy()
            .push(&test.name, &format!("Command::get_name({:?})", !test.fails));
        "COMMAND_NAME"
    }

    pub fn command_get_name_bad<'a>(test: Arc<Mutex<Test>>, _self: &'a DummyCommand) -> &'a str {
        let test = test.lock().unwrap();
        test.spy()
            .push(&test.name, &format!("Command::get_name({:?})", !test.fails));
        "DOES_NOT_EXIST"
    }

    pub fn config_get(
        test: Arc<Mutex<Test>>,
        _self: &DummyConfig,
        key: &str,
    ) -> Option<config::Primitive> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("Config::get({:?}): {:?}", !test.fails, key),
        );
        Some(config::Primitive::String("BOOM".to_string()))
    }

    pub fn config_resolve<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test>>,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "Provider::resolve({:?}): {:?} {:?}",
                !test.fails, keys, current
            ),
        );
        serde_yaml::from_str("RESOLVED").expect("To unwrap")
    }

    pub fn config_resolve_bad<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test>>,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "Provider::resolve({:?}): {:?} {:?}",
                !test.fails, keys, current
            ),
        );
        Some(Value::from(vec!["FOO"]))
    }

    pub fn config_resolve_bad_type<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test>>,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "Provider::resolve({:?}): {:?} {:?}",
                !test.fails, keys, current
            ),
        );
        Some(Value::Number(serde_yaml::Number::from(f64::NAN)))
    }

    pub fn config_resolve_f64<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test>>,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "Provider::resolve({:?}): {:?} {:?}",
                !test.fails, keys, current
            ),
        );
        Some(Value::Number(serde_yaml::Number::from(23.23)))
    }

    pub fn config_resolve_i32<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test>>,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "Provider::resolve({:?}): {:?} {:?}",
                !test.fails, keys, current
            ),
        );
        Some(Value::Number(serde_yaml::Number::from(-23)))
    }

    pub fn config_resolve_i64<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test>>,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "Provider::resolve({:?}): {:?} {:?}",
                !test.fails, keys, current
            ),
        );
        Some(Value::Number(serde_yaml::Number::from(-2323232323_i64)))
    }

    pub fn config_resolve_bool<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test>>,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "Provider::resolve({:?}): {:?} {:?}",
                !test.fails, keys, current
            ),
        );
        Some(Value::Bool(true))
    }

    pub fn config_resolve_u32<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test>>,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "Provider::resolve({:?}): {:?} {:?}",
                !test.fails, keys, current
            ),
        );
        Some(Value::Number(serde_yaml::Number::from(23)))
    }

    pub fn config_resolve_u64<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test>>,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "Provider::resolve({:?}): {:?} {:?}",
                !test.fails, keys, current
            ),
        );
        Some(Value::Number(serde_yaml::Number::from(232323232323_u64)))
    }

    pub fn config_serialized<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test>>,
        _self: &T,
    ) -> Option<Value> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("Provider::serialized({:?})", !test.fails),
        );
        serde_yaml::from_str("SERIALIZED").expect("To unwrap")
    }

    pub fn env_var(test: Arc<Mutex<Test>>, name: &str) -> Result<String, std::env::VarError> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("std::env::var({:?}): {:?}", !test.fails, name),
        );
        if test.fails {
            return Err(std::env::VarError::NotUnicode("Not unicode".into()));
        }
        Ok("info".to_string())
    }

    pub fn file_open(test: Arc<Mutex<Test>>, path: &Path) -> Result<std::fs::File, std::io::Error> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("File::open({:?}): {:?}", !test.fails, path),
        );
        if test.fails {
            return Err(std::io::Error::new(
                std::io::ErrorKind::IsADirectory,
                "Some error message",
            ));
        }
        let temp_file = NamedTempFile::new()?;
        let file = temp_file.reopen()?;
        Ok(file)
    }

    pub fn log_filter<'a>(
        test: Arc<Mutex<Test>>,
        _self: &'a mut Builder,
        _other: Option<&str>,
        level: LevelFilter,
    ) -> &'a mut Builder {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "env_logger::Builder::filter({:?}): {:?}",
                !test.fails, level
            ),
        );
        _self
    }

    pub fn log_init(test: Arc<Mutex<Test>>, _self: &Builder) {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("env_logger::Builder::init({:?})", !test.fails),
        );
    }

    pub fn log_new(test: Arc<Mutex<Test>>) -> Builder {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("env_logger::Builder::new({:?})", !test.fails),
        );
        Builder::default()
    }

    pub fn log_level_override(
        test: Arc<Mutex<Test>>,
        result: bool,
        args: config::ArcSafeArgs,
    ) -> Result<Option<log::Level>, config::SafeError> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "Factory::log_level_override({:?}/{:?}): {:?}",
                !test.fails, result, args
            ),
        );
        if test.fails {
            return Err("Failed getting log level override".into());
        }
        if result {
            return Ok(Some(log::Level::Trace));
        }
        Ok(None)
    }

    pub async fn override_config<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test<'_>>>,
        args: config::ArcSafeArgs,
        config: Box<T>,
    ) -> Result<Box<T>, config::SafeError> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "Config::override_config({:?}): {:?}, {:?}",
                !test.fails, args, config
            ),
        );
        Ok(config)
    }

    pub fn override_config_log<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test<'_>>>,
        args: config::ArcSafeArgs,
        config: &mut Box<T>,
    ) -> EmptyResult {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "Config::override_config_log({:?}): {:?}, {:?}",
                !test.fails, args, config
            ),
        );
        Ok(())
    }

    pub fn path_exists(test: Arc<Mutex<Test<'_>>>, _self: &Path) -> bool {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("Path.exists({:?}): {:?}", !test.fails, _self),
        );
        !test.fails
    }

    pub async fn read_yaml<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test<'_>>>,
        args: config::ArcSafeArgs,
    ) -> Result<Box<T>, config::SafeError> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("Config::read_yaml({:?}): {:?}", !test.fails, args),
        );
        let config: T = serde_yaml::from_str(TEST_YAML0).expect("Unable to parse yaml");
        Ok(Box::new(config))
    }

    pub fn runner_command<'a>(
        test: Arc<Mutex<Test<'a>>>,
        _self: &'a DummyRunner,
    ) -> &'a dyn command::Command {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("Runner::get_command({:?})", !test.fails),
        );
        &_self.command
    }

    pub fn runner_commands<'a>(
        test: Arc<Mutex<Test<'a>>>,
        _self: &'a DummyRunner,
    ) -> runner::CommandsFn<'a> {
        let testid: String;
        let fails: bool;
        let spy_arc: Arc<Spy>;
        {
            let test = test.lock().unwrap();
            testid = test.name.clone();
            fails = test.fails;
            spy_arc = Arc::new((**test.spy()).clone());
            test.spy()
                .push(&testid, &format!("Runner::commands({:?})", !test.fails));
        }

        let command: runner::CommandFn = Arc::new(move |_runner| {
            let testid: String = testid.clone();
            let spy = spy_arc.clone();
            Box::pin(async move {
                spy.push(
                    &testid,
                    &format!("Runner::configured_command({:?})", !fails),
                );
                Ok(())
            })
        });

        let mut commands: runner::CommandsFn = HashMap::new();
        commands.insert("COMMAND_NAME", command.clone());
        commands
    }

    pub fn runner_config(
        test: Arc<Mutex<Test>>,
        returns: Option<config::Primitive>,
        _self: &dyn runner::Runner,
        key: &str,
    ) -> Option<config::Primitive> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("Runner::config({:?}): {:?}", !test.fails, key),
        );
        returns
    }

    pub async fn runner_handle<'a>(
        test: Arc<Mutex<Test<'a>>>,
        _self: &'a dyn runner::Runner,
    ) -> EmptyResult {
        let test = test.lock().unwrap();
        test.spy()
            .push(&test.name, &format!("Runner::handle({:?})", !test.fails));
        Ok(())
    }

    pub fn runner_resolve_command(
        test: Arc<Mutex<Test>>,
        _self: &dyn runner::Runner,
    ) -> Result<runner::CommandFn, runner::CommandError> {
        let testid: String;
        let fails: bool;
        let spy_arc: Arc<Spy>;
        {
            let test = test.lock().unwrap();
            testid = test.name.clone();
            fails = test.fails;
            spy_arc = Arc::new((**test.spy()).clone());
            test.spy().push(
                &test.name,
                &format!("Runner::resolve_command({:?})", !test.fails),
            );
        }

        Ok(Arc::new(
            move |_runner| -> Pin<Box<dyn Future<Output = EmptyResult> + Send>> {
                let testid: String = testid.clone();
                let spy = spy_arc.clone();
                Box::pin(async move {
                    let spy = spy;
                    let testid: &str = testid.as_str();
                    spy.push(testid, &format!("Runner::configured_command({:?})", !fails));
                    Ok(())
                })
            },
        ))
    }

    pub fn runner_start_log<'a>(
        test: Arc<Mutex<Test<'a>>>,
        _self: &'a dyn runner::Runner,
    ) -> EmptyResult {
        let test = test.lock().unwrap();
        test.spy()
            .push(&test.name, &format!("Runner::start_log({:?})", !test.fails));
        Ok(())
    }

    pub fn serde_from_reader<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test>>,
        file: &std::fs::File,
    ) -> Result<T, serde_yaml::Error> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!(
                "serde_yaml::from_reader({:?}): {:?}",
                !test.fails,
                file.metadata().expect("Error parsing metadata").is_file()
            ),
        );
        if test.fails {
            let err: serde_yaml::Error = serde_yaml::from_str::<i32>("invalid").unwrap_err();
            return Err(err);
        }
        let config: T = serde_yaml::from_str(TEST_YAML0).expect("Unable to parse yaml");
        Ok(config)
    }

    pub fn serde_from_str<T: config::Provider + Loggable + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test>>,
        string: &str,
    ) -> Result<log::Level, serde_yaml::Error> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("serde_yaml::from_str({:?}): {:?}", !test.fails, string),
        );
        if test.fails {
            let err: serde_yaml::Error = serde_yaml::from_str::<i32>("invalid").unwrap_err();
            return Err(err);
        }
        let config: T = serde_yaml::from_str(TEST_YAML0).expect("Unable to parse yaml");
        Ok(config.log().level)
    }

    pub fn serde_to_value(
        test: Arc<Mutex<Test>>,
        thing: Box<dyn config::Provider>,
    ) -> Result<Value, serde_yaml::Error> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("serde_yaml::to_value({:?}): {:?}", !test.fails, thing),
        );
        serde_yaml::from_str("SERIALIZED")
    }

    pub fn set_log<T: config::Provider + serde::Deserialize<'static>>(
        test: Arc<Mutex<Test>>,
        _self: &mut T,
        level: log::Level,
    ) -> Result<(), Box<dyn std::error::Error + Sync + Send>> {
        let test = test.lock().unwrap();
        test.spy().push(
            &test.name,
            &format!("Config::set_log({:?}): {:?}", !test.fails, level),
        );
        if test.fails {
            return Err("Error setting log".into());
        }
        Ok(())
    }
}
