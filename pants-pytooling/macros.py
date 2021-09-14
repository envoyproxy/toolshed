

def _dep_on_myself(namespace: str) -> list:
    # This prevents dependency conflicts on a package's own upstream
    return [
        f"!//deps:{namespace}",
        f"{namespace}/{namespace.replace('.', '/').replace('-', '_')}"]


def pytooling_library(
        namespace: str,
        dependencies = None,  # Optional[List]
        **kwargs) -> None:
    """Library of namespaced code that can be packaged"""
    resources(
        name="package_data",
        sources=["py.typed"])
    python_library(
        dependencies=(
            _dep_on_myself(namespace)
            + [":package_data"]
            + (dependencies or [])),
        **kwargs)


def pytooling_package(
        namespace: str,
        dependencies = None,  # Optional[List] = None,
        library_kwargs = None,  # Optional[Dict] = None,
        setup_kwargs = None,  # Optional[Dict] = None,
        **kwargs) -> None:
    """Namespaced distribution package"""
    dependencies = (
        _dep_on_myself(namespace)
        + (dependencies or []))
    python_library(
        skip_mypy=True,
        dependencies=dependencies,
        **library_kwargs or {})

    files(
        name="build_artefacts",
        sources=["setup.cfg"])

    pytooling_distribution(
        name="package",
        dependencies=dependencies,
        provides=setup_py(
            name=namespace,
            **setup_kwargs or {}),
        verify_targets=[
            "//:check_modules",
            "//:check_metadata",
            "//:check_dependencies"],
        setup_py_commands=["bdist_wheel", "sdist"],
        **kwargs)


def pytooling_tests(
        namespace: str,
        dependencies = None,  # Optional[List] = None,
        **kwargs) -> None:
    """Test library for a namespaced package"""
    python_tests(
        dependencies=(
            _dep_on_myself(namespace)
            + (dependencies or [])),
        skip_mypy=True,
        **kwargs)
