//! Merging of lcov tracefiles.
//!
//! A tracefile is a sequence of records, one per line, grouped into sections
//! that start with `SF:<path>` and end with `end_of_record`. Merging sums the
//! execution counts of every section describing the same source file:
//!
//! * `DA:<line>,<count>[,<checksum>]` line hits are summed per line;
//! * `FN:<line>,<name>` function definitions are kept (first seen wins) and
//!   `FNDA:<count>,<name>` hits are summed per function;
//! * `BRDA:<line>,<block>,<branch>,<taken>` branch hits are summed per branch,
//!   where `-` (block never reached) counts as unreached unless some file did
//!   reach it;
//! * `LF`/`LH`, `FNF`/`FNH` and `BRF`/`BRH` totals are recomputed, and `TN`
//!   test names are dropped since the merged file describes every test.
//!
//! Files are parsed in parallel and the merged result is written sorted, so
//! the output is deterministic regardless of thread scheduling.

use std::collections::{BTreeMap, HashMap};
use std::fmt::Write as _;
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use rayon::prelude::*;

/// Coverage of one source file.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct FileCoverage {
    /// Line number -> execution count.
    pub lines: BTreeMap<u32, u64>,
    /// Function name -> (line, execution count).
    pub functions: BTreeMap<String, (u32, u64)>,
    /// (line, block, branch) -> taken count, `None` when never reached.
    pub branches: BTreeMap<(u32, u32, String), Option<u64>>,
}

impl FileCoverage {
    /// Adds `other`'s counts to this file's.
    pub fn merge(&mut self, other: FileCoverage) {
        for (line, count) in other.lines {
            *self.lines.entry(line).or_insert(0) += count;
        }
        for (name, (line, count)) in other.functions {
            let entry = self.functions.entry(name).or_insert((line, 0));
            entry.1 += count;
        }
        for (key, taken) in other.branches {
            let entry = self.branches.entry(key).or_insert(None);
            *entry = match (*entry, taken) {
                (None, None) => None,
                (a, b) => Some(a.unwrap_or(0) + b.unwrap_or(0)),
            };
        }
    }
}

/// Coverage of a set of source files, keyed by the `SF` path.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct Coverage {
    pub files: HashMap<String, FileCoverage>,
}

impl Coverage {
    /// Adds `other`'s files and counts to this coverage.
    pub fn merge(&mut self, other: Coverage) {
        for (path, coverage) in other.files {
            match self.files.get_mut(&path) {
                Some(existing) => existing.merge(coverage),
                None => {
                    self.files.insert(path, coverage);
                }
            }
        }
    }

    /// Parses one tracefile's contents.
    pub fn parse(content: &str) -> Result<Coverage> {
        let mut coverage = Coverage::default();
        let mut current: Option<(String, FileCoverage)> = None;
        for (index, raw) in content.lines().enumerate() {
            let line = raw.trim_end_matches('\r');
            if line.is_empty() {
                continue;
            }
            let (record, value) = match line.split_once(':') {
                Some(split) => split,
                None if line == "end_of_record" => {
                    if let Some((path, file)) = current.take() {
                        coverage.add_file(path, file);
                    }
                    continue;
                }
                None => bail!("line {}: unrecognised record {:?}", index + 1, line),
            };
            match record {
                "SF" => {
                    if let Some((path, file)) = current.take() {
                        coverage.add_file(path, file);
                    }
                    current = Some((value.to_string(), FileCoverage::default()));
                }
                "TN" | "LF" | "LH" | "FNF" | "FNH" | "BRF" | "BRH" => {}
                _ => {
                    let Some((_, file)) = current.as_mut() else {
                        bail!("line {}: {} record outside of a section", index + 1, record);
                    };
                    file.parse_record(record, value)
                        .with_context(|| format!("line {}: {:?}", index + 1, line))?;
                }
            }
        }
        if let Some((path, file)) = current.take() {
            coverage.add_file(path, file);
        }
        Ok(coverage)
    }

    fn add_file(&mut self, path: String, file: FileCoverage) {
        match self.files.get_mut(&path) {
            Some(existing) => existing.merge(file),
            None => {
                self.files.insert(path, file);
            }
        }
    }

