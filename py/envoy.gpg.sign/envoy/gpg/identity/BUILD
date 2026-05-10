
resources(
    name="package_data",
    sources=["py.typed"],
)

python_sources(
    name="envoy.gpg.identity",
    dependencies=[
        ":package_data",
        "//py/deps:reqs#aio-core",
        "//py/deps:reqs#python-gnupg",
    ],
)
