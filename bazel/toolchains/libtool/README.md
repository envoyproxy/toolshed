# Example usage of libtool toolchain with configure_make

To use the libtool toolchain in your configure_make rules:

## 1. In your WORKSPACE:

```python
load("@envoy_toolshed//bazel:deps.bzl", "resolve_dependencies")
resolve_dependencies()

load("@envoy_toolshed//bazel:toolchains.bzl", "load_toolchains")
load_toolchains()
```

## 2. In your BUILD file:

```python
load("@rules_foreign_cc//foreign_cc:defs.bzl", "configure_make")

configure_make(
    name = "colm",
    lib_source = "@colm//:all",
    autogen = True,
    configure_in_place = True,
    # Add the libtool toolchain type
    toolchains = [
        "@envoy_toolshed//toolchains/libtool:libtool_toolchain_type",
    ],
)
```

The libtool toolchain will automatically:
- Provide libtoolize and libtool binaries
- Set ACLOCAL_PATH to find libtool's m4 macros
- Include all necessary support files

## 3. To access libtool data in a custom rule:

```python
load("@envoy_toolshed//toolchains/libtool:libtool_toolchain.bzl", "get_libtool_data")

def _my_rule_impl(ctx):
    libtool = get_libtool_data(ctx)
    # libtool.libtoolize - path to libtoolize
    # libtool.env - environment variables to set
    # libtool.data - data files
```
