use crate::{
    EmptyResult, command, config, log, runner,
    test::{
        Tests,
        data::TEST_YAML0,
        dummy::{DummyCommand, DummyConfig, DummyRunner, Loggable},
    },
};
use ::log::LevelFilter;
use env_logger::Builder;
use guerrilla::PatchGuard;
use once_cell::sync::Lazy;
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
    pub fn config_get(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &DummyConfig,
        key: &str,
    ) -> Option<config::Primitive> {
        tests
            .spy
            .push(testid, &format!("Config::get({:?}): {:?}", success, key));
        Some(config::Primitive::String("BOOM".to_string()))
    }

    pub fn config_resolve<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        tests.spy.push(
            testid,
            &format!("Provider::resolve({:?}): {:?} {:?}", success, keys, current),
        );
        serde_yaml::from_str("RESOLVED").expect("To unwrap")
    }

    pub fn config_resolve_bad<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        tests.spy.push(
            testid,
            &format!("Provider::resolve({:?}): {:?} {:?}", success, keys, current),
        );
        Some(Value::from(vec!["FOO"]))
    }

    pub fn config_resolve_bad_type<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        tests.spy.push(
            testid,
            &format!("Provider::resolve({:?}): {:?} {:?}", success, keys, current),
        );
        Some(Value::Number(serde_yaml::Number::from(f64::NAN)))
    }

    pub fn config_resolve_f64<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        tests.spy.push(
            testid,
            &format!("Provider::resolve({:?}): {:?} {:?}", success, keys, current),
        );
        Some(Value::Number(serde_yaml::Number::from(23.23)))
    }

    pub fn config_resolve_i32<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        tests.spy.push(
            testid,
            &format!("Provider::resolve({:?}): {:?} {:?}", success, keys, current),
        );
        Some(Value::Number(serde_yaml::Number::from(-23)))
    }

    pub fn config_resolve_i64<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        tests.spy.push(
            testid,
            &format!("Provider::resolve({:?}): {:?} {:?}", success, keys, current),
        );
        Some(Value::Number(serde_yaml::Number::from(-2323232323_i64)))
    }

    pub fn config_resolve_bool<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        tests.spy.push(
            testid,
            &format!("Provider::resolve({:?}): {:?} {:?}", success, keys, current),
        );
        Some(Value::Bool(true))
    }

    pub fn config_serialized<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &T,
    ) -> Option<Value> {
        tests
            .spy
            .push(testid, &format!("Provider::serialized({:?})", success));
        serde_yaml::from_str("SERIALIZED").expect("To unwrap")
    }

    pub fn config_resolve_u32<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        tests.spy.push(
            testid,
            &format!("Provider::resolve({:?}): {:?} {:?}", success, keys, current),
        );
        Some(Value::Number(serde_yaml::Number::from(23)))
    }

    pub fn config_resolve_u64<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &T,
        current: &Value,
        keys: &[&str],
    ) -> Option<Value> {
        tests.spy.push(
            testid,
            &format!("Provider::resolve({:?}): {:?} {:?}", success, keys, current),
        );
        Some(Value::Number(serde_yaml::Number::from(232323232323_u64)))
    }

    pub fn env_var(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        name: &str,
    ) -> Result<String, std::env::VarError> {
        tests
            .spy
            .push(testid, &format!("std::env::var({:?}): {:?}", success, name));
        if !success {
            return Err(std::env::VarError::NotUnicode("Not unicode".into()));
        }
        Ok("info".to_string())
    }

    pub fn log_filter<'a>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &'a mut Builder,
        _other: Option<&str>,
        level: LevelFilter,
    ) -> &'a mut Builder {
        tests.spy.push(
            testid,
            &format!("env_logger::Builder::filter({:?}): {:?}", success, level),
        );
        _self
    }

    pub fn log_init(tests: &Lazy<Tests>, testid: &str, success: bool, _self: &Builder) {
        tests
            .spy
            .push(testid, &format!("env_logger::Builder::init({:?})", success));
    }

    pub fn log_new(tests: &Lazy<Tests>, testid: &str, success: bool) -> Builder {
        tests
            .spy
            .push(testid, &format!("env_logger::Builder::new({:?})", success));
        Builder::default()
    }

    pub fn file_open(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        path: &Path,
    ) -> Result<std::fs::File, std::io::Error> {
        tests
            .spy
            .push(testid, &format!("File::open({:?}): {:?}", success, path));
        if !success {
            return Err(std::io::Error::new(
                std::io::ErrorKind::IsADirectory,
                "Some error message",
            ));
        }
        let temp_file = NamedTempFile::new()?;
        let file = temp_file.reopen()?;
        Ok(file)
    }

    pub fn log_level_override(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        result: bool,
        args: config::ArcSafeArgs,
    ) -> Result<Option<log::Level>, config::SafeError> {
        tests.spy.push(
            testid,
            &format!(
                "Factory::log_level_override({:?}/{:?}): {:?}",
                success, result, args
            ),
        );
        if !success {
            return Err("Failed getting log level override".into());
        }
        if result {
            return Ok(Some(log::Level::Trace));
        }
        Ok(None)
    }

    pub async fn override_config<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests<'_>>,
        testid: &str,
        args: config::ArcSafeArgs,
        config: Box<T>,
    ) -> Result<Box<T>, config::SafeError> {
        tests.spy.push(
            testid,
            &format!("Config::override_config: {:?}, {:?}", args, config),
        );
        Ok(config)
    }

    pub fn override_config_log<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        args: config::ArcSafeArgs,
        config: &mut Box<T>,
    ) -> EmptyResult {
        tests.spy.push(
            testid,
            &format!(
                "Config::override_config_log({:?}): {:?}, {:?}",
                success, args, config
            ),
        );
        Ok(())
    }

    pub fn path_exists(tests: &Lazy<Tests>, testid: &str, result: bool, _self: &Path) -> bool {
        tests
            .spy
            .push(testid, &format!("Path.exists({:?}): {:?}", result, _self));
        result
    }

    pub async fn read_yaml<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests<'_>>,
        testid: &str,
        args: config::ArcSafeArgs,
    ) -> Result<Box<T>, config::SafeError> {
        tests
            .spy
            .push(testid, &format!("Config::read_yaml: {:?}", args));
        let config: T = serde_yaml::from_str(TEST_YAML0).expect("Unable to parse yaml");
        Ok(Box::new(config))
    }

    pub fn command_config<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        _self: &'a DummyCommand,
    ) -> Box<&'a dyn config::Provider> {
        tests
            .spy
            .push(testid, &format!("Command::get_config({:?})", success));
        Box::new(&_self.config)
    }

    pub fn command_get_name<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        _self: &'a DummyCommand,
    ) -> &'a str {
        tests
            .spy
            .push(testid, &format!("Command::get_name({:?})", success));
        "COMMAND_NAME"
    }

    pub fn command_get_name_bad<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        _self: &'a DummyCommand,
    ) -> &'a str {
        tests
            .spy
            .push(testid, &format!("Command::get_name({:?})", success));
        "DOES_NOT_EXIST"
    }

    pub fn runner_config(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        returns: Option<config::Primitive>,
        _self: &dyn runner::Runner,
        key: &str,
    ) -> Option<config::Primitive> {
        tests
            .spy
            .push(testid, &format!("Runner::config({:?}): {:?}", success, key));
        returns
    }

    pub fn runner_resolve_command(
        tests: &'static Lazy<Tests>,
        testid: &'static str,
        success: bool,
        _self: &dyn runner::Runner,
    ) -> Result<runner::CommandFn, runner::CommandError> {
        let spy = tests.spy;
        spy.push(testid, &format!("Runner::resolve_command({:?})", success));
        Ok(Arc::new(
            move |_runner: &Box<dyn runner::Runner>| -> Pin<Box<dyn Future<Output = EmptyResult> + Send>> {
                let spy = spy;
                let testid: &'static str = testid;
                Box::pin(async move {
                    spy.push(testid, &format!("Runner::configured_command({:?})", success));
                    Ok(())
                })
            },
        ))
    }

    pub fn runner_command<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        _self: &'a DummyRunner,
    ) -> &'a dyn command::Command {
        tests
            .spy
            .push(testid, &format!("Runner::get_command({:?})", success));
        &_self.command
    }

    pub fn runner_commands<'a>(
        tests: &'static Lazy<Tests>,
        testid: &'static str,
        success: bool,
        _self: &DummyRunner,
    ) -> runner::CommandsFn<'a> {
        let spy = tests.spy;
        spy.push(testid, &format!("Runner::commands({:?})", success));

        let command: runner::CommandFn = Arc::new(move |_runner: &Box<dyn runner::Runner>| {
            let testid: &'static str = testid;
            Box::pin(async move {
                spy.push(
                    testid,
                    &format!("Runner::configured_command({:?})", success),
                );
                Ok(())
            })
        });

        let mut commands: runner::CommandsFn = HashMap::new();
        commands.insert("COMMAND_NAME", command.clone());
        commands
    }

    pub async fn runner_handle<'a>(
        tests: &Lazy<Tests<'a>>,
        testid: &str,
        success: bool,
        _self: &'a dyn runner::Runner,
    ) -> EmptyResult {
        tests
            .spy
            .push(testid, &format!("Runner::handle({:?})", success));
        Ok(())
    }

    pub fn runner_start_log<'a>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &'a dyn runner::Runner,
    ) -> EmptyResult {
        tests
            .spy
            .push(testid, &format!("Runner::start_log({:?})", success));
        Ok(())
    }

    pub fn serde_from_reader<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        file: &std::fs::File,
    ) -> Result<T, serde_yaml::Error> {
        tests.spy.push(
            testid,
            &format!(
                "serde_yaml::from_reader({:?}): {:?}",
                success,
                file.metadata().expect("Error parsing metadata").is_file()
            ),
        );
        if !success {
            let err: serde_yaml::Error = serde_yaml::from_str::<i32>("invalid").unwrap_err();
            return Err(err);
        }
        let config: T = serde_yaml::from_str(TEST_YAML0).expect("Unable to parse yaml");
        Ok(config)
    }

    pub fn serde_from_str<T: config::Provider + Loggable + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        string: &str,
    ) -> Result<log::Level, serde_yaml::Error> {
        tests.spy.push(
            testid,
            &format!("serde_yaml::from_str({:?}): {:?}", success, string),
        );
        if !success {
            let err: serde_yaml::Error = serde_yaml::from_str::<i32>("invalid").unwrap_err();
            return Err(err);
        }
        let config: T = serde_yaml::from_str(TEST_YAML0).expect("Unable to parse yaml");
        Ok(config.log().level)
    }

    pub fn serde_to_value(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        thing: Box<dyn config::Provider>,
    ) -> Result<Value, serde_yaml::Error> {
        tests.spy.push(
            testid,
            &format!("serde_yaml::to_value({:?}): {:?}", success, thing),
        );
        serde_yaml::from_str("SERIALIZED")
    }

    pub fn set_log<T: config::Provider + serde::Deserialize<'static>>(
        tests: &Lazy<Tests>,
        testid: &str,
        success: bool,
        _self: &mut T,
        level: log::Level,
    ) -> Result<(), Box<dyn std::error::Error + Sync + Send>> {
        tests.spy.push(
            testid,
            &format!("Config::set_log({:?}): {:?}", success, level),
        );
        if !success {
            return Err("Error setting log".into());
        }
        Ok(())
    }
}
