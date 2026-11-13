#!/usr/bin/env bash
# //coverage:llvm_support against a fake llvm-cov that records its arguments.
set -euo pipefail

f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090
source "${RUNFILES_DIR:-$TEST_SRCDIR}/$f"
LLVM_COV_WRAPPER="$(rlocation "$LLVM_COV_WRAPPER")"

WORK="$PWD/llvm-wrappers-test.${BASHPID}"
mkdir -p "$WORK/bin"
trap 'rm -rf -- "$WORK"' EXIT
for tool in llvm-cov llvm-profdata; do
    printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$@" > "%s/%s.args"\n' "$WORK" "$tool" > "$WORK/bin/$tool"
    chmod +x "$WORK/bin/$tool"
done
export COVERAGE_GCOV_PATH="$WORK/bin/llvm-profdata"

expect_args() {
    local tool="$1"; shift
    [[ "$(cat "$WORK/$tool.args")" == "$(printf '%s\n' "$@")" ]] \
        || { echo "$tool got: $(tr '\n' ' ' < "$WORK/$tool.args")" >&2; exit 1; }
}

# export gets the skips and the external-path ignore, right after the subcommand.
"$LLVM_COV_WRAPPER" export -instr-profile "$WORK/x.data" -format=lcov -object "$WORK/bin/test"
expect_args llvm-cov export -skip-functions -skip-branches \
    '-ignore-filename-regex=^(external|bazel-out/[^/]+/bin/external)/' \
    -instr-profile "$WORK/x.data" -format=lcov -object "$WORK/bin/test"
# The ignore pattern matches external and generated-external paths only.
regex='^(external|bazel-out/[^/]+/bin/external)/'
for p in external/abseil-cpp+/absl/x.h bazel-out/k8-fastbuild/bin/external/grpc+/x.cc; do
    [[ "$p" =~ $regex ]] || { echo "should ignore: $p" >&2; exit 1; }
done
for p in source/common/x.cc envoy/x.h bazel-out/k8-fastbuild/bin/source/common/version.h test/x.cc; do
    [[ "$p" =~ $regex ]] && { echo "must keep: $p" >&2; exit 1; }
done
# The ignore pattern can be replaced or disabled.
LLVM_COV_IGNORE_FILENAME_REGEX='^third_party/' "$LLVM_COV_WRAPPER" export -format=lcov
expect_args llvm-cov export -skip-functions -skip-branches '-ignore-filename-regex=^third_party/' -format=lcov
LLVM_COV_IGNORE_FILENAME_REGEX='' "$LLVM_COV_WRAPPER" export -format=lcov
expect_args llvm-cov export -skip-functions -skip-branches -format=lcov
# Other subcommands pass through.
"$LLVM_COV_WRAPPER" show -instr-profile "$WORK/x.data"
expect_args llvm-cov show -instr-profile "$WORK/x.data"
"$LLVM_COV_WRAPPER"
[[ -z "$(cat "$WORK/llvm-cov.args")" ]]
# The real tool is found through COVERAGE_GCOV_PATH.
if env -u COVERAGE_GCOV_PATH "$LLVM_COV_WRAPPER" export 2>"$WORK/err"; then
    echo "Expected failure without COVERAGE_GCOV_PATH" >&2
    exit 1
fi
grep -q COVERAGE_GCOV_PATH "$WORK/err"
