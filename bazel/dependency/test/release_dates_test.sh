#!/bin/bash
set -euo pipefail

if [ -n "${TEST_SRCDIR:-}" ]; then
  if [ -d "${TEST_SRCDIR}/envoy_toolshed" ]; then
    RUNFILES_DIR="${TEST_SRCDIR}/envoy_toolshed"
  else
    RUNFILES_DIR="${TEST_SRCDIR}/_main"
  fi
  UPDATE_SCRIPT="${RUNFILES_DIR}/dependency/release-dates.sh"
  TESTDATA="${RUNFILES_DIR}/dependency/test/testdata/release_dates"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  UPDATE_SCRIPT="${SCRIPT_DIR}/../release-dates.sh"
  TESTDATA="${SCRIPT_DIR}/testdata/release_dates"
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

fixtures() {
  cp "${TESTDATA}/deps.yaml" "${TESTDATA}/api.yaml" "${tmpdir}/"
  chmod u+w "${tmpdir}/deps.yaml" "${tmpdir}/api.yaml"
}

# The lines that differ from the fixture, as `<line number>:<new line>`.
changes() {
  diff --unchanged-line-format= --old-line-format= --new-line-format='%dn:%L' \
       "${TESTDATA}/$1" "${tmpdir}/$1" || :
}

export RELEASE_DATES_METADATA="${tmpdir}/deps.yaml
${tmpdir}/api.yaml"

