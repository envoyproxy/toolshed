use ::log::LevelFilter;
use serde::{Deserialize, Serialize};
use std::{fmt, str::FromStr};

#[derive(Debug, Eq, Deserialize, Clone, Copy, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Level {
    Error,
    Warning,
    Info,
    Debug,
    Trace,
}

#[derive(Debug)]
pub struct LevelParseError;

impl std::error::Error for LevelParseError {}

impl FromStr for Level {
    type Err = LevelParseError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "error" => Ok(Level::Error),
            "warning" => Ok(Level::Warning),
            "info" => Ok(Level::Info),
            "debug" => Ok(Level::Debug),
            "trace" => Ok(Level::Trace),
            _ => Err(LevelParseError),
        }
    }
}

impl From<Level> for LevelFilter {
    fn from(level: Level) -> Self {
        match level {
            Level::Error => LevelFilter::Error,
            Level::Warning => LevelFilter::Warn,
            Level::Info => LevelFilter::Info,
            Level::Debug => LevelFilter::Debug,
            Level::Trace => LevelFilter::Trace,
        }
    }
}

impl fmt::Display for Level {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let level_str = match self {
            Level::Error => "error",
            Level::Warning => "warning",
            Level::Info => "info",
            Level::Debug => "debug",
            Level::Trace => "trace",
        };
        write!(f, "{}", level_str)
    }
}

impl fmt::Display for LevelParseError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "Invalid log level")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test::data::LOG_LEVELS;
    use assert_matches::assert_matches;

    #[test]
    fn test_log_level_to_string() {
        for (key, (log_level, _)) in LOG_LEVELS.iter() {
            assert_eq!(*key, log_level.to_string());
        }
    }

    #[test]
    fn test_log_level_from_string() {
        for (key, (log_level, _)) in LOG_LEVELS.iter() {
            assert_eq!(Level::from_str(key).unwrap(), *log_level);
        }
    }

    #[test]
    fn test_log_level_from_string_bad() {
        assert_matches!(Level::from_str("NOT_A_LOG_LEVEL"), Err(LevelParseError));
    }

    #[test]
    fn test_log_level_parser_error() {
        assert_eq!(LevelParseError.to_string(), "Invalid log level");
    }

    #[test]
    fn test_log_levelfilter_from_level() {
        for (_, (log_level, level_filter)) in LOG_LEVELS.iter() {
            assert_eq!(LevelFilter::from(*log_level), *level_filter);
        }
    }
}
