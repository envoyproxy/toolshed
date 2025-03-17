#![feature(coverage_attribute)]

mod args;
mod command;
mod config;
mod handler;
mod listener;
mod mapping;
mod proc;
mod response;
mod runner;
mod tls;

#[cfg(feature = "test")]
pub mod test;

use std::process;

const DEFAULT_HOSTNAME: &str = "echo";
const DEFAULT_HTTP_HOST: &str = "127.0.0.1";
const DEFAULT_HTTP_PORT: u16 = 8787;

#[allow(dead_code)]
#[tokio::main]
#[coverage(off)]
async fn main() -> ! {
    runner::main().await;
    process::exit(0);
}
