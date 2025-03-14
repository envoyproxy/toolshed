pub mod args;
pub mod command;
pub mod config;
pub mod handler;
pub mod log;
pub mod runner;

#[cfg(feature = "test")]
pub mod test;

use std::error::Error;

pub type EmptyResult = Result<(), Box<dyn Error + Send + Sync>>;

pub const DEFAULT_CONFIG_PATH: &str = "./config.yaml";
