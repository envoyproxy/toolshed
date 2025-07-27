# Example of using glint toolchain in a genrule

load("//toolchains/glint:current_toolchain.bzl", "current_glint_toolchain")

# Example: Use glint to check for whitespace issues
genrule(
    name = "check_whitespace",
    srcs = glob(["*.txt"]),
    outs = ["whitespace_report.json"],
    cmd = """
        # Use glint to check for whitespace issues
        $(location //toolchains/glint:current_glint_toolchain) \
            $(SRCS) > $@ || \
            echo "Whitespace issues found (see report)"
    """,
    tools = ["//toolchains/glint:current_glint_toolchain"],
)

# Example: Use glint to fix whitespace issues
genrule(
    name = "fix_whitespace",
    srcs = glob(["*.txt"]),
    outs = [f.replace(".txt", "_fixed.txt") for f in glob(["*.txt"])],
    cmd = """
        # Copy files and fix whitespace issues
        for src in $(SRCS); do
            base=$(basename $src .txt)
            cp $src $base\_fixed.txt
        done
        $(location //toolchains/glint:current_glint_toolchain) \
            --fix *_fixed.txt || true
    """,
    tools = ["//toolchains/glint:current_glint_toolchain"],
)

# Example data files for testing
filegroup(
    name = "test_data",
    srcs = [
        "example1.txt",
        "example2.txt",
    ],
)

# Create test files
genrule(
    name = "create_test_files",
    outs = [
        "example1.txt",
        "example2.txt",
    ],
    cmd = """
        echo 'This line has trailing spaces    ' > $(location example1.txt)
        echo -e 'This line has\ttabs' >> $(location example1.txt)
        echo -n 'No final newline' >> $(location example1.txt)
        echo 'Clean line' > $(location example2.txt)
        echo 'Another clean line' >> $(location example2.txt)
    """,
)
