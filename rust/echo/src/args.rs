use clap::Parser;
use toolshed_runner as runner;

#[derive(Clone, Debug, Parser, PartialEq)]
#[command(version = "1.0", about = "HTTP echo")]
pub struct Args {
    #[command(flatten)]
    pub base: runner::args::BaseArgs,
    #[arg(long)]
    pub host: Option<String>,
    #[arg(long)]
    pub hostname: Option<String>,
    #[arg(short, long)]
    pub port: Option<u16>,
}

impl runner::args::Provider for Args {
    fn config(&self) -> String {
        self.base.config.clone()
    }

    fn log_level(&self) -> Option<String> {
        self.base.log_level.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use toolshed_runner::{args::Provider as _, DEFAULT_CONFIG_PATH};

    #[test]
    fn test_args_constructor() {
        let clargs = vec!["test_program"];
        let args = Args::parse_from(clargs.clone());
        assert!(args.base.config == *DEFAULT_CONFIG_PATH.to_string());
        assert!(args.config() == *DEFAULT_CONFIG_PATH.to_string());
        assert!(args.base.log_level.is_none());
        assert!(args.log_level().is_none());
        assert!(args.host.is_none());
        assert!(args.hostname.is_none());
        assert!(args.port.is_none());
    }
}
