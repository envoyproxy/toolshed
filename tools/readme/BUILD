python_sources(
    dependencies=[
        "//deps:reqs#jinja2",
        "//deps:reqs#packaging",
        "//deps:reqs#setuptools",
        "//deps:reqs#aio.run.runner",
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
