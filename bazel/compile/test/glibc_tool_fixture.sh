#!/bin/bash
# Deliberately accept only the arguments used by the checker.
set -euo pipefail
[[ "$#" -eq 2 && "$2" == "fixture.a" ]] || exit 90
case "$1" in
    -u)
        [[ "${FIXTURE_NM_FAIL:-false}" != "true" ]] || exit 91
        printf 'first.o:\n                 U memcpy\n'
        if [[ "${FIXTURE_LARGE:-false}" == "true" ]]; then
            for ((i = 0; i < 5000; i++)); do
                printf '                 U harmless_symbol_%s\n' "${i}"
            done
        fi
        printf 'last.o:\n                 %s\n' "${FIXTURE_UNDEFINED:-U memcpy@GLIBC_2.31}"
        ;;
    --version-info)
        [[ "${FIXTURE_READELF_FAIL:-false}" != "true" ]] || exit 92
        printf '%s\n' "${FIXTURE_VERSIONS:-No version information found.}"
        ;;
    -d)
        printf '%s\n' "${FIXTURE_DYNAMIC:-There is no dynamic section in this file.}"
        ;;
    *) exit 93 ;;
esac
