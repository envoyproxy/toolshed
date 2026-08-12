load(":wee8_package.bzl", "wee8_package")

licenses(["notice"])

# Per-arch packaging targets — tagged manual so they are not built by //...
# and are only triggered explicitly by the package-v8 CI job:
#   bazel build -c opt //v8:wee8_package_linux_x86_64   (ubuntu-24.04)
#   bazel build -c opt //v8:wee8_package_linux_aarch64  (ubuntu-24.04-arm)
[
    wee8_package(arch = arch)
    for arch in ["x86_64", "aarch64"]
]
