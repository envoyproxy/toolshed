"""Envoy-specific V8 patches for ABI compatibility.

These patches are copied from envoyproxy/envoy and applied during V8 builds
to ensure the prebuilt wee8 library matches Envoy's expectations.
"""

licenses(["notice"])  # Apache 2

exports_files([
    "v8.patch",
    "v8_no_python_load.patch",
    "v8_novtune.patch",
    "v8_ppc64le.patch",
    "v8_python.patch",
    "v8_module.patch",
])
