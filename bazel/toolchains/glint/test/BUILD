load("//toolchains/glint:glint_toolchain.bzl", "get_glint_data")

def _glint_test_impl(ctx):
    """Test implementation that verifies glint toolchain is available."""
    glint_data = get_glint_data(ctx)

    # Create a test script that runs glint
    test_script = ctx.actions.declare_file(ctx.label.name)

    script_content = """#!/bin/bash
set -e

# Create a test file with whitespace issues
cat > test_file.txt << 'EOF'
This line has trailing whitespace
This line has a tab    here
This file has no final newline
EOF

# Check if glint is available and works
if command -v {glint} >/dev/null 2>&1; then
    echo "✓ Glint found at: {glint}"
    # Run glint on the test file (should find issues)
    if {glint} test_file.txt 2>&1 | grep -q "files_with_issues"; then
        echo "✓ Glint successfully detected whitespace issues"
        exit 0
    else
        echo "✗ Glint did not detect expected issues"
        exit 1
    fi
else
    echo "✗ Glint not found at expected path: {glint}"
    exit 1
fi
""".format(glint = glint_data.glint)

    ctx.actions.write(
        output = test_script,
        content = script_content,
        is_executable = True,
    )

    runfiles = ctx.runfiles()
    if hasattr(glint_data, "glint_file") and glint_data.glint_file:
        runfiles = runfiles.merge(ctx.runfiles(files = [glint_data.glint_file]))

    return [
        DefaultInfo(
            executable = test_script,
            runfiles = runfiles,
        ),
    ]

glint_test = rule(
    implementation = _glint_test_impl,
    test = True,
    toolchains = ["//toolchains/glint:glint_toolchain_type"],
)

# Actual test target
glint_test(
    name = "glint_toolchain_test",
    tags = ["manual"],  # Manual because glint might not be built yet
)
