#![feature(coverage_attribute)]

mod args;
mod command;
mod config;
mod handler;
mod listener;
mod mapping;
mod response;
mod runner;

#[cfg(feature = "test")]
pub mod test;

use std::process;

const DEFAULT_ADDRESS: &str = "127.0.0.1";
const DEFAULT_PORT: u16 = 8787;

#[tokio::main]
#[coverage(off)]
async fn main() -> ! {
    runner::main().await;
    process::exit(0);
}
