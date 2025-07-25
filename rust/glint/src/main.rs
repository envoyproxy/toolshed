mod args;
mod check;
mod files;
mod fix;

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
use crate::files::{FileIssues, find_files, process_file, should_exclude};
use crate::fix::fix_file;

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

#[derive(Debug, Serialize, Deserialize)]
struct FixResult {
    files: HashMap<String, FixedFileInfo>,
    summary: FixSummary,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct FixedFileInfo {
    trailing_whitespace_fixed: usize,
    tabs_converted: usize,
    final_newline_added: bool,
}

#[derive(Debug, Serialize, Deserialize)]
struct FixSummary {
    total_files: usize,
    files_fixed: usize,
    total_fixes: usize,
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

    if args.fix {
        let mut fixed_files = HashMap::new();
        let mut error_count = 0;
        let mut total_files_checked = 0;

        for file in &all_files {
            if should_exclude(file) {
                continue;
            }

            total_files_checked += 1;

            match fix_file(file) {
                Ok(Some(result)) => {
                    fixed_files.insert(
                        file.display().to_string(),
                        FixedFileInfo {
                            trailing_whitespace_fixed: result.trailing_whitespace_fixed,
                            tabs_converted: result.tabs_converted,
                            final_newline_added: result.final_newline_added,
                        },
                    );
                }
                Ok(None) => {
                    // No fixes needed for this file
                }
                Err(e) => {
                    eprintln!("Error fixing {}: {}", file.display(), e);
                    error_count += 1;
                }
            }
        }

        if error_count > 0 {
            std::process::exit(1);
        }

        if !fixed_files.is_empty() {
            let files_fixed = fixed_files.len();
            let total_fixes: usize = fixed_files
                .values()
                .map(|f| {
                    f.trailing_whitespace_fixed
                        + f.tabs_converted
                        + if f.final_newline_added { 1 } else { 0 }
                })
                .sum();

            let result = FixResult {
                files: fixed_files,
                summary: FixSummary {
                    total_files: total_files_checked,
                    files_fixed,
                    total_fixes,
                },
            };

            println!("{}", serde_json::to_string_pretty(&result)?);
        }

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

    println!("{}", serde_json::to_string_pretty(&result)?);
    if files_with_issues > 0 || had_error.load(Ordering::Relaxed) {
        std::process::exit(1);
    }
    Ok(())
}
