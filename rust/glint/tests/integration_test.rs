use std::process::Command;
use std::path::PathBuf;
use std::fs;
use serde_json::Value;
use tempfile::TempDir;

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

fn run_glint_fix_test(fixture_name: &str) {
    // Create a temp directory and copy the test file
    let temp_dir = TempDir::new().expect("Failed to create temp directory");
    let temp_file = temp_dir.path().join(fixture_name);

    // Copy the fixture to temp location
    let fixture_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join(fixture_name);

    fs::copy(&fixture_path, &temp_file)
        .expect(&format!("Failed to copy fixture {} to temp location", fixture_name));

    // First run glint to check if the file has issues
    let mut check_cmd = Command::new("cargo");
    check_cmd.arg("run");
    check_cmd.arg("--quiet");
    check_cmd.arg("--");
    check_cmd.arg(&temp_file);

    let check_output = check_cmd.output().expect("Failed to execute glint check");
    let has_issues = !check_output.status.success();

    // Run glint --fix
    let mut cmd = Command::new("cargo");
    cmd.arg("run");
    cmd.arg("--quiet");
    cmd.arg("--");
    cmd.arg("--fix");
    cmd.arg(&temp_file);

    let output = cmd.output().expect("Failed to execute glint --fix");

    // Check that the command succeeded
    assert!(output.status.success(),
        "Expected glint --fix to exit with zero status for {}, got {:?}\nOutput: {}",
        fixture_name, output.status.code(), String::from_utf8_lossy(&output.stderr));

    // If the file had issues, we should get JSON output
    let stdout = String::from_utf8_lossy(&output.stdout);
    if has_issues {
        // Parse the JSON output
        let actual_json: Value = serde_json::from_str(&stdout)
            .expect(&format!("Expected JSON output for {} but got: {}", fixture_name, stdout));

        // Load expected fix JSON
        let expected_fix_json_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("tests")
            .join("fixtures")
            .join(format!("{}.expected_fix.json", fixture_name));

        if expected_fix_json_path.exists() {
            let expected_json_content = fs::read_to_string(&expected_fix_json_path)
                .expect(&format!("Failed to read expected fix JSON: {:?}", expected_fix_json_path));

            let mut expected_json: Value = serde_json::from_str(&expected_json_content)
                .expect(&format!("Failed to parse expected fix JSON for {}", fixture_name));

            // Normalize file paths in expected JSON to match actual output
            if let Some(files) = expected_json.get_mut("files").and_then(|f| f.as_object_mut()) {
                let mut normalized_files = serde_json::Map::new();
                for (_key, value) in files.iter() {
                    // The actual output will have the temp file path
                    let temp_file_str = temp_file.to_string_lossy().to_string();
                    normalized_files.insert(temp_file_str, value.clone());
                }
                *files = normalized_files;
            }

            // Compare JSON output
            assert_eq!(actual_json, expected_json,
                "Fix JSON output mismatch for {}.\nActual:\n{}\nExpected:\n{}",
                fixture_name,
                serde_json::to_string_pretty(&actual_json).unwrap(),
                serde_json::to_string_pretty(&expected_json).unwrap());
        }
    } else {
        // If no issues, there should be no output
        assert!(stdout.is_empty(),
            "Expected no output for clean file {}, but got: {}", fixture_name, stdout);
    }

    // Read the fixed content
    let fixed_content = fs::read_to_string(&temp_file)
        .expect(&format!("Failed to read fixed file for {}", fixture_name));

    // Read the expected fixed content
    let expected_fixed_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join(format!("{}.expected_fixed", fixture_name));

    let expected_fixed_content = fs::read_to_string(&expected_fixed_path)
        .expect(&format!("Failed to read expected fixed file: {:?}", expected_fixed_path));

    // Compare the fixed content with expected
    assert_eq!(fixed_content, expected_fixed_content,
        "Fixed content mismatch for {}.\nActual:\n{}\nExpected:\n{}",
        fixture_name, fixed_content, expected_fixed_content);
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

// Fix tests
#[test]
fn test_fix_bad_txt() {
    run_glint_fix_test("bad.txt");
}

#[test]
fn test_fix_bad2_txt() {
    run_glint_fix_test("bad2.txt");
}

#[test]
fn test_fix_bad3_txt() {
    run_glint_fix_test("bad3.txt");
}

#[test]
fn test_fix_bad4_txt() {
    run_glint_fix_test("bad4.txt");
}

#[test]
fn test_fix_good_txt() {
    run_glint_fix_test("good.txt");
}

// To add more tests, just create:
// 1. A fixture file: tests/fixtures/badN.txt
// 2. An expected file: tests/fixtures/badN.txt.expected.json
// 3. An expected fixed file: tests/fixtures/badN.txt.expected_fixed
// 4. An expected fix JSON file: tests/fixtures/badN.txt.expected_fix.json
// 5. Test functions:
// #[test]
// fn test_badN_txt() {
//     run_glint_test("badN.txt", false);
// }
// #[test]
// fn test_fix_badN_txt() {
//     run_glint_fix_test("badN.txt");
// }
