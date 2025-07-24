use anyhow::{Context, Result};
use std::fs::File;
use std::io::{BufRead, BufReader, Read, Seek, SeekFrom};
use std::path::Path;

pub fn final_newline(path: &Path) -> Result<bool> {
    let mut file = File::open(path).context("Failed to open file")?;
    let size = file.metadata()?.len();
    if size == 0 {
        return Ok(true); // Empty files are considered OK
    }
    file.seek(SeekFrom::End(-1))?;
    let mut last_byte = [0u8; 1];
    file.read_exact(&mut last_byte)?;
    Ok(last_byte[0] != b'\n')
}

pub fn trailing_whitespace(path: &Path) -> Result<Vec<usize>> {
    let file = File::open(path).context("Failed to open file")?;
    let reader = BufReader::new(file);
    let mut lines_with_trailing = Vec::new();
    for (line_num, line) in reader.lines().enumerate() {
        let line = line?;
        if line.ends_with(' ') || line.ends_with('\t') {
            lines_with_trailing.push(line_num + 1); // 1-based line numbers
        }
    }
    Ok(lines_with_trailing)
}

pub fn mixed_indentation(path: &Path) -> Result<bool> {
    let file = File::open(path).context("Failed to open file")?;
    let reader = BufReader::new(file);
    let mut has_tab_indent = false;
    let mut has_space_indent = false;
    for line in reader.lines() {
        let line = line?;
        if line.starts_with('\t') {
            has_tab_indent = true;
        } else if line.starts_with(' ') {
            has_space_indent = true;
        }
        if has_tab_indent && has_space_indent {
            return Ok(true);
        }
    }
    Ok(false)
}