    /// Writes the coverage as an lcov tracefile, files and lines in sorted order.
    pub fn write_to(&self, out: &mut impl Write) -> io::Result<()> {
        let mut paths: Vec<&String> = self.files.keys().collect();
        paths.sort();
        let mut buffer = String::new();
        for path in paths {
            let file = &self.files[path];
            buffer.clear();
            let _ = writeln!(buffer, "SF:{path}");
            for (name, (line, _)) in &file.functions {
                let _ = writeln!(buffer, "FN:{line},{name}");
            }
            for (name, (_, count)) in &file.functions {
                let _ = writeln!(buffer, "FNDA:{count},{name}");
            }
            if !file.functions.is_empty() {
                let hit = file
                    .functions
                    .values()
                    .filter(|(_, count)| *count > 0)
                    .count();
                let _ = writeln!(buffer, "FNF:{}", file.functions.len());
                let _ = writeln!(buffer, "FNH:{hit}");
            }
            for ((line, block, branch), taken) in &file.branches {
                match taken {
                    Some(count) => {
                        let _ = writeln!(buffer, "BRDA:{line},{block},{branch},{count}");
                    }
                    None => {
                        let _ = writeln!(buffer, "BRDA:{line},{block},{branch},-");
                    }
                }
            }
            if !file.branches.is_empty() {
                let hit = file
                    .branches
                    .values()
                    .filter(|taken| taken.unwrap_or(0) > 0)
                    .count();
                let _ = writeln!(buffer, "BRF:{}", file.branches.len());
                let _ = writeln!(buffer, "BRH:{hit}");
            }
            for (line, count) in &file.lines {
                let _ = writeln!(buffer, "DA:{line},{count}");
            }
            let hit = file.lines.values().filter(|count| **count > 0).count();
            let _ = writeln!(buffer, "LF:{}", file.lines.len());
            let _ = writeln!(buffer, "LH:{hit}");
            buffer.push_str("end_of_record\n");
            out.write_all(buffer.as_bytes())?;
        }
        Ok(())
    }
}

impl FileCoverage {
    fn parse_record(&mut self, record: &str, value: &str) -> Result<()> {
        match record {
            "DA" => {
                let mut fields = value.split(',');
                let line = parse_u32(fields.next(), "line")?;
                let count = parse_u64(fields.next(), "count")?;
                *self.lines.entry(line).or_insert(0) += count;
            }
            "FN" => {
                // `FN:<start>,<name>`, or `FN:<start>,<end>,<name>` since lcov 2.0. Names may
                // themselves contain commas (demangled C++), so only a purely numeric second
                // field is the end line.
                let (line, rest) = value.split_once(',').context("FN needs <line>,<name>")?;
                let line = parse_u32(Some(line), "line")?;
                let name = match rest.split_once(',') {
                    Some((end, name))
                        if !end.is_empty() && end.bytes().all(|b| b.is_ascii_digit()) =>
                    {
                        name
                    }
                    _ => rest,
                };
                self.functions.entry(name.to_string()).or_insert((line, 0));
            }
            "FNDA" => {
                let (count, name) = value.split_once(',').context("FNDA needs <count>,<name>")?;
                let count = parse_u64(Some(count), "count")?;
                let entry = self.functions.entry(name.to_string()).or_insert((0, 0));
                entry.1 += count;
            }
            "BRDA" => {
                let mut fields = value.splitn(4, ',');
                let line = parse_u32(fields.next(), "line")?;
                let block = parse_u32(fields.next(), "block")?;
                let branch = fields.next().context("BRDA needs <branch>")?.to_string();
                let taken = match fields.next().context("BRDA needs <taken>")? {
                    "-" => None,
                    count => Some(parse_u64(Some(count), "taken")?),
                };
                let entry = self.branches.entry((line, block, branch)).or_insert(None);
                *entry = match (*entry, taken) {
                    (None, None) => None,
                    (a, b) => Some(a.unwrap_or(0) + b.unwrap_or(0)),
                };
            }
            // Version-specific or tool-specific records (e.g. `VER`, `FNL`/`FNA` of newer
            // lcov) carry nothing the merged report reads.
            _ => {}
        }
        Ok(())
    }
}

fn parse_u32(field: Option<&str>, what: &str) -> Result<u32> {
    field
        .with_context(|| format!("missing {what}"))?
        .trim()
        .parse()
        .with_context(|| format!("invalid {what}"))
}

fn parse_u64(field: Option<&str>, what: &str) -> Result<u64> {
    field
        .with_context(|| format!("missing {what}"))?
        .trim()
        .parse()
        .with_context(|| format!("invalid {what}"))
}

/// Parses and merges the given tracefiles in parallel.
pub fn merge_files(paths: &[PathBuf]) -> Result<Coverage> {
    paths
        .par_iter()
        .map(|path| {
            let content = fs::read(path).with_context(|| format!("reading {}", path.display()))?;
            // Tracefiles are ASCII apart from source paths; a stray byte must not stop the merge.
            let content = String::from_utf8_lossy(&content);
            Coverage::parse(&content).with_context(|| format!("parsing {}", path.display()))
        })
        .try_reduce(Coverage::default, |mut a, b| {
            a.merge(b);
            Ok(a)
        })
}

