pub mod args;
pub mod command;
pub mod config;
pub mod handler;
pub mod listener;
pub mod mapping;
pub mod response;
pub mod runner;

const DEFAULT_ADDRESS: &str = "127.0.0.1";
const DEFAULT_PORT: u16 = 8787;

#[cfg(feature = "test")]
pub mod test;
