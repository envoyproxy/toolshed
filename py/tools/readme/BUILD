python_sources(
    dependencies=[
        "//py/deps:reqs#jinja2",
        "//py/deps:reqs#packaging",
        "//py/deps:reqs#setuptools",
        "//py/deps:reqs#aio-run-runner",
    ],
)

pex_binary(
    name="summarize",
    dependencies=[
        "./summarize.py",
    ],
    entry_point="readme.summarize",
)

pex_binary(
    name="header",
    dependencies=[
        "./header.py",
    ],
    entry_point="readme.header",
)
