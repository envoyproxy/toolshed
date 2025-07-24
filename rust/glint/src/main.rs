mod args;
mod check;
mod files;

use anyhow::Result;
use clap::Parser;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{
    Mutex,
    atomic::{AtomicBool, Ordering},
};

use crate::args::Args;
use crate::files::{FileIssues, find_files, process_file};

#[derive(Debug, Serialize, Deserialize)]
struct LintResult {
    files: HashMap<String, FileIssues>,
    summary: Summary,
}

#[derive(Debug, Serialize, Deserialize)]
struct Summary {
    total_files: usize,
    files_with_issues: usize,
    total_issues: usize,
}

fn main() -> Result<()> {
    let args = Args::parse();
    let mut all_files = Vec::new();
    for path in &args.paths {
        if !path.exists() {
            eprintln!("Warning: Path does not exist: {}", path.display());
            continue;
        }
        all_files.extend(find_files(path)?);
    }

    if all_files.is_empty() {
        eprintln!("No files to process");
        return Ok(());
    }

    let file_issues = Mutex::new(HashMap::new());
    let had_error = AtomicBool::new(false);
    all_files
        .par_iter()
        .for_each(|file| match process_file(file) {
            Ok(Some((path, issues))) => {
                let mut map = file_issues.lock().unwrap();
                map.insert(path, issues);
            }
            Ok(None) => {}
            Err(e) => {
                eprintln!("Error processing {}: {}", file.display(), e);
                had_error.store(true, Ordering::Relaxed);
            }
        });

    let files = file_issues.into_inner().unwrap();

    // Calculate summary
    let total_files = all_files.len();
    let files_with_issues = files.len();
    let total_issues: usize = files.values().map(|f| f.total_issues()).sum();

    let result = LintResult {
        files,
        summary: Summary {
            total_files,
            files_with_issues,
            total_issues,
        },
    };

    // Output JSON
    println!("{}", serde_json::to_string_pretty(&result)?);

    // Exit with non-zero status if there were issues
    if files_with_issues > 0 || had_error.load(Ordering::Relaxed) {
        std::process::exit(1);
    }

    Ok(())
}
