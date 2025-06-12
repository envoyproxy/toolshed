# Autotools Toolchain for Bazel

This provides a hermetic autotools toolchain (m4, autoconf, automake, libtool) for use with foreign_cc rules.

## Usage

```python
load("@envoy_toolshed//toolchains/autotools:configure_make_autotools.bzl", "configure_make_with_autotools")

configure_make_with_autotools(
    name = "colm",
    autogen = True,
    configure_in_place = True,
    configure_options = [
        "--disable-shared",
        "--enable-static",
    ],
    env = {
        "CXXFLAGS": "--static -lstdc++ -Wno-unused-command-line-argument",
    },
    lib_source = "@net_colm_open_source_colm//:all",
    out_binaries = ["colm"],
    tags = ["skip_on_windows"],
)
```

## Setup

In your WORKSPACE:

```python
load("@envoy_toolshed//bazel/compile:autotools.bzl", "setup_autotools")
setup_autotools()

load("@envoy_toolshed//bazel/toolchains:register.bzl", "toolshed_toolchains")
toolshed_toolchains()
```

## How it works

The autotools toolchain:
1. Downloads prebuilt m4, autoconf, automake, and libtool binaries for your platform
2. Makes them available to foreign_cc rules via `additional_tools`
3. Sets up the necessary environment variables and paths
4. Ensures all m4 macros are available via ACLOCAL_PATH

## Components included

- **m4**: GNU macro processor required by autoconf
- **autoconf**: Generates configure scripts from configure.ac
- **automake**: Generates Makefile.in from Makefile.am
- **libtool**: Manages creation of static and shared libraries

All components work together seamlessly with proper path configuration.