# A stand-in for the checker. It reports a mismatch for the dependencies that it is given, with
# coloured output, a summary that repeats them, and the exit code of a failed check, and records
# which dependencies it was run on.
check="${tmpdir}/check"
cat > "$check" <<CHECK
#!/bin/bash
[[ "\$1" == --repository_locations=* && "\$2 \$3" == "-c release_dates" && \$# == 3 ]] \
  || { echo "unexpected args: \$*"; exit 2; }
"${JQ_BIN:-jq}" -r 'keys | join(" ")' "\${1#--repository_locations=}" > "${tmpdir}/checked"
mismatch() {
  grep -qw "\$1" "${tmpdir}/checked" || return 0
  printf '\033[34mDependencyChecker\033[0m \033[1;36mERROR\033[0m \033[1;31m[release_dates] Mismatch: %s %s != %s\033[0m\r\n' "\$@"
  echo "[release_dates] Mismatch: \$1 \$2 != \$3" >> "${tmpdir}/summary"
}
: > "${tmpdir}/summary"
mismatch fmt 2026-06-16 2026-11-07
mismatch rules_buf 2026-04-30 2026-11-05
printf '\033[32m[release_dates] Match (2026-08-17): abseil-cpp\033[0m\n'
echo 'DependencyChecker ERROR ERRORS Summary [release_dates]:'
cat "${tmpdir}/summary"
[[ ! -s "${tmpdir}/summary" ]] || exit 1
CHECK
chmod +x "$check"

DEPENDENCIES="${TESTDATA}/dependencies.json"

update() {
  "${UPDATE_SCRIPT}" "$@"
}

lookup() {
  RELEASE_DATES_CHECK="$check" RELEASE_DATES_DEPENDENCIES="$DEPENDENCIES" update "$@"
}

# The dates of the named dependencies are looked up, by a check of only those.
fixtures
lookup fmt abseil-cpp > "${tmpdir}/out"
[[ "$(cat "${tmpdir}/checked")" == "abseil-cpp fmt" ]] \
  || fail "the check was run on: $(cat "${tmpdir}/checked")"
[[ "$(changes deps.yaml)" == '13:  release_date: "2026-11-07"  # trailing comment' ]] \
  || fail "lookup: deps.yaml changed unexpectedly: $(changes deps.yaml)"
# fmt is in both files, and is fixed in both; rules_buf was not named.
[[ "$(changes api.yaml)" == '8:  release_date: "2026-11-07"' ]] \
  || fail "lookup: api.yaml changed unexpectedly: $(changes api.yaml)"
grep -q "abseil-cpp: no release date to fix" "${tmpdir}/out" || fail "no report for abseil-cpp"
grep -q "Release dates: 1 updated, 0 already set" "${tmpdir}/out" \
  || fail "lookup: unexpected summary: $(tail -n1 "${tmpdir}/out")"

# A lookup and a given date together: only the lookup is checked.
fixtures
lookup rules_buf zstd=2026-11-11 > "${tmpdir}/out"
[[ "$(cat "${tmpdir}/checked")" == "rules_buf" ]] \
  || fail "the check was run on: $(cat "${tmpdir}/checked")"
[[ "$(changes deps.yaml)" == "39:  release_date: '2026-11-11'" ]] \
  || fail "mixed: deps.yaml changed unexpectedly: $(changes deps.yaml)"
[[ "$(changes api.yaml)" == '3:  release_date: "2026-11-05"' ]] \
  || fail "mixed: api.yaml changed unexpectedly: $(changes api.yaml)"

# A dependency can be named as the module that it is, where that is not its key.
fixtures
lookup fmt-module > "${tmpdir}/out"
[[ "$(cat "${tmpdir}/checked")" == "fmt" ]] || fail "the check was run on: $(cat "${tmpdir}/checked")"
[[ "$(changes deps.yaml)" == '13:  release_date: "2026-11-07"  # trailing comment' ]] \
  || fail "module name: deps.yaml changed unexpectedly: $(changes deps.yaml)"

# Names that are not dependencies can be skipped: the rest are looked up.
fixtures
lookup --skip-unknown nope rules_buf nor-this > "${tmpdir}/out"
[[ "$(cat "${tmpdir}/checked")" == "rules_buf" ]] \
  || fail "the check was run on: $(cat "${tmpdir}/checked")"
grep -q "Not in the dependencies, skipped: nope nor-this" "${tmpdir}/out" || fail "no report of the skipped"
[[ "$(changes api.yaml)" == '3:  release_date: "2026-11-05"' ]] \
  || fail "skip: api.yaml changed unexpectedly: $(changes api.yaml)"

# ... and if none are left, nothing is checked.
fixtures
rm -f "${tmpdir}/checked"
lookup --skip-unknown nope > "${tmpdir}/out"
[[ ! -e "${tmpdir}/checked" ]] || fail "the check was run with nothing to look up"
grep -q "Release dates: 0 updated, 0 already set" "${tmpdir}/out" || fail "unexpected summary"

# A name that is not a dependency is an error, before anything is checked.
fixtures
rm -f "${tmpdir}/checked"
if lookup fmt nope > "${tmpdir}/out" 2> "${tmpdir}/err"; then
  fail "expected a failure for an unknown dependency"
fi
grep -q "Not in the dependencies: nope" "${tmpdir}/err" || fail "unexpected error for nope"
[[ ! -e "${tmpdir}/checked" ]] || fail "the check was run for an unknown dependency"
[[ -z "$(changes deps.yaml)$(changes api.yaml)" ]] || fail "changed for an unknown dependency"

# With no arguments every dependency is checked, and what is reported is fixed.
fixtures
lookup > "${tmpdir}/out"
[[ "$(cat "${tmpdir}/checked")" == "abseil-cpp fmt nested rules_buf zstd" ]] \
  || fail "the check was run on: $(cat "${tmpdir}/checked")"
[[ "$(changes deps.yaml)" == '13:  release_date: "2026-11-07"  # trailing comment' ]] \
  || fail "all: deps.yaml changed unexpectedly: $(changes deps.yaml)"
expected_api='3:  release_date: "2026-11-05"
8:  release_date: "2026-11-07"'
[[ "$(changes api.yaml)" == "$expected_api" ]] \
  || fail "all: api.yaml changed unexpectedly: $(changes api.yaml)"
grep -q "Release dates: 2 updated, 0 already set" "${tmpdir}/out" \
  || fail "all: unexpected summary: $(tail -n1 "${tmpdir}/out")"

# A check with nothing to report.
fixtures
lookup nested > "${tmpdir}/out"
[[ -z "$(changes deps.yaml)$(changes api.yaml)" ]] || fail "changed with nothing to fix"
grep -q "Release dates: 0 updated, 0 already set" "${tmpdir}/out" || fail "unexpected summary"

# A check that fails for another reason is a failure, with its output.
fixtures
printf '#!/bin/bash\necho "GitHub rate limit exceeded"\nexit 1\n' > "${tmpdir}/check_broken"
chmod +x "${tmpdir}/check_broken"
if RELEASE_DATES_CHECK="${tmpdir}/check_broken" RELEASE_DATES_DEPENDENCIES="$DEPENDENCIES" \
     update fmt > "${tmpdir}/out" 2> "${tmpdir}/err"; then
  fail "expected a failure when the check fails with no mismatch"
fi
grep -q "GitHub rate limit exceeded" "${tmpdir}/err" || fail "the output of the failed check is not shown"
[[ -z "$(changes deps.yaml)$(changes api.yaml)" ]] || fail "changed though the check failed"

# A lookup with no checker.
for args in "" "fmt"; do
  # shellcheck disable=SC2086
  if update $args > "${tmpdir}/out" 2> "${tmpdir}/err"; then
    fail "expected a failure for a lookup with no checker"
  fi
  grep -q "No checker and dependencies" "${tmpdir}/err" || fail "unexpected error with no checker"
done

# Dates given as arguments, quoted, unquoted and with a comment.
fixtures
update fmt=2026-11-07 unquoted=2026-03-04 zstd=2026-11-11 abseil-cpp=2026-08-17 > "${tmpdir}/out"
expected_deps='13:  release_date: "2026-11-07"  # trailing comment
35:  release_date: 2026-03-04
39:  release_date: '"'"'2026-11-11'"'"''
[[ "$(changes deps.yaml)" == "$expected_deps" ]] \
  || fail "deps.yaml changed unexpectedly: $(changes deps.yaml)"
[[ "$(changes api.yaml)" == '8:  release_date: "2026-11-07"' ]] \
  || fail "api.yaml changed unexpectedly: $(changes api.yaml)"
grep -q "fmt 2026-06-16 -> 2026-11-07" "${tmpdir}/out" || fail "no report of the fmt update"
grep -q "Release dates: 3 updated, 1 already set" "${tmpdir}/out" \
  || fail "unexpected summary: $(tail -n1 "${tmpdir}/out")"

# Only the field of the dependency itself is changed: not one in a block scalar, a nested mapping
# or a comment, though they hold the same date.
fixtures
update nested=2026-05-05 > "${tmpdir}/out"
[[ "$(changes deps.yaml)" == '26:  release_date: "2026-05-05"' ]] \
  || fail "nested: changed unexpectedly: $(changes deps.yaml)"

# A dependency that is not in the files, or has no date, is an error, after the rest are updated.
fixtures
if update no-date=2026-01-01 missing=2026-01-01 zstd=2026-11-11 > "${tmpdir}/out" 2> "${tmpdir}/err"; then
  fail "expected a failure for unknown dependencies"
fi
grep -q "no release_date found for no-date" "${tmpdir}/err" || fail "no error for no-date"
grep -q "no release_date found for missing" "${tmpdir}/err" || fail "no error for missing"
grep -q "2 of 3 dependencies not found" "${tmpdir}/err" || fail "unexpected failure summary"
[[ "$(changes deps.yaml)" == "39:  release_date: '2026-11-11'" ]] \
  || fail "zstd was not updated alongside the failures"

# Usage errors.
fixtures
for bad in "fmt=tomorrow" "fmt 2026-11-07" "=2026-11-07"; do
  if update "$bad" > "${tmpdir}/out" 2> "${tmpdir}/err"; then
    fail "expected a failure for the argument: ${bad}"
  fi
  grep -q "Expected <name> or <name>=<date>" "${tmpdir}/err" || fail "unexpected error for: ${bad}"
done
[[ -z "$(changes deps.yaml)$(changes api.yaml)" ]] || fail "changed on a usage error"
if RELEASE_DATES_METADATA="${tmpdir}/nope.yaml" update fmt=2026-11-07 2> "${tmpdir}/err"; then
  fail "expected a failure for a missing file"
fi
grep -q "No such file" "${tmpdir}/err" || fail "no error for the missing file"
if RELEASE_DATES_METADATA="" update fmt=2026-11-07 2> "${tmpdir}/err"; then
  fail "expected a failure with no files"
fi
grep -q "No metadata files" "${tmpdir}/err" || fail "no error for no files"

echo "PASS"
