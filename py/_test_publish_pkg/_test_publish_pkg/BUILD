# Inner module BUILD for the _test_publish_pkg test fixture.
#
# The dev_deps target groups the pinned dependencies used for development
# and testing.  The toolshed_distribution in the outer BUILD depends on
# "!_inner:dev_deps" so these pinned versions are excluded from the wheel's
# Requires-Dist. Loose ranges from setup.cfg install_requires are included
# instead via synthetic publish requirement targets.

target(
    name="dev_deps",
    dependencies=[
        "//py/deps:reqs#aiohttp",
        "//py/deps:reqs#packaging",
        "//py/deps:reqs#pyyaml",
    ],
)

toolshed_library(
    "_test_publish_pkg",
    dependencies=[":dev_deps"],
)
