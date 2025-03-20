use log::{LevelFilter, Log, Metadata, Record};
use std::sync::{Arc, Mutex, OnceLock};

static LOGGER: OnceLock<&'static TestLogger> = OnceLock::new();

#[derive(Clone, Debug, PartialEq)]
pub struct LogEntry {
    pub level: log::Level,
    pub message: String,
}

#[derive(Debug)]
pub struct TestLogger {
    logs: Arc<Mutex<Vec<LogEntry>>>,
}

impl TestLogger {
    pub fn new() -> Self {
        TestLogger {
            logs: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub fn install(&self) -> Result<(), log::SetLoggerError> {
        // Clear logs
        self.logs.lock().unwrap().clear();

        log::set_max_level(LevelFilter::Info);
        log::set_boxed_logger(Box::new(TestLoggerImpl {
            logs: self.logs.clone(),
        }))
    }

    pub fn logs(&self) -> Vec<LogEntry> {
        self.logs.lock().unwrap().clone()
    }
}

struct TestLoggerImpl {
    logs: Arc<Mutex<Vec<LogEntry>>>,
}

impl Log for TestLoggerImpl {
    fn enabled(&self, metadata: &Metadata) -> bool {
        metadata.level() <= log::Level::Info
    }

    fn log(&self, record: &Record) {
        if self.enabled(record.metadata()) {
            let mut logs = self.logs.lock().unwrap();
            logs.push(LogEntry {
                level: record.level(),
                message: format!("{}", record.args()),
            });
        }
    }

    fn flush(&self) {}
}

pub fn setup_logger() -> &'static TestLogger {
    LOGGER
        .get_or_init(|| Box::leak(Box::new(TestLogger::new())))
        .tap(|logger| {
            let _ = logger.install();
        })
}

trait Tap {
    fn tap<F: FnOnce(&Self)>(self, f: F) -> Self;
}

impl<T> Tap for T {
    fn tap<F: FnOnce(&Self)>(self, f: F) -> Self {
        f(&self);
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use log::{error, info, warn};
    use serial_test::serial;

    #[test]
    #[serial(toolshed_lock)]
    fn test_logger_basic_functionality() {
        let logger = setup_logger();

        info!("Test info message");
        warn!("Test warning message");
        error!("Test error message");

        let logs = logger.logs();
        assert_eq!(logs.len(), 3, "Expected exactly 3 log entries");
        assert_eq!(logs[0].level, log::Level::Info);
        assert_eq!(logs[1].level, log::Level::Warn);
        assert_eq!(logs[2].level, log::Level::Error);
        assert_eq!(logs[0].message, "Test info message");
    }

    #[test]
    #[serial(toolshed_lock)]
    fn test_multiple_log_messages() {
        let logger = setup_logger();

        for i in 0..5 {
            info!("Log message {}", i);
        }

        let logs = logger.logs();
        assert_eq!(logs.len(), 5, "Expected exactly 5 log entries");
        for (i, log) in logs.iter().enumerate() {
            assert_eq!(log.message, format!("Log message {}", i));
        }
    }
}
