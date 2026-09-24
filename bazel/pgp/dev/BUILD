load("//pgp:defs.bzl", "pgp_toolchain", "sq_signer")

sq_signer(
    name = "sq_signer",
    sq = "@sq//:sq_from_source",
    visibility = ["//visibility:public"],
)

pgp_toolchain(
    name = "sq_signer_toolchain",
    signer = ":sq_signer",
)

toolchain(
    name = "sq_toolchain",
    toolchain = ":sq_signer_toolchain",
    toolchain_type = "//pgp:toolchain_type",
    visibility = ["//visibility:public"],
)
