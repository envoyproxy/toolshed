load("@rules_shell//shell:sh_test.bzl", "sh_test")

sh_test(
    name = "check_reports_test",
    size = "small",
    srcs = ["check_reports_test.sh"],
    data = ["//format/clang_tidy:check_reports"],
    env = {"CHECKER": "$(rootpath //format/clang_tidy:check_reports)"},
)
