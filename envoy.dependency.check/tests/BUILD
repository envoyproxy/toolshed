
pytooling_tests(
    "envoy.dependency.check",
    dependencies=[
        "//deps:abstracts",
        "//deps:aio.api.github",
        "//deps:aio.core",
        "//deps:aio.run.checker",
        "//aio.run.checker/aio/run/checker/__init__.py",
        "//deps:envoy.base.utils",
        "//deps:aiohttp",
        "//deps:packaging",
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
