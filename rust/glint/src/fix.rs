use anyhow::{Context, Result};
use std::fs;
use std::path::Path;

#[derive(Debug)]
pub struct FixResult {
    pub trailing_whitespace_fixed: usize,
    pub tabs_converted: usize,
    pub final_newline_added: bool,
}

pub fn fix_file(path: &Path) -> Result<Option<FixResult>> {
    let content = fs::read_to_string(path)
        .with_context(|| format!("Failed to read file: {}", path.display()))?;

    let mut fixed_lines = Vec::new();
    let mut trailing_whitespace_fixed = 0;
    let mut tabs_converted = 0;
    let mut changed = false;

    for line in content.lines() {
        let mut fixed_line = line.to_string();

        let tab_count = fixed_line.chars().filter(|&c| c == '\t').count();

        if tab_count > 0 {
            fixed_line = fixed_line.replace('\t', "    ");
            tabs_converted += tab_count;
            changed = true;
        }

        let trimmed = fixed_line.trim_end();
        if trimmed.len() < fixed_line.len() {
            fixed_line = trimmed.to_string();
            trailing_whitespace_fixed += 1;
            changed = true;
        }

        fixed_lines.push(fixed_line);
    }

    let needs_final_newline = !content.is_empty() && !content.ends_with('\n');
    let mut fixed_content = fixed_lines.join("\n");

    if !content.is_empty() && content.ends_with('\n') {
        fixed_content.push('\n');
    } else if needs_final_newline {
        fixed_content.push('\n');
        changed = true;
    }

    if changed {
        fs::write(path, fixed_content)
            .with_context(|| format!("Failed to write file: {}", path.display()))?;

        Ok(Some(FixResult {
            trailing_whitespace_fixed,
            tabs_converted,
            final_newline_added: needs_final_newline,
        }))
    } else {
        Ok(None)
    }
}
