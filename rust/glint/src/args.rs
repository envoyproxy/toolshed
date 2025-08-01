use clap::Parser;
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(name = "glint")]
#[command(about = "Lint files for whitespace issues", long_about = None)]
pub struct Args {
    #[arg(short, long)]
    pub fix: bool,

    #[arg(required = true)]
    pub paths: Vec<PathBuf>,
}
