"""Module extension for the generated certificate epoch."""

load("//certs:epoch.bzl", "cert_epoch_repo")

def _cert_epoch_extension_impl(module_ctx):
    cert_epoch_repo(name = "cert_epoch")

    # The repo definition never varies, which is all `reproducible` claims here (it keeps the
    # extension out of lockfiles). The year itself is read when the repo is fetched, and the
    # repo rule is not reproducible, so its contents are never cached across fetches.
    return module_ctx.extension_metadata(reproducible = True)

cert_epoch_extension = module_extension(
    implementation = _cert_epoch_extension_impl,
    doc = "Provides `@cert_epoch//:year`, the epoch year used by `generated_certs`.",
)
