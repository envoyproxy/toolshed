"""End-to-end test: verify the built wheel METADATA for the test fixture
package.

This test builds the ``toolshed-test-publish-pkg`` wheel via
``runtime_package_dependencies`` (pants produces the wheel before the test
sandbox is created) then cracks it open and asserts that:

- Name, Version, Summary, Requires-Python match setup.cfg exactly.
- Classifier lines include the expected values.
- Requires-Dist contains the **loose** specifiers from setup.cfg
  ``install_requires`` via synthetic publish requirement targets, NOT the
  pinned ``==`` versions from the dev resolve.
- No extra packages leak in from the dev resolve (count check).
- The ``dev`` extras_require group appears as Provides-Extra / Requires-Dist.
- entry_points.txt in the dist-info has the expected console_scripts entry.

The test intentionally fails if the toolshed_package macro wires pinned dev
deps into the wheel instead of the per-package setup.cfg ranges.
"""

import glob
import os
import pathlib
import zipfile
from email.message import Message
from email.parser import Parser
from typing import List, Tuple

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


# ---------------------------------------------------------------------------
# Expected values — must match py/_test_publish_pkg/setup.cfg exactly
# ---------------------------------------------------------------------------

_EXPECTED_NAME = "toolshed-test-publish-pkg"
_EXPECTED_VERSION = "0.0.1"
_EXPECTED_SUMMARY = "Toolshed test fixture for publish metadata validation"
_EXPECTED_PYTHON_REQUIRES = ">=3.12"

_EXPECTED_CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Programming Language :: Python :: 3.12",
]

# These must be LOOSE ranges, not == pins.
_EXPECTED_INSTALL_REQUIRES = [
    "aiohttp>=3.8.1",
    "packaging>=23.0",
    "pyyaml",
]

_EXPECTED_EXTRA = "dev"
_EXPECTED_CONSOLE_SCRIPT = "toolshed-test-publish-pkg"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_wheel() -> pathlib.Path:
    """Locate the built wheel in the pants test sandbox.

    pants places ``runtime_package_dependencies`` artefacts at their normal
    dist/ output path but with the ``dist/`` prefix stripped.  For the target
    at ``//py/_test_publish_pkg:package`` the wheel lands at::

        py/_test_publish_pkg/toolshed_test_publish_pkg-<ver>-*.whl

    We glob broadly in case the exact sub-path differs between pants versions.
    """
    candidates = (
        glob.glob("py/_test_publish_pkg/*.whl")
        + glob.glob("**/*.whl", recursive=True)
    )
    whl_files = [
        p for p in candidates
        if "toolshed_test_publish_pkg" in os.path.basename(p)
        or "toolshed-test-publish-pkg" in os.path.basename(p)
    ]
    if not whl_files:
        all_whl = glob.glob("**/*.whl", recursive=True)
        pytest.fail(
            f"Could not find toolshed_test_publish_pkg wheel.\n"
            f"cwd={os.getcwd()!r}\n"
            f"all .whl files found: {all_whl}")
    return pathlib.Path(whl_files[0])


def _read_metadata(wheel_path: pathlib.Path) -> Tuple[Message, List[str]]:
    """Open the wheel zip and return the parsed METADATA Message."""
    with zipfile.ZipFile(wheel_path) as zf:
        metadata_names = [
            n for n in zf.namelist()
            if n.endswith("/METADATA") and ".dist-info/" in n
        ]
        assert len(metadata_names) == 1, (
            f"Expected exactly one METADATA in {wheel_path.name}, "
            f"found: {metadata_names}")
        return Parser().parsestr(
            zf.read(metadata_names[0]).decode("utf-8")), zf.namelist()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_wheel_basic_metadata() -> None:
    """Name, Version, Summary, Requires-Python match setup.cfg."""
    wheel_path = _find_wheel()
    msg, _ = _read_metadata(wheel_path)

    assert msg["Name"] == _EXPECTED_NAME, (
        f"Name mismatch: expected {_EXPECTED_NAME!r}, got {msg['Name']!r}")
    assert msg["Version"] == _EXPECTED_VERSION, (
        f"Version mismatch: expected {_EXPECTED_VERSION!r}, "
        f"got {msg['Version']!r}")
    assert msg["Summary"] == _EXPECTED_SUMMARY, (
        f"Summary mismatch: expected {_EXPECTED_SUMMARY!r}, "
        f"got {msg['Summary']!r}")
    assert msg["Requires-Python"] == _EXPECTED_PYTHON_REQUIRES, (
        f"Requires-Python mismatch: expected {_EXPECTED_PYTHON_REQUIRES!r}, "
        f"got {msg['Requires-Python']!r}")


def test_wheel_classifiers() -> None:
    """Classifier lines include the expected values from setup.cfg."""
    wheel_path = _find_wheel()
    msg, _ = _read_metadata(wheel_path)

    classifiers: List[str] = msg.get_all("Classifier") or []
    for expected in _EXPECTED_CLASSIFIERS:
        assert expected in classifiers, (
            f"Expected classifier {expected!r} not found.\n"
            f"All classifiers: {classifiers}")


