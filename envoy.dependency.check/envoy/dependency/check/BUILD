
pytooling_library(
    "envoy.dependency.check",
    dependencies=[
        "//deps:abstracts",
        "//deps:aio.api.github",
        "//deps:aio.core",
        # TODO: revert once aio.run.checker 0.3.0 is released
        # "//deps:aio.run.checker",
        "//aio.run.checker/aio/run/checker/__init__.py",
        "//deps:envoy.base.utils",
        "//deps:jinja2",
        "//deps:aiohttp",
        "//deps:packaging",
    ],
    sources=[
        "abstract/__init__.py",
        "abstract/checker.py",
        "abstract/cves/__init__.py",
        "abstract/cves/cpe.py",
        "abstract/cves/cve.py",
        "abstract/cves/cves.py",
        "abstract/cves/version_matcher.py",
        "abstract/dependency.py",
        "abstract/issues.py",
        "abstract/release.py",
        "checker.py",
        "cmd.py",
        "exceptions.py",
        "typing.py",
    ],
)
