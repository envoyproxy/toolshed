licenses(["notice"])  # Apache 2

package(default_visibility = ["//visibility:public"])

# Worker container image used by EngFlow RBE.
#
# This is the multi-arch worker image produced by this repo (see
# `docker/build/` and `.github/docker-manifests.yml`).
#
# TODO: pin to `@sha256:<digest>` once the v0.1.3 release is stable.
WORKER_IMAGE = "docker://gcr.io/envoy-ci/envoy-build:worker-v0.1.8@sha256:934b50777b1eb9348b0e62cafd9eee5c79828e57d4ca08083c86d3099b14bb42"

# GCC worker container image used by EngFlow RBE for gcc builds.
#
# Image produced by this repo at release docker-v0.1.3.
# GCC is now hermetic: GCC_WORKER_IMAGE and //compile:gcc_worker are no longer
# required for correctness and can be collapsed into the general worker later.
# Both GCC 13.4.0 archives are x86_64-hosted; aarch64 targets cross-compile on
# linux_x64_gcc rather than the arm64 RBE pool. Native sibling releases omit GCC 13.
GCC_WORKER_IMAGE = "docker://gcr.io/envoy-ci/envoy-build:gcc-v0.1.8@sha256:342d7eaccb753e8efb2aa171dccfd3bd7e531a22730ecb72372ab64c5967681b"

platform(
    name = "linux_x64",
    constraint_values = [
        "@platforms//os:linux",
        "@platforms//cpu:x86_64",
        "//compile:llvm_worker",
    ],
    exec_properties = {
        "container-image": WORKER_IMAGE,
        "OSFamily": "Linux",
    },
)

platform(
    name = "linux_arm64",
    constraint_values = [
        "@platforms//os:linux",
        "@platforms//cpu:aarch64",
        "//compile:llvm_worker",
    ],
    exec_properties = {
        "container-image": WORKER_IMAGE,
        "OSFamily": "Linux",
        "Pool": "arm",
    },
)

platform(
    name = "linux_x64_gcc",
    constraint_values = [
        "@platforms//os:linux",
        "@platforms//cpu:x86_64",
        "//compile:gcc_worker",
    ],
    exec_properties = {
        "container-image": GCC_WORKER_IMAGE,
        "OSFamily": "Linux",
    },
)
