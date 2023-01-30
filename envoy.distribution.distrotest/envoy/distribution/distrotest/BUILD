
pytooling_library(
    "envoy.distribution.distrotest",
    dependencies=[
        ":data",
        "//deps:reqs#aio.run.checker",
        "//deps:reqs#envoy.base.utils",
        "//deps:reqs#envoy.docker.utils",
    ],
)

resources(
    name="data",
    sources=[
        "distrotest.sh",
        "distrotest.yaml",
    ],
)
