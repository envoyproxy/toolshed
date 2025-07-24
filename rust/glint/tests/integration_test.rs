use std::process::Command;
use std::path::PathBuf;
use std::fs;
use serde_json::Value;

fn run_glint_test(fixture_name: &str, expect_success: bool) {
    let mut cmd = Command::new("cargo");
    cmd.arg("run");
    cmd.arg("--quiet");
    cmd.arg("--");
    
    // Get the path to the test fixture
    let fixture_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join(fixture_name);
    
    cmd.arg(&fixture_path);
    
    let output = cmd.output().expect("Failed to execute glint");
    
    // Check exit code
    if expect_success {
        assert!(output.status.success(), 
            "Expected glint to exit with zero status for {}, got {:?}", 
            fixture_name, output.status.code());
    } else {
        assert!(!output.status.success(), 
            "Expected glint to exit with non-zero status for {}", fixture_name);
        assert_eq!(output.status.code(), Some(1), 
            "Expected exit code 1 for {}", fixture_name);
    }
    
    // Parse the actual JSON output
    let stdout = String::from_utf8_lossy(&output.stdout);
    let actual_json: Value = serde_json::from_str(&stdout)
        .expect(&format!("Failed to parse JSON output for {}: {}", fixture_name, stdout));
    
    // Load expected JSON
    let expected_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join(format!("{}.expected.json", fixture_name));
    
    let expected_content = fs::read_to_string(&expected_path)
        .expect(&format!("Failed to read expected file: {:?}", expected_path));
    
    let mut expected_json: Value = serde_json::from_str(&expected_content)
        .expect(&format!("Failed to parse expected JSON for {}", fixture_name));
    
    // Normalize file paths in expected JSON to match actual output
    if let Some(files) = expected_json.get_mut("files").and_then(|f| f.as_object_mut()) {
        let mut normalized_files = serde_json::Map::new();
        for (key, value) in files.iter() {
            // Convert relative path in expected to absolute path
            let absolute_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join(key)
                .to_string_lossy()
                .to_string();
            normalized_files.insert(absolute_path, value.clone());
        }
        *files = normalized_files;
    }
    
    // Compare JSON
    assert_eq!(actual_json, expected_json, 
        "JSON output mismatch for {}.\nActual:\n{}\nExpected:\n{}", 
        fixture_name, 
        serde_json::to_string_pretty(&actual_json).unwrap(),
        serde_json::to_string_pretty(&expected_json).unwrap());
}

#[test]
fn test_bad_txt() {
    run_glint_test("bad.txt", false);
}

#[test]
fn test_bad2_txt() {
    run_glint_test("bad2.txt", false);
}

#[test]
fn test_bad3_txt() {
    run_glint_test("bad3.txt", false);
}

#[test]
fn test_good_txt() {
    run_glint_test("good.txt", true);
}

#[test]
fn test_bad4_txt() {
    run_glint_test("bad4.txt", false);
}

// To add more tests, just create:
// 1. A fixture file: tests/fixtures/badN.txt
// 2. An expected file: tests/fixtures/badN.txt.expected.json
// 3. A test function:
// #[test]
// fn test_badN_txt() {
//     run_glint_test("badN.txt", false);
// }
