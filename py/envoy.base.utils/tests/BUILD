
toolshed_tests(
    "envoy.base.utils",
    dependencies=[
        ":data",
        "//py/deps:reqs#abstracts",
        "//py/deps:reqs#aio-api-github",
        "//py/deps:reqs#aio-core",
        "//py/deps:reqs#aio-run-runner",
        "//py/deps:reqs#aiohttp",
        "//py/deps:reqs#frozendict",
        "//py/deps:reqs#jinja2",
        "//py/deps:reqs#orjson",
        "//py/deps:reqs#packaging",
        "//py/deps:reqs#protobuf",
        "//py/deps:reqs#python-gnupg",
        "//py/deps:reqs#pyyaml",
        "//py/deps:reqs#trycast",
        "//py/deps:reqs#zstandard",
    ],
)

resources(
    name="data",
    sources=[
        "integration/**/*",
    ],
)
