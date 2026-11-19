#!/usr/bin/env bash
set -euo pipefail

compiler="$PWD/$1"
readelf="${compiler%gcc}readelf"
arch="$3"
flags=()
while IFS= read -r flag; do
    # Toolchain flags use execroot paths; tests stage repos at the runfiles root.
    flags+=("${flag//external\//}")
done < "$2"
compile_flags=()
while IFS= read -r flag; do
    compile_flags+=("${flag//external\//}")
done < "$4"

cd "$TEST_SRCDIR"
cat > "$TEST_TMPDIR/main.cc" <<'EOF'
extern int answer();
int main() { return answer() != 42; }
EOF
cat > "$TEST_TMPDIR/answer.cc" <<'EOF'
#include <string>
#include <vector>
int answer() { return std::stoi(std::vector<std::string>{"42"}.at(0)); }
EOF
# Keep toolchain search paths relative, as in an action with a cleared environment.
env - "$compiler" "${compile_flags[@]}" -c "$TEST_TMPDIR/answer.cc" -o "$TEST_TMPDIR/answer.o"
env - "$compiler" "${compile_flags[@]}" "${flags[@]}" "$TEST_TMPDIR/main.cc" -Wl,--start-lib "$TEST_TMPDIR/answer.o" -Wl,--end-lib -o "$TEST_TMPDIR/program"

cd "$TEST_TMPDIR"
"$readelf" -p .comment program > comment
grep -q 'Linker: LLD' comment
"$readelf" --program-headers --wide program > headers
grep -Eq 'GNU_STACK[[:space:]]+([^[:space:]]+[[:space:]]+){5}RW[[:space:]]' headers
if [[ "$arch" == x86_64 ]]; then
    ./program
fi
