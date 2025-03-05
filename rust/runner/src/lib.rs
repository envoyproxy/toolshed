pub mod args;
pub mod command;
pub mod config;
pub mod log;
pub mod runner;

#[cfg(test)]
mod test_helpers;
// #[cfg(test)]
// mod test_macros;

use std::error::Error;

pub type EmptyResult = Result<(), Box<dyn Error + Send + Sync>>;

pub const DEFAULT_CONFIG_PATH: &str = "./config.yaml";
