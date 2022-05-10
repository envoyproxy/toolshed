
pytooling_tests(
    "envoy.base.utils",
    dependencies=[
        ":data",
        "//deps:abstracts",
        "//deps:aio.core",
        "//deps:aio.run.runner",
        "//deps:pyyaml",
        "//deps:pytz",
        "//deps:trycast",
    ],
)

resources(
    name="data",
    sources=[
        "integration/**/*",
    ],
)
