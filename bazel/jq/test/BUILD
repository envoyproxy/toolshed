load("@bazel_skylib//rules:diff_test.bzl", "diff_test")
load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//jq:defs.bzl", "jq_binary", "jq_library", "jq_test")
load(":analysis_test.bzl", "collision_source", "execution_constraints_test", "failure_test", "provider_test")

constraint_setting(name = "test_execution")

constraint_value(
    name = "execution_constraint",
    constraint_setting = ":test_execution",
)

execution_constraints_test(name = "execution_constraints_test")

jq_library(
    name = "str",
    srcs = ["str.jq"],
)

jq_library(
    name = "greet",
    srcs = ["greet.jq"],
    deps = [":str"],
)

jq_library(
    name = "remapped",
    srcs = [
        "modules/feature.jq",
        "modules/helper.jq",
    ],
    import_prefix = "renamed",
    strip_import_prefix = "modules",
)

jq_library(
    name = "absolute_prefix",
    srcs = ["modules/helper.jq"],
    import_prefix = "absolute",
    strip_import_prefix = "/jq/test/modules",
)

jq_library(
    name = "json_module",
    srcs = ["config.json"],
)

genrule(
    name = "generate_module",
    outs = ["generated.jq"],
    cmd = "printf 'def answer: 42;\\n' > $@",
)

jq_library(
    name = "generated",
    srcs = [":generate_module"],
)

jq_library(
    name = "override",
    srcs = ["overrides/str.jq"],
    strip_import_prefix = "overrides",
    deps = [":str"],
)

jq_library(
    name = "diamond",
    deps = [
        ":greet",
        ":override",
    ],
)

provider_test(
    name = "library_provider_test",
    roots = [
        "greet.modules",
        "str.modules",
    ],
    sources = [
        "greet.jq",
        "str.jq",
    ],
    target_under_test = ":greet",
)

provider_test(
    name = "diamond_order_test",
    roots = [
        "diamond.modules",
        "greet.modules",
        "str.modules",
        "override.modules",
    ],
    sources = [
        "greet.jq",
        "str.jq",
        "str.jq",
    ],
    target_under_test = ":diamond",
)

jq_binary(
    name = "notice",
    jq_args = ["-n"],
    main = "notice.jq",
    # Do not sort: jq module search order is significant.
    deps = [
        ":greet",
        ":remapped",
        ":json_module",
        ":generated",
        ":absolute_prefix",
    ],
)

provider_test(
    name = "binary_provider_test",
    roots = [
        "greet.modules",
        "str.modules",
        "remapped.modules",
        "json_module.modules",
        "generated.modules",
        "absolute_prefix.modules",
    ],
    sources = [
        "config.json",
        "feature.jq",
        "generated.jq",
        "greet.jq",
        "helper.jq",
        "str.jq",
    ],
    target_under_test = ":notice",
)

genrule(
    name = "notice_output",
    outs = ["notice.json"],
    cmd = "$(execpath :notice) > $@",
    tools = [":notice"],
)

diff_test(
    name = "genrule_tool_test",
    file1 = ":notice_output",
    file2 = "notice.expected.json",
)

jq_binary(
    name = "smoke",
    filter = "{name: .name, config: $config[0].value}",
    jq_args = ["-c"],
    named_srcs = {"config": "config.json"},
)

sh_test(
    name = "binary_smoke_test",
    srcs = ["binary_smoke.sh"],
    args = [
        "$(rlocationpath :smoke)",
        "$(rlocationpath input.json)",
        "$(rlocationpath smoke.expected.json)",
    ],
    data = [
        "input.json",
        "smoke.expected.json",
        ":smoke",
        "@bazel_tools//tools/bash/runfiles",
    ],
)

jq_binary(
    name = "false_binary",
    filter = "false",
)

sh_test(
    name = "false_assertion_test",
    srcs = ["negative.sh"],
    args = ["$(rlocationpath :false_binary)"],
    data = [
        ":false_binary",
        "@bazel_tools//tools/bash/runfiles",
    ],
)

jq_test(
    name = "assertion_test",
    filter = 'import "greet" as greet; (" world " | greet::hello) == "Hello world"',
    deps = [":greet"],
)

jq_test(
    name = "named_comparison_test",
    filter = '$a[0] == $b[0] or error("drift")',
    named_srcs = {
        "a": "input.json",
        "b": "input.reordered.json",
    },
)

jq_test(
    name = "shared_named_source_test",
    filter = "$a == $b",
    named_srcs = {
        "a": "input.json",
        "b": "input.json",
    },
)

jq_test(
    name = "positional_assertion_test",
    srcs = ["input.json"],
    filter = '.name == "world"',
)

jq_test(
    name = "standard_args_test",
    args = ["$(rootpath input.json)"],
    data = ["input.json"],
    env = {"JQ_TEST_VALUE": "world"},
    filter = ".name == env.JQ_TEST_VALUE",
    jq_args = ["-c"],
)

jq_test(
    name = "standard_args_golden_test",
    args = ["$(rootpath input.json)"],
    data = ["input.json"],
    expected = "raw.expected",
    filter = ".name",
    jq_args = ["-r"],
    raw = True,
)

provider_test(
    name = "generated_provider_test",
    roots = ["generated.modules"],
    sources = ["generated.jq"],
    target_under_test = ":generated",
)

jq_test(
    name = "golden_test",
    srcs = ["input.json"],
    expected = "input.reordered.json",
    filter = ".",
)

jq_test(
    name = "raw_golden_test",
    srcs = ["input.json"],
    expected = "raw.expected",
    filter = ".name",
    jq_args = ["-r"],
    raw = True,
)

jq_test(
    name = "golden_null_input_test",
    expected = "answer.json",
    filter = "{answer: 42}",
)

jq_test(
    name = "cases_test",
    cases = "str.test",
    deps = [":str"],
)

jq_test(
    name = "direct_root_wins_test",
    filter = 'import "str" as str; (null | str::trim) == "override"',
    deps = [":override"],
)

jq_binary(
    name = "both",
    filter = ".",
    main = "notice.jq",
    tags = ["manual"],
)

jq_binary(
    name = "neither",
    tags = ["manual"],
)

failure_test(
    name = "both_rejected_test",
    message = "exactly one of main or filter",
    target_under_test = ":both",
)

failure_test(
    name = "neither_rejected_test",
    message = "exactly one of main or filter",
    target_under_test = ":neither",
)

collision_source(
    name = "collision_source",
    tags = ["manual"],
)

jq_library(
    name = "collision",
    srcs = [
        "str.jq",
        ":collision_source",
    ],
    tags = ["manual"],
)

failure_test(
    name = "collision_rejected_test",
    message = "import-path collision",
    target_under_test = ":collision",
)

jq_library(
    name = "marker_collision",
    srcs = ["str.jq"],
    import_prefix = ".jq_root",
    tags = ["manual"],
)

failure_test(
    name = "marker_collision_rejected_test",
    message = "reserved marker name",
    target_under_test = ":marker_collision",
)
