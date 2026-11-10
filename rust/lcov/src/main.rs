//! `lcov-merge`: merge lcov tracefiles into one.
//!
//! ```text
//! lcov-merge --output merged.info a.info b.info ...
//! lcov-merge --output merged.info --reports-file reports.txt
//! ```
//!
//! `--reports-file` names a file listing tracefile paths one per line, as Bazel
//! writes for its coverage report action. Paths that do not exist are skipped
//! (a test that produced no coverage data contributes nothing), everything
//! else is parsed in parallel and summed.

use std::fs::File;
use std::io::{self, BufWriter, Write};
use std::path::PathBuf;

use anyhow::{Context, Result, bail};
use clap::Parser;

#[derive(Parser, Debug)]
#[command(name = "lcov-merge", about = "Merge lcov tracefiles into one")]
struct Args {
    /// Where to write the merged tracefile ("-" for stdout).
    #[arg(short, long)]
    output: PathBuf,

    /// A file listing tracefiles to merge, one path per line.
    #[arg(long)]
    reports_file: Option<PathBuf>,

    /// Number of threads to parse with (default: the number of CPUs).
    #[arg(long)]
    threads: Option<usize>,

    /// Tracefiles to merge.
    files: Vec<PathBuf>,
}

fn main() -> Result<()> {
    let args = Args::parse();
    if let Some(threads) = args.threads {
        rayon::ThreadPoolBuilder::new()
            .num_threads(threads)
            .build_global()
            .context("configuring threads")?;
    }

    let mut files = args.files;
    if let Some(reports_file) = &args.reports_file {
        files.extend(toolshed_lcov::read_reports_file(reports_file)?);
    }
    if files.is_empty() && args.reports_file.is_none() {
        bail!("no tracefiles given; pass paths or --reports-file");
    }
    let (present, missing): (Vec<PathBuf>, Vec<PathBuf>) =
        files.into_iter().partition(|path| path.is_file());
    for path in &missing {
        eprintln!("lcov-merge: skipping missing tracefile {}", path.display());
    }

    let coverage = toolshed_lcov::merge_files(&present)?;

    if args.output.as_os_str() == "-" {
        let stdout = io::stdout();
        let mut out = BufWriter::new(stdout.lock());
        coverage.write_to(&mut out)?;
        out.flush()?;
    } else {
        let file = File::create(&args.output)
            .with_context(|| format!("creating {}", args.output.display()))?;
        let mut out = BufWriter::new(file);
        coverage.write_to(&mut out)?;
        out.flush()?;
    }
    eprintln!(
        "lcov-merge: merged {} tracefiles covering {} source files",
        present.len(),
        coverage.files.len()
    );
    Ok(())
}
