use std::fs;
use std::process::Command;

use tempfile::TempDir;

fn lcov_merge() -> Command {
    Command::new(env!("CARGO_BIN_EXE_lcov-merge"))
}

#[test]
fn merges_listed_files_and_skips_missing() {
    let dir = TempDir::new().unwrap();
    let a = dir.path().join("a.dat");
    let b = dir.path().join("b.dat");
    fs::write(&a, "SF:src/x.cc\nDA:1,1\nDA:2,0\nend_of_record\n").unwrap();
    fs::write(
        &b,
        "SF:src/x.cc\nDA:2,5\nend_of_record\nSF:src/y.cc\nDA:1,0\nend_of_record\n",
    )
    .unwrap();
    let reports = dir.path().join("reports.txt");
    fs::write(
        &reports,
        format!(
            "{}\n{}\n{}\n",
            a.display(),
            b.display(),
            dir.path().join("gone.dat").display()
        ),
    )
    .unwrap();
    let output = dir.path().join("merged.dat");

    let status = lcov_merge()
        .arg("--output")
        .arg(&output)
        .arg("--reports-file")
        .arg(&reports)
        .status()
        .unwrap();
    assert!(status.success());
    assert_eq!(
        fs::read_to_string(&output).unwrap(),
        "SF:src/x.cc\nDA:1,1\nDA:2,5\nLF:2\nLH:2\nend_of_record\nSF:src/y.cc\nDA:1,0\nLF:1\nLH:0\nend_of_record\n"
    );
}

#[test]
fn positional_files_to_stdout() {
    let dir = TempDir::new().unwrap();
    let a = dir.path().join("a.dat");
    fs::write(&a, "SF:a\nDA:1,2\nend_of_record\n").unwrap();
    let output = lcov_merge()
        .arg("--output")
        .arg("-")
        .arg(&a)
        .arg(&a)
        .output()
        .unwrap();
    assert!(output.status.success());
    assert_eq!(
        String::from_utf8(output.stdout).unwrap(),
        "SF:a\nDA:1,4\nLF:1\nLH:1\nend_of_record\n"
    );
}

#[test]
fn fails_without_inputs_or_on_garbage() {
    let dir = TempDir::new().unwrap();
    assert!(
        !lcov_merge()
            .arg("--output")
            .arg("-")
            .status()
            .unwrap()
            .success()
    );
    let bad = dir.path().join("bad.dat");
    fs::write(&bad, "SF:a\nDA:nope\n").unwrap();
    assert!(
        !lcov_merge()
            .arg("--output")
            .arg("-")
            .arg(&bad)
            .status()
            .unwrap()
            .success()
    );
}
