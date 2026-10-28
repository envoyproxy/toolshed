#!/usr/bin/env bash
set -euo pipefail

compiler="$PWD/$1"
readelf="${compiler%/gcc}/readelf"
arch="$3"
flags=()
while IFS= read -r flag; do
    # Toolchain flags use execroot paths; tests stage repos at the runfiles root.
    flags+=("${flag//external\//$TEST_SRCDIR/}")
done < "$2"

cd "$TEST_TMPDIR"
cat > main.cc <<'EOF'
extern int answer();
int main() { return answer() != 42; }
EOF
cat > answer.cc <<'EOF'
int answer() { return 42; }
EOF
"$compiler" "${flags[@]}" -c answer.cc -o answer.o
"$compiler" "${flags[@]}" main.cc -Wl,--start-lib answer.o -Wl,--end-lib -o program

"$readelf" -p .comment program > comment
grep -q 'Linker: LLD' comment
"$readelf" --program-headers --wide program > headers
grep -Eq 'GNU_STACK[[:space:]]+([^[:space:]]+[[:space:]]+){5}RW[[:space:]]' headers
if [[ "$arch" == x86_64 ]]; then
    ./program
fi
