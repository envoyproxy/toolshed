mod args;
mod config;
mod handler;
mod listener;
mod command;
mod response;
mod runner;

const DEFAULT_ADDRESS: &str = "127.0.0.1";
const DEFAULT_PORT: u16 = 8787;

#[tokio::main]
#[allow(dead_code)]
async fn main() {
    runner::main().await;
}
