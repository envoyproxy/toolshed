#!/usr/bin/env bash
# Test script to verify network connectivity for Pants build system
# This script tests connectivity to all required domains for Pants to function

set -euo pipefail

COLOR_RED="\x1b[31m"
COLOR_GREEN="\x1b[32m"
COLOR_YELLOW="\x1b[33m"
COLOR_RESET="\x1b[0m"

function log() {
  echo -e "$@" 1>&2
}

function green() {
  log "${COLOR_GREEN}✓ $*${COLOR_RESET}"
}

function red() {
  log "${COLOR_RED}✗ $*${COLOR_RESET}"
}

function yellow() {
  log "${COLOR_YELLOW}⚠ $*${COLOR_RESET}"
}

echo "Testing Pants Network Requirements"
echo "==================================="
echo ""

# Track results
PASSED=0
FAILED=0
WARNINGS=0

# Test function
test_url() {
  local url="$1"
  local description="$2"
  local required="$3"
  
  echo -n "Testing $description... "
  
  if curl -s -I -L --max-time 10 --connect-timeout 5 "$url" > /dev/null 2>&1; then
    green "OK"
    ((PASSED++))
    return 0
  else
    if [[ "$required" == "required" ]]; then
      red "FAILED (Required)"
      ((FAILED++))
    else
      yellow "FAILED (Optional)"
      ((WARNINGS++))
    fi
    return 1
  fi
}

echo "1. GitHub Domains (Pants Binary & Python Interpreters)"
echo "--------------------------------------------------------"
test_url "https://github.com/pantsbuild/scie-pants/releases" "github.com - scie-pants releases" "required"
test_url "https://github.com/pantsbuild/pants/releases" "github.com - pants releases" "required"
test_url "https://github.com/indygreg/python-build-standalone/releases" "github.com - python-build-standalone" "required"
test_url "https://objects.githubusercontent.com" "objects.githubusercontent.com - GitHub CDN" "required"
test_url "https://raw.githubusercontent.com/pantsbuild/pants/main/README.md" "raw.githubusercontent.com - raw content" "optional"

echo ""
echo "2. PyPI Domains (Python Packages)"
echo "----------------------------------"
test_url "https://pypi.org/simple/" "pypi.org - package index" "required"
test_url "https://pypi.org/pypi/jinja2/json" "pypi.org - package API" "required"
test_url "https://files.pythonhosted.org" "files.pythonhosted.org - PyPI CDN" "required"

echo ""
echo "3. Specific Pants Resources"
echo "---------------------------"
# Test actual URLs that Pants will use
PANTS_VERSION="2.23.0"
PANTS_OS="linux"
PANTS_ARCH="x86_64"

test_url "https://github.com/pantsbuild/scie-pants/releases/latest" "scie-pants latest release redirect" "required"
test_url "https://github.com/pantsbuild/pants/releases/download/release_${PANTS_VERSION}/pants.${PANTS_VERSION}.pex" "Pants ${PANTS_VERSION} PEX" "required"

echo ""
echo "Summary"
echo "======="
echo ""
log "Passed:   ${COLOR_GREEN}${PASSED}${COLOR_RESET}"
if [[ $WARNINGS -gt 0 ]]; then
  log "Warnings: ${COLOR_YELLOW}${WARNINGS}${COLOR_RESET}"
fi
if [[ $FAILED -gt 0 ]]; then
  log "Failed:   ${COLOR_RED}${FAILED}${COLOR_RESET}"
fi

echo ""
if [[ $FAILED -eq 0 ]]; then
  green "All required domains are accessible!"
  echo ""
  echo "Pants should be able to:"
  echo "  - Download the scie-pants launcher"
  echo "  - Download the Pants PEX for version ${PANTS_VERSION}"
  echo "  - Download Python interpreters"
  echo "  - Download Python packages from PyPI"
  exit 0
else
  red "Some required domains are NOT accessible!"
  echo ""
  echo "Pants will likely fail during:"
  echo "  - Bootstrap (if GitHub is blocked)"
  echo "  - Initialization (if GitHub is blocked)"
  echo "  - Dependency resolution (if PyPI is blocked)"
  echo ""
  echo "Add these domains to COPILOT_AGENT_FIREWALL_ALLOW_LIST_ADDITIONS:"
  echo "  - github.com"
  echo "  - objects.githubusercontent.com"
  echo "  - pypi.org"
  echo "  - files.pythonhosted.org"
  echo ""
  echo "See .github/PANTS_FIREWALL_ALLOWLIST.md for details"
  exit 1
fi
