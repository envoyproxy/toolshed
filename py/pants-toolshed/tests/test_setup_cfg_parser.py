"""Unit tests for toolshed_setup_cfg (setup.cfg parsing)."""

import configparser
import textwrap

import pytest

from toolshed_setup_cfg import (
    parse_entry_points,
    parse_extras_require,
    parse_list,
    parse_metadata,
    parse_options,
    parse_package_data,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(ini_text: str) -> configparser.ConfigParser:
    """Return a ConfigParser pre-loaded with *ini_text*."""
    config = configparser.ConfigParser()
    config.read_string(textwrap.dedent(ini_text))
    return config


# ---------------------------------------------------------------------------
# parse_list
# ---------------------------------------------------------------------------

def test_parse_list_single_line():
    assert parse_list("foo") == ["foo"]


def test_parse_list_multi_line():
    value = "\n    foo\n    bar\n    baz\n"
    assert parse_list(value) == ["foo", "bar", "baz"]


def test_parse_list_empty_lines_stripped():
    value = "\n    foo\n\n    bar\n"
    assert parse_list(value) == ["foo", "bar"]


def test_parse_list_blank_value():
    assert parse_list("") == []


# ---------------------------------------------------------------------------
# parse_metadata
# ---------------------------------------------------------------------------

@pytest.fixture
def metadata_config():
    return make_config("""
        [metadata]
        name = my-pkg
        description = A cool package
        author = Ryan
        long_description = file: README.rst
        classifiers =
            Development Status :: 4 - Beta
            Programming Language :: Python :: 3
    """)


def test_parse_metadata_basic_fields(metadata_config, tmp_path):
    readme = tmp_path / "README.rst"
    readme.write_text("My readme")
    kwargs = parse_metadata(metadata_config, str(tmp_path))
    assert kwargs["name"] == "my-pkg"
    assert kwargs["description"] == "A cool package"
    assert kwargs["author"] == "Ryan"


def test_parse_metadata_long_description_from_file(metadata_config, tmp_path):
    readme = tmp_path / "README.rst"
    readme.write_text("Long description content")
    kwargs = parse_metadata(metadata_config, str(tmp_path))
    assert kwargs["long_description"] == "Long description content"


def test_parse_metadata_classifiers_as_list(metadata_config, tmp_path):
    (tmp_path / "README.rst").write_text("")
    kwargs = parse_metadata(metadata_config, str(tmp_path))
    assert kwargs["classifiers"] == [
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
    ]


def test_parse_metadata_long_description_inline():
    config = make_config("""
        [metadata]
        long_description = Just inline text
    """)
    kwargs = parse_metadata(config, "/irrelevant")
    assert kwargs["long_description"] == "Just inline text"


def test_parse_metadata_no_classifiers():
    config = make_config("""
        [metadata]
        name = simple
    """)
    kwargs = parse_metadata(config, "/irrelevant")
    assert "classifiers" not in kwargs


# ---------------------------------------------------------------------------
# parse_options – python_requires
# ---------------------------------------------------------------------------

def test_parse_options_python_requires():
    config = make_config("""
        [options]
        python_requires = >=3.12
    """)
    assert parse_options(config, "/x")["python_requires"] == ">=3.12"


def test_parse_options_python_requires_absent():
    config = make_config("""
        [options]
        zip_safe = false
    """)
    assert "python_requires" not in parse_options(config, "/x")


# ---------------------------------------------------------------------------
# parse_options – install_requires
# ---------------------------------------------------------------------------

def test_parse_options_install_requires_single():
    config = make_config("""
        [options]
        install_requires = mypy
    """)
    assert parse_options(config, "/x")["install_requires"] == ["mypy"]


def test_parse_options_install_requires_multi():
    config = make_config("""
        [options]
        install_requires =
            mypy
            abstracts>=0.0.12
            aio.core>=0.10.5
    """)
    assert parse_options(config, "/x")["install_requires"] == [
        "mypy",
        "abstracts>=0.0.12",
        "aio.core>=0.10.5",
    ]


def test_parse_options_install_requires_absent():
    config = make_config("""
        [options]
        python_requires = >=3.12
    """)
    assert "install_requires" not in parse_options(config, "/x")


# ---------------------------------------------------------------------------
# parse_options – zip_safe
# ---------------------------------------------------------------------------

def test_parse_options_zip_safe_false():
    config = make_config("""
        [options]
        zip_safe = false
    """)
    result = parse_options(config, "/x")
    assert result["zip_safe"] is False


def test_parse_options_zip_safe_true():
    config = make_config("""
        [options]
        zip_safe = true
    """)
    assert parse_options(config, "/x")["zip_safe"] is True


# ---------------------------------------------------------------------------
# parse_options – packages / py_modules are intentionally ignored
# (pants forbids setting these in setup_py(...) and computes them itself)
# ---------------------------------------------------------------------------

def test_parse_options_packages_ignored():
    config = make_config("""
        [options]
        packages = find:

        [options.packages.find]
        include =
            mypkg
            mypkg.*
    """)
    result = parse_options(config, "/x")
    assert "packages" not in result
    assert "namespace_packages" not in result
    assert "package_dir" not in result


def test_parse_options_py_modules_ignored():
    config = make_config("""
        [options]
        py_modules = my_module
    """)
    assert "py_modules" not in parse_options(config, "/x")


def test_parse_options_explicit_packages_ignored():
    config = make_config("""
        [options]
        packages =
            mypkg
            mypkg.subpkg
    """)
    assert "packages" not in parse_options(config, "/x")


# ---------------------------------------------------------------------------
# parse_entry_points
# ---------------------------------------------------------------------------

def test_parse_entry_points_present():
    config = make_config("""
        [options.entry_points]
        pytest11 =
            iters = pytest_iters
    """)
    result = parse_entry_points(config)
    assert result is not None
    assert "iters=pytest_iters" in result["pytest11"]


def test_parse_entry_points_absent():
    config = make_config("[metadata]\nname=x\n")
    assert parse_entry_points(config) is None


def test_parse_entry_points_multiple_groups():
    config = make_config("""
        [options.entry_points]
        console_scripts =
            my-tool = my_pkg:main
        pytest11 =
            plugin = my_pkg.plugin
    """)
    result = parse_entry_points(config)
    assert result is not None
    assert "console_scripts" in result
    assert "pytest11" in result


# ---------------------------------------------------------------------------
# parse_extras_require
# ---------------------------------------------------------------------------

def test_parse_extras_require():
    config = make_config("""
        [options.extras_require]
        test =
            pytest
            pytest-coverage
        lint = flake8
    """)
    result = parse_extras_require(config)
    assert result is not None
    assert result["test"] == ["pytest", "pytest-coverage"]
    assert result["lint"] == ["flake8"]


def test_parse_extras_require_absent():
    config = make_config("[metadata]\nname=x\n")
    assert parse_extras_require(config) is None


def test_parse_extras_require_single_item():
    config = make_config("""
        [options.extras_require]
        types = mypy
    """)
    result = parse_extras_require(config)
    assert result is not None
    assert result["types"] == ["mypy"]


# ---------------------------------------------------------------------------
# parse_package_data
# ---------------------------------------------------------------------------

def test_parse_package_data_newline_separated():
    config = make_config("""
        [options.package_data]
        mypackage =
            py.typed
            data/*.json
    """)
    result = parse_package_data(config)
    assert result is not None
    assert result["mypackage"] == ["py.typed", "data/*.json"]


def test_parse_package_data_comma_separated():
    config = make_config("""
        [options.package_data]
        mypackage = py.typed, data/*.json
    """)
    result = parse_package_data(config)
    assert result is not None
    assert result["mypackage"] == ["py.typed", "data/*.json"]


def test_parse_package_data_single_file():
    config = make_config("""
        [options.package_data]
        abstracts = py.typed
    """)
    result = parse_package_data(config)
    assert result is not None
    assert result["abstracts"] == ["py.typed"]


def test_parse_package_data_multiple_packages():
    config = make_config("""
        [options.package_data]
        pkg_a = py.typed
        pkg_b = data.json
    """)
    result = parse_package_data(config)
    assert result is not None
    assert "pkg_a" in result
    assert "pkg_b" in result


def test_parse_package_data_absent():
    config = make_config("[metadata]\nname=x\n")
    assert parse_package_data(config) is None


# ---------------------------------------------------------------------------
# parse_options – no [options] section
# ---------------------------------------------------------------------------

def test_parse_options_no_section():
    config = make_config("[metadata]\nname=x\n")
    assert parse_options(config, "/x") == {}


# ---------------------------------------------------------------------------
# Integration: full setup.cfg like abstracts
# ---------------------------------------------------------------------------

def test_full_abstracts_config(tmp_path):
    """Simulate the abstracts setup.cfg being parsed end-to-end."""
    (tmp_path / "README.rst").write_text("Abstracts readme")

    config = make_config("""
        [metadata]
        name = abstracts
        version = file: VERSION
        description = Abstract class and interface definitions
        long_description = file: README.rst
        classifiers =
            Development Status :: 4 - Beta
            Programming Language :: Python :: 3.12

        [options]
        python_requires = >=3.12
        packages = find:

        [options.extras_require]
        test =
            pytest
            pytest-coverage
        lint = flake8

        [options.package_data]
        abstracts = py.typed

        [options.packages.find]
        include =
            abstracts
            abstracts.*
        exclude =
            build.*
            tests.*
    """)

    metadata_kwargs = parse_metadata(config, str(tmp_path))
    assert metadata_kwargs["name"] == "abstracts"
    assert metadata_kwargs["long_description"] == "Abstracts readme"
    assert "Development Status :: 4 - Beta" in metadata_kwargs["classifiers"]

    options_kwargs = parse_options(config, str(tmp_path))
    assert options_kwargs["python_requires"] == ">=3.12"
    # packages must NOT be set — pants computes it.
    assert "packages" not in options_kwargs

    extras = parse_extras_require(config)
    assert extras is not None
    assert extras["lint"] == ["flake8"]
    assert "pytest" in extras["test"]

    pkg_data = parse_package_data(config)
    assert pkg_data is not None
    assert pkg_data["abstracts"] == ["py.typed"]


def test_full_mypy_abstracts_config():
    """Simulate the mypy-abstracts setup.cfg being parsed end-to-end."""
    config = make_config("""
        [metadata]
        name = mypy-abstracts
        description = Mypy plugin for abstracts lib
        classifiers =
            Development Status :: 4 - Beta
            Intended Audience :: Developers

        [options]
        python_requires = >=3.12
        install_requires = mypy

        [options.extras_require]
        test =
            pytest
            pytest-coverage
        types = mypy
    """)

    metadata_kwargs = parse_metadata(config, "/irrelevant")
    assert metadata_kwargs["name"] == "mypy-abstracts"
    assert "Development Status :: 4 - Beta" in metadata_kwargs["classifiers"]

    options_kwargs = parse_options(config, "/irrelevant")
    # install_requires from setup.cfg should be ["mypy"] not a pinned version.
    # This is the key override that prevents requirements.in's mypy==1.20.0
    # from leaking into the published wheel.
    assert options_kwargs["install_requires"] == ["mypy"]
    assert options_kwargs["python_requires"] == ">=3.12"

    extras = parse_extras_require(config)
    assert extras is not None
    assert extras["types"] == ["mypy"]
