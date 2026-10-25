#!/usr/bin/env bash
set -euo pipefail

root="${1%/xbin/gcc}"
sysroot="$2"
arch="$3"
version="$4"
check_glibc="$5"
readelf="$root/bin/readelf"
nm="$root/bin/nm"
cxx="$root/lib64"
if [[ "$arch" == aarch64 ]]; then
    readelf="$root/bin/aarch64-linux-readelf"
    nm="$root/bin/aarch64-linux-nm"
    cxx="$root/aarch64-linux/lib64"
fi
gcc="$root/lib/gcc/$arch-linux/$version"

declare -A defined=() undefined=()
max_major=0
max_minor=0
checked_exports=0

check_version() {
    local symbol="$1" major minor
    if [[ "$symbol" =~ @GLIBC_([0-9]+)\.([0-9]+) ]]; then
        major="${BASH_REMATCH[1]}"
        minor="${BASH_REMATCH[2]}"
        if (( major > 2 || (major == 2 && minor > 31) )); then
            echo "Runtime requires newer than glibc 2.31: $symbol" >&2
            exit 1
        fi
        if (( major > max_major || (major == max_major && minor > max_minor) )); then
            max_major="$major"
            max_minor="$minor"
        fi
    fi
}

# A shared sibling exposes symbol versions, but is NOT evidence that the static
# archive is safe: static objects usually have unversioned undefined names.
symbols="$("$readelf" --dyn-syms --wide "$cxx/libstdc++.so")"
while read -r index value size type bind visibility section symbol rest; do
    if [[ "$section" == UND && -n "${symbol:-}" ]]; then
        check_version "$symbol"
    fi
done <<< "$symbols"

# Resolve strong undefined archive symbols against the other static runtimes,
# GCC's crtbegin/crtend, and glibc's nonshared helpers (e.g. atexit).
for input in "$cxx/libstdc++.a" "$gcc/libgcc.a" "$gcc/libgcc_eh.a" "$gcc/crtbegin.o" "$gcc/crtend.o"; do
    # The shared checker runs nm -u over every member, rejecting versioned
    # requirements and newer unversioned __isoc23_*/__libc_single_threaded names.
    BINARY="$input" NM="$nm" READELF="$readelf" bash "$check_glibc"
    symbols="$("$readelf" --symbols --wide "$input")"
    while read -r index value size type bind visibility section symbol rest; do
        [[ -n "${symbol:-}" && ( "$bind" == GLOBAL || "$bind" == WEAK || "$bind" == UNIQUE ) ]] || continue
        if [[ "$section" == UND ]]; then
            check_version "$symbol"
            [[ "$bind" != GLOBAL ]] || undefined["${symbol%%@*}"]=1
        else
            defined["${symbol%%@*}"]=1
        fi
    done <<< "$symbols"
done

while IFS= read -r input; do
    if [[ "$input" == */libc_nonshared.a ]]; then
        symbols="$("$readelf" --symbols --wide "$input")"
    else
        # Ignore linker scripts named *.so; inspect actual ELF DSOs.
        symbols="$("$readelf" --dyn-syms --wide "$input" 2>/dev/null)" || continue
    fi
    while read -r index value size type bind visibility section symbol rest; do
        [[ -n "${symbol:-}" && "$section" != UND && ( "$bind" == GLOBAL || "$bind" == WEAK ) ]] || continue
        # Private or post-floor exports cannot satisfy a glibc 2.31 contract.
        [[ "$symbol" != *@GLIBC_PRIVATE ]] || continue
        if [[ "$symbol" =~ @+GLIBC_([0-9]+)\.([0-9]+) ]]; then
            major="${BASH_REMATCH[1]}"
            minor="${BASH_REMATCH[2]}"
            (( major < 2 || (major == 2 && minor <= 31) )) || continue
        fi
        defined["${symbol%%@*}"]=1
        checked_exports=$((checked_exports + 1))
    done <<< "$symbols"
done < <(find "$sysroot/lib" "$sysroot/usr/lib" -type f \( -name '*.so*' -o -name libc_nonshared.a \))

(( checked_exports > 0 )) || { echo "No base-sysroot ELF exports found" >&2; exit 1; }
# This one symbol is synthesized by the linker, not libc or a startup object.
defined[_GLOBAL_OFFSET_TABLE_]=1
failed=0
for symbol in "${!undefined[@]}"; do
    if [[ ! -v "defined[$symbol]" ]]; then
        echo "Static runtime symbol unavailable in base glibc <=2.31: $symbol" >&2
        failed=1
    fi
done
(( failed == 0 )) || exit 1
echo "$arch: libstdc++.so maximum GLIBC_$max_major.$max_minor; ${#undefined[@]} strong static undefined names resolved against runtimes/CRT/base glibc <=2.31"
