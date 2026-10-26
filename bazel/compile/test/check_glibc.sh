#!/bin/bash
# Inspect every archive member (or a linked ELF binary) for glibc > 2.31.
# Unversioned newer entry points must also be rejected in relocatable objects.
set -euo pipefail

: "${BINARY:?BINARY must be set}"
NM="${NM:-nm}"
READELF="${READELF:-readelf}"

# Capture complete output before matching: grep -q pipelines can SIGPIPE nm,
# and inspecting only one archive member misses incompatible references.
undefined="$("${NM}" -u "${BINARY}")"
if grep -E '(^|[[:space:]])(__isoc23_[^[:space:]@]*|__libc_single_threaded)(@[^[:space:]]*)?([[:space:]]|$)' <<< "${undefined}"; then
    echo "FAIL: ${BINARY} references glibc entry points newer than 2.31"
    exit 1
fi

versions="$("${READELF}" --version-info "${BINARY}")"
if ! awk '
    {
        line = $0
        while (match(line, /GLIBC_[0-9]+(\.[0-9]+)+/)) {
            version = substr(line, RSTART + 6, RLENGTH - 6)
            count = split(version, parts, ".")
            # Compare numeric components, not strings (2.9 < 2.31 < 2.100).
            for (i = 1; i <= count; i++) {
                limit = (i == 1 ? 2 : (i == 2 ? 31 : 0))
                if (parts[i] + 0 > limit) {
                    print "FAIL: GLIBC_" version " exceeds GLIBC_2.31"
                    failed = 1
                    break
                }
                if (parts[i] + 0 < limit) {
                    break
                }
            }
            line = substr(line, RSTART + RLENGTH)
        }
    }
    END { exit failed }
' <<< "${undefined}
${versions}"; then
    exit 1
fi
echo "PASS: ${BINARY} requires no glibc newer than 2.31"

if [[ "${CHECK_STATIC_RUNTIME:-false}" == "true" ]]; then
    dynamic="$("${READELF}" -d "${BINARY}")"
    if grep -E '\(NEEDED\).*(libstdc\+\+|libgcc_s)' <<< "${dynamic}"; then
        echo "FAIL: ${BINARY} dynamically links the GCC C++ runtime"
        exit 1
    fi
    echo "PASS: no dynamic libstdc++ or libgcc_s dependencies"
fi
