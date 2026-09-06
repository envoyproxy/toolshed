load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//certs:certs.bzl", "generated_certs")
load(":certs_analysis_test.bzl", "command_test")

generated_certs(
    name = "generated",
    spec = "fixtures/certs.spec",
    srcs = glob(["fixtures/**"], exclude = ["fixtures/*.spec"]),
    outs = [
        "ca_cert_info.h",
        "ca_cert_hash.h",
        "ca_cert.pem",
        "chain.pem",
        "bundle.p12",
        "unencrypted.p12",
        "revoked.crl.pem",
        "statuses.der",
        "ec_status.der",
        "ocsp_info.h",
        "trust-bundle.json",
        "leaf_cert_info.h",
        "leaf_cert_hash.h",
        "expired.pem",
        "expired_cert_info.h",
        "long.pem",
        "long_cert_info.h",
        "v1.pem",
        "ec_responder.pem",
    ],
    year = 2030,
    testonly = True,
)

generated_certs(
    name = "serial_a",
    spec = "fixtures/serial.spec",
    srcs = glob(["fixtures/**"], exclude = ["fixtures/*.spec"]),
    outs = [
        "serial_ca.pem",
        "serial_leaf.pem",
    ],
    year = 2030,
    testonly = True,
)

generated_certs(
    name = "serial_b",
    spec = "fixtures/serial2.spec",
    srcs = glob(["fixtures/**"], exclude = ["fixtures/*.spec"]),
    outs = [
        "serial_ca_2.pem",
        "serial_leaf_2.pem",
    ],
    year = 2030,
    testonly = True,
)

generated_certs(
    name = "missing_output",
    spec = "fixtures/missing_output.spec",
    srcs = glob(["fixtures/**"], exclude = ["fixtures/*.spec"]),
    outs = ["not_created.pem"],
    year = 2030,
    testonly = True,
    tags = ["manual"],
)

generated_certs(
    name = "stamped",
    spec = "fixtures/serial.spec",
    srcs = glob(["fixtures/**"], exclude = ["fixtures/*.spec"]),
    outs = ["stamped_ca.pem", "stamped_leaf.pem"],
    tags = ["manual"],
)

generated_certs(
    name = "fallback",
    spec = "fixtures/serial.spec",
    srcs = glob(["fixtures/**"], exclude = ["fixtures/*.spec"]),
    outs = ["fallback_ca.pem", "fallback_leaf.pem"],
    fallback_to_host_year = True,
    tags = ["manual"],
)

generated_certs(
    name = "custom_status",
    spec = "fixtures/serial.spec",
    srcs = glob(["fixtures/**"], exclude = ["fixtures/*.spec"]),
    outs = ["custom_ca.pem", "custom_leaf.pem"],
    year_status_key = "CUSTOM_CERT_YEAR",
    tags = ["manual"],
)

sh_test(
    name = "certs_test",
    size = "small",
    srcs = ["certs_test.sh"],
    data = [
        ":generated",
        ":serial_a",
        ":serial_b",
        "fixtures/ca_key.pem",
        "@jq_toolchains//:resolved_toolchain",
    ],
    env = {"JQ_BIN": "$(JQ_BIN)"},
    toolchains = ["@jq_toolchains//:resolved_toolchain"],
)

sh_test(
    name = "failure_test",
    size = "small",
    srcs = ["failure_test.sh"],
    args = [
        "$(rootpath //certs:gen)",
        "$(rootpath fixtures/ca_key.pem)",
    ],
    data = [
        "//certs:gen",
    ] + glob(["fixtures/**"]),
)

command_test(
    name = "pinned_command_test",
    target_under_test = ":generated_gen",
    expected = '--year "2030"',
)

command_test(
    name = "output_validation_command_test",
    target_under_test = ":missing_output_gen",
    expected = "did not create declared output(s)",
)

command_test(
    name = "stamped_command_test",
    target_under_test = ":stamped_gen",
    expected = "STABLE_CERT_EPOCH_YEAR",
)

command_test(
    name = "fallback_command_test",
    target_under_test = ":fallback_gen",
    expected = "date -u +%Y",
)

command_test(
    name = "custom_status_command_test",
    target_under_test = ":custom_status_gen",
    expected = "CUSTOM_CERT_YEAR",
)
