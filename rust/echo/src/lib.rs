pub mod args;
pub mod command;
pub mod config;
pub mod handler;
pub mod listener;
pub mod mapping;
pub mod proc;
pub mod response;
pub mod runner;
pub mod tls;

const DEFAULT_HOSTNAME: &str = "echo";
const DEFAULT_HTTP_HOST: &str = "127.0.0.1";
const DEFAULT_HTTP_PORT: u16 = 8787;

#[cfg(feature = "test")]
pub mod test;
