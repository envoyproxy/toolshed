
pytooling_library(
    "envoy.distribution.distrotest",
    dependencies=[
        ":data",
        "//deps:envoy.base.checker",
        "//deps:envoy.base.utils",
        "//deps:envoy.docker.utils",
    ],
)

resources(
    name="data",
    sources=[
        "distrotest.sh",
        "distrotest.yaml",
    ],
)
