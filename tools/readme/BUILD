python_sources(
    dependencies=[
        "//deps:jinja2",
        "//deps:packaging",
        "//deps:setuptools",
        "//deps:aio.run.runner",
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
