licenses(["notice"])  # Apache 2

package(default_visibility = ["//visibility:public"])

# Worker container image used by EngFlow RBE.
#
# This is the multi-arch worker image produced by this repo (see
# `docker/build/` and `.github/docker-manifests.yml`).
#
# TODO: pin to `@sha256:<digest>` once the v0.1.3 release is stable.
WORKER_IMAGE = "docker://gcr.io/envoy-ci/envoy-build:worker-v0.1.3@sha256:482b9906428e68a65101a1b27abf81f69dfd1b4377f66283866110bfd8127ea3"

# GCC worker container image used by EngFlow RBE for gcc builds.
#
# Image produced by this repo at release docker-v0.1.3.
GCC_WORKER_IMAGE = "docker://gcr.io/envoy-ci/envoy-build:gcc-v0.1.3@sha256:2a12bbcd5e95bc037bae5dfb2eb6361e55faf737098cbf90b4378e2345d9eecf"

platform(
    name = "linux_x64",
    constraint_values = [
        "@platforms//os:linux",
        "@platforms//cpu:x86_64",
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
    ],
    exec_properties = {
        "container-image": GCC_WORKER_IMAGE,
        "OSFamily": "Linux",
    },
)

platform(
    name = "linux_arm64_gcc",
    constraint_values = [
        "@platforms//os:linux",
        "@platforms//cpu:aarch64",
    ],
    exec_properties = {
        "container-image": GCC_WORKER_IMAGE,
        "OSFamily": "Linux",
        "Pool": "arm",
    },
)
