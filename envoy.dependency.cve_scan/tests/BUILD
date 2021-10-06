
pytooling_tests(
    "envoy.dependency.cve_scan",
    dependencies=[
        "//deps:abstracts",
        "//deps:pytest-asyncio",
        ":data",
    ],
)

resources(
    name="data",
    sources=[
        "**/*.json",
        "**/*.yaml",
    ],
)
