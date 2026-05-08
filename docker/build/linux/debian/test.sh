#!/bin/bash -e

# ensure python can print unicode
python3 -c "print(chr(9786))"
# ensure clangd and clang-format are available on PATH
clangd --version
clang-format --version
