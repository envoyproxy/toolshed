

def _dep_on_myself(namespace: str) -> list:
    # This prevents dependency conflicts on a package's own upstream
    return [
        # f"!//deps:reqs#{namespace}",
        f"{namespace}/{namespace.replace('.', '/').replace('-', '_')}"]


def toolshed_library(
        namespace: str,
        dependencies=None,  # Optional[List]
        **kwargs) -> None:
    """Library of namespaced code that can be packaged"""
    resources(
        name="package_data",
        sources=["py.typed"])
    python_sources(
        dependencies=(
            _dep_on_myself(namespace)
            + [":package_data"]
            + (dependencies or [])),
        **kwargs)


def toolshed_package(
        namespace: str,
        dependencies=None,  # Optional[List] = None,
        library_kwargs=None,  # Optional[Dict] = None,
        setup_kwargs=None,  # Optional[Dict] = None,
        **kwargs) -> None:
    """Namespaced distribution package"""
    dependencies = (
        _dep_on_myself(namespace)
        + (dependencies or []))
    resources(
        name="build_artefacts",
        sources=["VERSION", "setup.cfg"])
    python_sources(
        skip_mypy=True,
        dependencies=dependencies,
        **library_kwargs or {})
    # pytooling_distribution(
    #    name="package",
    #    dependencies=dependencies,
    #    provides=setup_py(
    #        name=namespace,
    #        **setup_kwargs or {}),
    #    wheel=True,
    #    sdist=True,
    #    **kwargs)
    # readme_snippet(
    #     name="package_snippet",
    #     artefacts=[
    #         f"{namespace}:build_artefacts",
    #         "//templates:README.package.md.tmpl"],
    #     text=["//tools/readme:summarize"])


def toolshed_tests(
        namespace: str,
        dependencies=None,  # Optional[List] = None,
        **kwargs) -> None:
    """Test library for a namespaced package"""
    dependencies = (
        _dep_on_myself(namespace)
        + (dependencies or []))

    # TODO: remove this if we add separate per-package
    #   pytest.ini files
    if "//deps:reqs#pytest-abstracts" not in dependencies:
        dependencies.append("//deps:reqs#pytest-abstracts")
    if "//deps:reqs#pytest-asyncio" not in dependencies:
        dependencies.append("//deps:reqs#pytest-asyncio")
    if "//deps:reqs#pytest-iters" not in dependencies:
        dependencies.append("//deps:reqs#pytest-iters")
    if "//deps:reqs#pytest-patches" not in dependencies:
        dependencies.append("//deps:reqs#pytest-patches")

    python_tests(
        dependencies=dependencies,
        skip_mypy=True,
        **kwargs)
