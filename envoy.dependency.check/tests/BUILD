
pytooling_tests(
    "envoy.dependency.check",
    dependencies=[
        "//deps:abstracts",
        "//deps:aio.api.github",
        "//deps:aio.core",
        # TODO: revert once aio.run.checker 0.3.0 is released
        # "//deps:aio.run.checker",
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
