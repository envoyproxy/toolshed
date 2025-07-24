use crate::check;
#[allow(unused_imports)]
use anyhow::{Context, Result};
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileIssues {
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub trailing_whitespace: Vec<usize>,
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    pub mixed_indentation: bool,
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    pub no_final_newline: bool,
}

impl FileIssues {
    pub fn new() -> Self {
        FileIssues {
            trailing_whitespace: Vec::new(),
            mixed_indentation: false,
            no_final_newline: false,
        }
    }

    pub fn has_issues(&self) -> bool {
        !self.trailing_whitespace.is_empty() || self.mixed_indentation || self.no_final_newline
    }

    pub fn total_issues(&self) -> usize {
        self.trailing_whitespace.len()
            + if self.mixed_indentation { 1 } else { 0 }
            + if self.no_final_newline { 1 } else { 0 }
    }
}

pub fn should_exclude(path: &Path) -> bool {
    let path_str = path.to_string_lossy();
    let exclude_patterns = [
        r"[\w\W/-]*\.go$",
        r"[\w\W/-]*\.patch$",
        r"^test/[\w/]*_corpus/[\w/]*",
        r"^tools/[\w/]*_corpus/[\w/]*",
        r"[\w/]*password_protected_password.txt$",
    ];
    for pattern in &exclude_patterns {
        if let Ok(re) = Regex::new(pattern) {
            if re.is_match(&path_str) {
                return true;
            }
        }
    }
    false
}

pub fn process_file(path: &Path) -> Result<Option<(String, FileIssues)>> {
    if should_exclude(path) {
        return Ok(None);
    }
    let mut issues = FileIssues::new();

    match check::trailing_whitespace(path) {
        Ok(lines) => issues.trailing_whitespace = lines,
        Err(e) => {
            return Err(e.context(format!(
                "Failed to check trailing whitespace for {}",
                path.display()
            )));
        }
    }

    match check::mixed_indentation(path) {
        Ok(mixed) => issues.mixed_indentation = mixed,
        Err(e) => {
            return Err(e.context(format!(
                "Failed to check mixed indentation for {}",
                path.display()
            )));
        }
    }

    match check::final_newline(path) {
        Ok(missing) => issues.no_final_newline = missing,
        Err(e) => {
            return Err(e.context(format!(
                "Failed to check final newline for {}",
                path.display()
            )));
        }
    }

    if issues.has_issues() {
        Ok(Some((path.display().to_string(), issues)))
    } else {
        Ok(None)
    }
}

/// Recursively find all files in a directory
pub fn find_files(path: &Path) -> Result<Vec<PathBuf>> {
    let mut files = Vec::new();
    if path.is_file() {
        files.push(path.to_path_buf());
    } else if path.is_dir() {
        for entry in std::fs::read_dir(path)? {
            let entry = entry?;
            let path = entry.path();
            if path.is_file() {
                files.push(path);
            } else if path.is_dir() {
                files.extend(find_files(&path)?);
            }
        }
    }
    Ok(files)
}