def test_wheel_requires_dist_loose_ranges() -> None:
    """Requires-Dist must contain LOOSE ranges, never == pins.

    This is the key test: if the toolshed_package macro mistakenly wires
    the pinned //py/deps:reqs#* targets into the wheel instead of (or in
    addition to) the synthetic per-package publish requirement targets, the
    Requires-Dist
    will contain ``==`` specifiers and this test will fail.
    """
    wheel_path = _find_wheel()
    msg, _ = _read_metadata(wheel_path)

    all_requires_dist: List[str] = msg.get_all("Requires-Dist") or []
    full_block = "\n".join(f"  Requires-Dist: {r}" for r in all_requires_dist)

    # Split into main (unconditional) and extra-gated deps.
    main_requires = [
        r for r in all_requires_dist
        if "; extra ==" not in r
    ]

    actual_requires: dict = {
        canonicalize_name(Requirement(r).name): Requirement(r)
        for r in main_requires
    }

    for expected_str in _EXPECTED_INSTALL_REQUIRES:
        expected = Requirement(expected_str)
        canon = canonicalize_name(expected.name)

        assert canon in actual_requires, (
            f"Expected {expected_str!r} in Requires-Dist (unconditional) "
            f"but not found.\n"
            f"All Requires-Dist:\n{full_block}")

        actual = actual_requires[canon]

        # Check the specifier matches the loose range, not a pin.
        if str(expected.specifier):
            assert str(actual.specifier) == str(expected.specifier), (
                f"Specifier mismatch for {expected.name!r}: "
                f"expected {str(expected.specifier)!r}, "
                f"got {str(actual.specifier)!r}.\n"
                f"All Requires-Dist:\n{full_block}")

        # The key assertion: no == operator in any specifier.
        for spec in actual.specifier:
            assert spec.operator != "==", (
                f"Wheel has pinned dep {actual.name}{actual.specifier} "
                f"(operator ==) — expected a loose range.\n"
                f"This indicates the toolshed_package macro is walking "
                f"pinned dev deps into the wheel instead of "
                f"setup.cfg ranges.\n"
                f"All Requires-Dist:\n{full_block}")


def test_wheel_requires_dist_no_extra_packages() -> None:
    """Main Requires-Dist must contain exactly the setup.cfg install_requires
    packages.

    No extra packages from the dev resolve should leak into the wheel.
    """
    wheel_path = _find_wheel()
    msg, _ = _read_metadata(wheel_path)

    all_requires_dist: List[str] = msg.get_all("Requires-Dist") or []
    full_block = "\n".join(f"  Requires-Dist: {r}" for r in all_requires_dist)

    main_requires = [
        r for r in all_requires_dist
        if "; extra ==" not in r
    ]

    expected_canon = {
        canonicalize_name(Requirement(r).name)
        for r in _EXPECTED_INSTALL_REQUIRES
    }
    actual_canon = {
        canonicalize_name(Requirement(r).name)
        for r in main_requires
    }

    assert actual_canon == expected_canon, (
        f"Unexpected packages in main Requires-Dist.\n"
        f"Expected: {sorted(expected_canon)}\n"
        f"Got:      {sorted(actual_canon)}\n"
        f"Extra:    {sorted(actual_canon - expected_canon)}\n"
        f"Missing:  {sorted(expected_canon - actual_canon)}\n"
        f"All Requires-Dist:\n{full_block}")


def test_wheel_extras_require() -> None:
    """The 'dev' extra must appear as Provides-Extra and Requires-Dist."""
    wheel_path = _find_wheel()
    msg, _ = _read_metadata(wheel_path)

    provides_extra: List[str] = msg.get_all("Provides-Extra") or []
    assert _EXPECTED_EXTRA in provides_extra, (
        f"Expected Provides-Extra: {_EXPECTED_EXTRA!r}, "
        f"got: {provides_extra}")

    all_requires_dist: List[str] = msg.get_all("Requires-Dist") or []
    dev_reqs = [
        r for r in all_requires_dist
        if f'extra == "{_EXPECTED_EXTRA}"' in r
        or f"extra == '{_EXPECTED_EXTRA}'" in r
    ]
    assert dev_reqs, (
        f"Expected at least one Requires-Dist for extra={_EXPECTED_EXTRA!r}, "
        f"found none.\n"
        f"All Requires-Dist: {all_requires_dist}")


def test_wheel_entry_points() -> None:
    """entry_points.txt must contain the expected console_scripts entry."""
    wheel_path = _find_wheel()
    _, all_names = _read_metadata(wheel_path)

    ep_names = [n for n in all_names if n.endswith("entry_points.txt")]
    assert ep_names, (
        f"No entry_points.txt found in {wheel_path.name}.\n"
        f"Files: {[n for n in all_names if '.dist-info/' in n]}")

    with zipfile.ZipFile(wheel_path) as zf:
        ep_text = zf.read(ep_names[0]).decode("utf-8")

    assert _EXPECTED_CONSOLE_SCRIPT in ep_text, (
        f"Expected console_script {_EXPECTED_CONSOLE_SCRIPT!r} in "
        f"entry_points.txt.\n"
        f"entry_points.txt content:\n{ep_text}")
