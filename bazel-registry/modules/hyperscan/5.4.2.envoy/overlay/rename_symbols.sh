#!/bin/bash
# Symbol renaming script for hyperscan fat runtime
# Usage: rename_symbols.sh <prefix> <input.a> <output.a>

set -e

PREFIX=$1
INPUT_AR=$(realpath "$2")
OUTPUT_AR=$(realpath "$3")

# Create temporary directory for work
TMPDIR=$(mktemp -d)
trap "rm -rf ${TMPDIR}" EXIT

# Keep symbols (from cmake/keep.syms.in)
KEEPSYMS="${TMPDIR}/keep.syms"
cat > "${KEEPSYMS}" << 'EOF'
hs_misc_alloc
hs_misc_free
hs_free_scratch
hs_stream_alloc
hs_stream_free
hs_scratch_alloc
hs_scratch_free
hs_database_alloc
hs_database_free
^_
EOF

# Extract archive to temporary directory
cd "${TMPDIR}"
ar x "${INPUT_AR}"

# Process each object file
for obj in *.o; do
    SYMSFILE="${obj}.syms"
    
    # Get all global symbols from the object, filter out keep symbols,
    # and create rename map
    nm -f p -g "${obj}" | cut -f1 -d' ' | grep -v -f "${KEEPSYMS}" | sed -e "s/\(.*\)/\1 ${PREFIX}_\1/" > "${SYMSFILE}"
    
    # Rename symbols if any need renaming
    if [ -s "${SYMSFILE}" ]; then
        objcopy --redefine-syms="${SYMSFILE}" "${obj}"
    fi
    
    rm -f "${SYMSFILE}"
done

# Create output archive with renamed symbols
ar rcs "${OUTPUT_AR}" *.o

# Return to original directory
cd - > /dev/null
