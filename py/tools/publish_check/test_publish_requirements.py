"""Validation tests for setup.cfg publish requirement ranges.

Check B: dev resolve ⊆ published ranges. Parse py/deps/requirements.txt
to get a map of name → resolved version. For each entry in every
package's setup.cfg ``install_requires``, look up the corresponding
resolved version and assert it satisfies the range. Toolshed packages
(published under py/) are skipped since they are not pinned in
requirements.txt with a single canonical dev version.
"""

import configparser
import pathlib
import re
from typing import Dict, List, Tuple

import pytest
from packaging.requirements import Requirement
from packaging.version import Version
from packaging.utils import canonicalize_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


def _find_publishable_packages() -> List[pathlib.Path]:
    """Return package dirs under py/ with install_requires in setup.cfg."""
    py_dir = _REPO_ROOT / "py"
    publishable = []
    for pkg_dir in sorted(p for p in py_dir.glob("*") if p.is_dir()):
        if _read_setup_cfg_install_requires(pkg_dir):
            publishable.append(pkg_dir)
    return publishable


def _read_setup_cfg_install_requires(
        pkg_dir: pathlib.Path) -> List[str]:
    """Return install_requires from setup.cfg, or [] if absent."""
    cfg = configparser.ConfigParser()
    cfg.read(pkg_dir / "setup.cfg")
    if not cfg.has_section("options"):
        return []
    raw = cfg["options"].get("install_requires", "")
    return [
        line.strip()
        for line in raw.strip().splitlines()
        if line.strip()]


def _parse_dev_resolve(
        requirements_txt: pathlib.Path) -> Dict[str, Version]:
    """Parse py/deps/requirements.txt into {canonical_name: Version}."""
    result: Dict[str, Version] = {}
    pattern = re.compile(r"^([A-Za-z0-9._-]+)==([0-9][^\s]*)", re.MULTILINE)
    for name, ver in pattern.findall(requirements_txt.read_text()):
        result[canonicalize_name(name)] = Version(ver)
    return result


# ---------------------------------------------------------------------------
# Build parametrized test data
# ---------------------------------------------------------------------------

_PUBLISHABLE_PACKAGES = _find_publishable_packages()

_DEV_RESOLVE: Dict[str, Version] = _parse_dev_resolve(
    _REPO_ROOT / "py" / "deps" / "requirements.txt")

# Canonical names of toolshed packages (skip in Check B).
_TOOLSHED_CANONICAL_NAMES = frozenset(
    canonicalize_name(p.name)
    for p in _PUBLISHABLE_PACKAGES)


# ---------------------------------------------------------------------------
# Check B: dev resolve ⊆ setup.cfg published ranges
# ---------------------------------------------------------------------------

def _check_b_cases() -> List[Tuple[pathlib.Path, str]]:
    """Collect (pkg_dir, req_str) pairs to parametrize Check B."""
    cases = []
    for pkg_dir in _PUBLISHABLE_PACKAGES:
        for req_str in _read_setup_cfg_install_requires(pkg_dir):
            req = Requirement(req_str)
            if canonicalize_name(req.name) not in _TOOLSHED_CANONICAL_NAMES:
                cases.append((pkg_dir, req_str))
    return cases


def _case_id(case: Tuple[pathlib.Path, str]) -> str:
    pkg_dir, req_str = case
    return f"{pkg_dir.name}::{req_str}"


@pytest.mark.parametrize("case", _check_b_cases(), ids=_case_id)
def test_dev_resolve_satisfies_publish_range(
        case: Tuple[pathlib.Path, str]) -> None:
    """The dev-pinned version must satisfy the publish range."""
    pkg_dir, req_str = case
    req = Requirement(req_str)
    canon = canonicalize_name(req.name)

    dev_version = _DEV_RESOLVE.get(canon)
    if dev_version is None:
        pytest.skip(
            f"{pkg_dir.name}: {req.name!r} not found in "
            f"py/deps/requirements.txt — skipping range check")

    assert dev_version in req.specifier, (
        f"{pkg_dir.relative_to(_REPO_ROOT)}: "
        f"setup.cfg install_requires declares {req_str!r} but "
        f"dev resolve has {req.name}=={dev_version}, "
        f"which does not satisfy the range. "
        f"Either loosen the publish range or bump the dev pin."
    )
