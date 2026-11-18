"""Tools for Envoy's tap traces."""

load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@rules_python//python:defs.bzl", "py_binary")

def tap2pcap(name, proto, message, **kwargs):
    """A binary that converts an Envoy socket tap trace to PCAP.

    The trace is read as `message`, a `TraceWrapper` (`envoy.data.tap.v3`), so the proto comes from
    the caller and not from this module. One TCP segment is synthesized for each read or write of
    a socket buffered trace, with nothing but Python: no Wireshark (`text2pcap`) is needed.

    Example:

    ```starlark
    tap2pcap(
        name = "tap2pcap",
        message = "envoy.data.tap.v3.wrapper_pb2.TraceWrapper",
        proto = "//envoy/data/tap/v3:pkg_py_proto",
    )
    ```

    ```console
    $ bazel run //tools:tap2pcap /some/tap/path_0.pb path_0.pcap
    ```

    Args:
        name: Name of the binary.
        proto: A `py_proto_library` (or other Python target) that provides `message`.
        message: The trace wrapper message class, as `<python module>.<class>`.
        **kwargs: Passed to the `py_binary`.
    """
    module, _, cls = message.rpartition(".")
    if not module:
        fail("`message` must be `<python module>.<class>`: %s" % message)
    main = "%s_main.py" % name
    write_file(
        name = "%s_main" % name,
        out = main,
        content = [
            "import sys",
            "",
            "from %s import %s" % (module, cls),
            "",
            "import tap2pcap",
            "",
            "if __name__ == \"__main__\":",
            "    sys.exit(tap2pcap.main(%s))" % cls,
            "",
        ],
    )
    py_binary(
        name = name,
        srcs = [main],
        main = main,
        deps = [
            Label("//tap:tap2pcap"),
            proto,
        ],
        **kwargs
    )