/// Reads a list of tracefile paths, one per line, as written by Bazel for the
/// coverage report action.
pub fn read_reports_file(path: &Path) -> Result<Vec<PathBuf>> {
    let content =
        fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    Ok(content
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .map(PathBuf::from)
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    const A: &str = "TN:a\nSF:src/x.cc\nFN:3,foo\nFNDA:1,foo\nFNF:1\nFNH:1\nBRDA:4,0,0,1\nBRDA:4,0,1,-\nDA:3,1\nDA:4,0\nDA:5,2\nLF:3\nLH:2\nend_of_record\n";
    const B: &str = "SF:src/x.cc\nFN:3,foo\nFNDA:0,foo\nBRDA:4,0,0,-\nBRDA:4,0,1,3\nDA:3,0\nDA:4,4\nDA:6,1\nend_of_record\nSF:src/y.cc\nDA:1,1\nend_of_record\n";

    #[test]
    fn parses_sections() {
        let coverage = Coverage::parse(A).unwrap();
        let file = &coverage.files["src/x.cc"];
        assert_eq!(file.lines[&3], 1);
        assert_eq!(file.lines[&4], 0);
        assert_eq!(file.functions["foo"], (3, 1));
        assert_eq!(file.branches[&(4, 0, "1".to_string())], None);
    }

    #[test]
    fn merges_counts() {
        let mut coverage = Coverage::parse(A).unwrap();
        coverage.merge(Coverage::parse(B).unwrap());
        let file = &coverage.files["src/x.cc"];
        assert_eq!(file.lines[&3], 1);
        assert_eq!(file.lines[&4], 4);
        assert_eq!(file.lines[&5], 2);
        assert_eq!(file.lines[&6], 1);
        assert_eq!(file.functions["foo"], (3, 1));
        assert_eq!(file.branches[&(4, 0, "0".to_string())], Some(1));
        assert_eq!(file.branches[&(4, 0, "1".to_string())], Some(3));
        assert_eq!(coverage.files["src/y.cc"].lines[&1], 1);
    }

    #[test]
    fn writes_sorted_with_totals() {
        let mut coverage = Coverage::parse(B).unwrap();
        coverage.merge(Coverage::parse(A).unwrap());
        let mut out = Vec::new();
        coverage.write_to(&mut out).unwrap();
        let text = String::from_utf8(out).unwrap();
        assert_eq!(
            text,
            "SF:src/x.cc\nFN:3,foo\nFNDA:1,foo\nFNF:1\nFNH:1\nBRDA:4,0,0,1\nBRDA:4,0,1,3\nBRF:2\nBRH:2\nDA:3,1\nDA:4,4\nDA:5,2\nDA:6,1\nLF:4\nLH:4\nend_of_record\nSF:src/y.cc\nDA:1,1\nLF:1\nLH:1\nend_of_record\n"
        );
    }

    #[test]
    fn function_records_with_end_lines_and_commas_in_names() {
        let coverage = Coverage::parse(
            "SF:a\nFN:10,20,foo\nFNDA:1,foo\nFN:30,bar(int, int)\nFNDA:2,bar(int, int)\nFN:40,50,baz(int, int)\nFNDA:0,baz(int, int)\nend_of_record\n",
        )
        .unwrap();
        let file = &coverage.files["a"];
        assert_eq!(file.functions.len(), 3);
        assert_eq!(file.functions["foo"], (10, 1));
        assert_eq!(file.functions["bar(int, int)"], (30, 2));
        assert_eq!(file.functions["baz(int, int)"], (40, 0));
    }

    #[test]
    fn keeps_unreached_branches_and_zero_lines() {
        let coverage = Coverage::parse("SF:a\nBRDA:1,0,0,-\nDA:1,0\nend_of_record\n").unwrap();
        let mut out = Vec::new();
        coverage.write_to(&mut out).unwrap();
        assert_eq!(
            String::from_utf8(out).unwrap(),
            "SF:a\nBRDA:1,0,0,-\nBRF:1\nBRH:0\nDA:1,0\nLF:1\nLH:0\nend_of_record\n"
        );
    }

    #[test]
    fn same_file_twice_in_one_tracefile_is_merged() {
        let coverage =
            Coverage::parse("SF:a\nDA:1,1\nend_of_record\nSF:a\nDA:1,2\nend_of_record\n").unwrap();
        assert_eq!(coverage.files["a"].lines[&1], 3);
    }

    #[test]
    fn rejects_records_outside_sections_and_garbage() {
        assert!(Coverage::parse("DA:1,1\n").is_err());
        assert!(Coverage::parse("SF:a\nnonsense\n").is_err());
        assert!(Coverage::parse("SF:a\nDA:x,1\n").is_err());
    }

    #[test]
    fn empty_input_is_empty_coverage() {
        let coverage = Coverage::parse("").unwrap();
        assert!(coverage.files.is_empty());
        let mut out = Vec::new();
        coverage.write_to(&mut out).unwrap();
        assert!(out.is_empty());
    }
}
