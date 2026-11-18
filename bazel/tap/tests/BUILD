load("@com_google_protobuf//bazel:proto_library.bzl", "proto_library")
load("@com_google_protobuf//bazel:py_proto_library.bzl", "py_proto_library")
load("@rules_python//python:defs.bzl", "py_library", "py_test")
load("//tap:defs.bzl", "tap2pcap")

py_library(
    name = "pcap",
    srcs = ["pcap.py"],
    imports = ["."],
)

py_test(
    name = "tap2pcap_test",
    srcs = ["tap2pcap_test.py"],
    deps = [
        ":pcap",
        "//tap:tap2pcap",
    ],
)

# A proto with the fields of Envoy's trace wrapper that are read, as the Envoy API cannot be
# depended on from here.
proto_library(
    name = "trace_proto",
    srcs = ["trace.proto"],
    deps = ["@com_google_protobuf//:timestamp_proto"],
)

py_proto_library(
    name = "trace_py_proto",
    deps = [":trace_proto"],
)

tap2pcap(
    name = "tap2pcap",
    message = "tap.tests.trace_pb2.TraceWrapper",
    proto = ":trace_py_proto",
)

py_test(
    name = "tap2pcap_binary_test",
    srcs = ["tap2pcap_binary_test.py"],
    args = [
        "$(rootpath :tap2pcap)",
        "$(rootpath socket.pb_text)",
        "$(rootpath http.pb_text)",
    ],
    data = [
        "http.pb_text",
        "socket.pb_text",
        ":tap2pcap",
    ],
    deps = [
        ":pcap",
        ":trace_py_proto",
    ],
)
