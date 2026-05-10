
resources(
    name="package_data",
    sources=["py.typed"])

python_sources(
    dependencies=[
        ":data",
        ":package_data",
        "//py/deps:reqs#aio-run-checker",
        "//py/deps:reqs#envoy-base-utils",
        "//py/deps:reqs#envoy-docker-utils",
    ],
)

resources(
    name="data",
    sources=[
        "distrotest.sh",
        "distrotest.yaml",
    ],
)
