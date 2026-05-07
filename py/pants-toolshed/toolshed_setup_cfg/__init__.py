"""Pure parsing functions for setup.cfg options.

This module contains no pants dependencies so it can be unit-tested
independently of the pants runtime.

Note: `packages`, `namespace_packages`, `package_dir` and `py_modules`
are intentionally NOT parsed here. Pants forbids setting `packages`,
`namespace_packages` and `package_dir` in `provides=setup_py(...)` and
computes them from the BUILD source graph. `py_modules` is redundant
given that. Any values for those keys in `setup.cfg` exist purely as
documentation/setuptools-compatibility and are ignored at build time.
"""

import configparser
import pathlib
from typing import Any, Dict, List, Optional


def parse_list(value: str) -> List[str]:
    """Parse a multi-line (or single-line) config value into a list."""
    return [item.strip() for item in value.strip().split("\n") if item.strip()]


def parse_metadata(
        config: configparser.ConfigParser,
        namespace: str) -> Dict[str, Any]:
    """Parse [metadata] section into setup() kwargs.

    Handles long_description file: directives and classifiers as a list.
    """
    kwargs: Dict[str, Any] = {}
    for option in config["metadata"]:
        value = config["metadata"][option]
        if option == "long_description":
            if value.startswith("file:"):
                filepath = value.split(":", 1)[1].strip()
                kwargs[option] = pathlib.Path(
                    f"{namespace}/{filepath}").read_text()
            else:
                kwargs[option] = value
        elif option == "classifiers":
            kwargs[option] = parse_list(value)
        else:
            kwargs[option] = value
    return kwargs


def parse_options(
        config: configparser.ConfigParser,
        namespace: str) -> Dict[str, Any]:
    """Parse [options] section into setup() kwargs.

    Handles python_requires, install_requires and zip_safe.

    `packages` and `py_modules` are intentionally ignored — pants computes
    these from the BUILD source graph and forbids setting them via
    `provides=setup_py(...)`.
    """
    kwargs: Dict[str, Any] = {}
    if not config.has_section("options"):
        return kwargs

    options = config["options"]

    if "python_requires" in options:
        kwargs["python_requires"] = options["python_requires"].strip()

    if "install_requires" in options:
        kwargs["install_requires"] = parse_list(options["install_requires"])

    if "zip_safe" in options:
        kwargs["zip_safe"] = options.getboolean("zip_safe")

    return kwargs


def parse_entry_points(
        config: configparser.ConfigParser) -> Optional[Dict[str, List[str]]]:
    """Parse [options.entry_points] into setup() entry_points dict."""
    if not config.has_section("options.entry_points"):
        return None
    entry_points: Dict[str, List[str]] = {}
    for entry_point in config["options.entry_points"]:
        entry_points[entry_point] = (
            config["options.entry_points"][entry_point]
            .strip().replace(" ", "").split("\n"))
    return entry_points


def parse_extras_require(
        config: configparser.ConfigParser) -> Optional[Dict[str, List[str]]]:
    """Parse [options.extras_require] into setup() extras_require dict."""
    if not config.has_section("options.extras_require"):
        return None
    extras: Dict[str, List[str]] = {}
    for extra in config["options.extras_require"]:
        extras[extra] = parse_list(config["options.extras_require"][extra])
    return extras


def parse_package_data(
        config: configparser.ConfigParser) -> Optional[Dict[str, List[str]]]:
    """Parse [options.package_data] into setup() package_data dict.

    Values may be comma- or newline-separated.
    """
    if not config.has_section("options.package_data"):
        return None
    package_data: Dict[str, List[str]] = {}
    for pkg in config["options.package_data"]:
        raw = config["options.package_data"][pkg].strip()
        items = [
            item.strip()
            for item in raw.replace(",", "\n").split("\n")
            if item.strip()]
        package_data[pkg] = items
    return package_data
