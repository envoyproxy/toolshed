

def pytooling_library(namespace, dependencies=[], **kwargs):
    dependencies = [f"!//:{namespace}", f"{namespace}/{namespace.replace('.', '/').replace('-', '_')}"] + dependencies
    python_library(
        dependencies=dependencies,
        **kwargs)


def pytooling_package(name, dependencies=[], **kwargs):

    python_library(
        skip_mypy=True,
        dependencies=dependencies,
    )

    pytooling_distribution(
        name="package",
        provides=setup_py(
            name=name,
            **kwargs,
        ),
        setup_py_commands=["bdist_wheel", "sdist"],
    )


def pytooling_tests(namespace, dependencies=[], **kwargs):
    dependencies = [f"!//:{namespace}", f"{namespace}/{namespace.replace('.', '/').replace('-', '_')}"] + dependencies
    python_tests(
        dependencies=dependencies,
        skip_mypy=True,
        **kwargs)
