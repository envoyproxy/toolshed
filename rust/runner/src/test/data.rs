use crate::log;
use ::log::LevelFilter;
use std::collections::HashMap;

pub const TEST_YAML0: &str = "
log:
  level: trace
";

pub const TEST_YAML1: &str = "
dict0:
  subdict0:
    key0: value0
  list0:
  - item0
  - dictitem0:
      key1: value1
";

pub static LOG_LEVELS: once_cell::sync::Lazy<HashMap<&'static str, (log::Level, LevelFilter)>> =
    once_cell::sync::Lazy::new(|| {
        let mut map = HashMap::new();
        map.insert("debug", (log::Level::Debug, LevelFilter::Debug));
        map.insert("error", (log::Level::Error, LevelFilter::Error));
        map.insert("info", (log::Level::Info, LevelFilter::Info));
        map.insert("trace", (log::Level::Trace, LevelFilter::Trace));
        map.insert("warning", (log::Level::Warning, LevelFilter::Warn));
        map
    });
