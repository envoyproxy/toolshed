"""Pure parsing functions for setup.cfg options.

This module contains no pants dependencies so it can be unit-tested
independently of the pants runtime.
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


def _parse_packages_find(
        config: configparser.ConfigParser) -> Dict[str, List[str]]:
    """Parse [options.packages.find] into kwargs for find_packages()."""
    find_kwargs: Dict[str, List[str]] = {}
    if config.has_section("options.packages.find"):
        section = config["options.packages.find"]
        if "include" in section:
            find_kwargs["include"] = parse_list(section["include"])
        if "exclude" in section:
            find_kwargs["exclude"] = parse_list(section["exclude"])
    return find_kwargs


def parse_options(
        config: configparser.ConfigParser,
        namespace: str) -> Dict[str, Any]:
    """Parse [options] section into setup() kwargs.

    Handles packages (including find: / find_namespace: resolution),
    py_modules, python_requires, install_requires, and zip_safe.
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

    if "py_modules" in options:
        kwargs["py_modules"] = parse_list(options["py_modules"])

    if "packages" in options:
        packages_val = options["packages"].strip()
        if packages_val in ("find:", "find_namespace:"):
            find_kwargs = _parse_packages_find(config)
            if packages_val == "find:":
                from setuptools import find_packages
                kwargs["packages"] = find_packages(
                    where=namespace, **find_kwargs)
            else:
                from setuptools import find_namespace_packages
                kwargs["packages"] = find_namespace_packages(
                    where=namespace, **find_kwargs)
        else:
            kwargs["packages"] = parse_list(packages_val)

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
