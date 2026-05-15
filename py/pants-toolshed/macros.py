

def _dep_on_myself(namespace: str) -> list:
    # This prevents dependency conflicts on a package's own upstream
    return [
        # f"!//py/deps:reqs#{namespace}",
        f"py/{namespace}/{namespace.replace('.', '/').replace('-', '_')}"]


def _canonical_name(name: str) -> str:
    chars = []
    saw_sep = False
    for char in name.strip().lower():
        if char in "-_.":
            if not saw_sep:
                chars.append("-")
            saw_sep = True
            continue
        chars.append(char)
        saw_sep = False
    return "".join(chars)


def _publish_req_target_name(req_str: str) -> str:
    # Keep this logic aligned with toolshed_publish_reqs/rules.py.
    # BUILD macros cannot use import statements, so we cannot reuse
    # packaging.Requirement or toolshed_setup_cfg helpers here.
    # This parser intentionally supports the normalized requirement forms
    # used in toolshed setup.cfg install_requires entries.
    requirement_name_chars = []
    for char in req_str.strip():
        if char in " <>=!~[;":
            break
        requirement_name_chars.append(char)
    canonical = _canonical_name("".join(requirement_name_chars))
    sanitized = "".join(
        char if ("a" <= char <= "z" or "0" <= char <= "9") else "_"
        for char in canonical.replace("-", "_"))
    collapsed = []
    saw_underscore = False
    for char in sanitized:
        if char == "_":
            if not saw_underscore:
                collapsed.append(char)
            saw_underscore = True
            continue
        collapsed.append(char)
        saw_underscore = False
    return f"_publish__{''.join(collapsed)}"


def _req_bare_name(req_str: str) -> str:
    chars = []
    for ch in req_str.strip():
        if ch in " <>=!~[;":
            break
        chars.append(ch)
    return _canonical_name("".join(chars))


def _setup_cfg_install_requires(namespace: str) -> list:
    # Keep this parser aligned with toolshed_setup_cfg.parse_options().
    # BUILD macros cannot import modules, so parsing is inlined here.
    reqs = []
    in_options = False
    in_install_requires = False
    setup_cfg = f"py/{namespace}/setup.cfg"
    for raw_line in open(setup_cfg, encoding="utf-8").read().splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_options = (stripped == "[options]")
            in_install_requires = False
            continue
        if not in_options:
            continue
        if stripped.startswith("install_requires"):
            in_install_requires = True
            if "=" in raw_line:
                value = raw_line.split("=", 1)[1].strip()
                if value:
                    reqs.append(value)
            continue
        if in_install_requires:
            if raw_line and not raw_line[0].isspace():
                in_install_requires = False
                continue
            if stripped and not stripped.startswith("#"):
                reqs.append(stripped)
    return reqs


def _publish_req_dependencies(namespace: str) -> list:
    return [
        f"//py/{namespace}:{_publish_req_target_name(req_str)}"
        for req_str in _setup_cfg_install_requires(namespace)
    ]


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
    """Namespaced distribution package.

    Wheel install_requires originate from synthetic ``python_requirement``
    targets named ``_publish__<canonical_name>`` in each package directory.
    Both the synthetic targets and this macro dependency list are derived
    directly from ``setup.cfg`` ``install_requires``.
    """

    # Source target deps remain whatever was passed in (tests / dev use
    # the pinned //py/deps:reqs#* set as before).
    library_dependencies = (
        _dep_on_myself(namespace)
        + (dependencies or []))

    resources(
        name="build_artefacts",
        sources=["VERSION", "setup.cfg"])

    python_sources(
        skip_mypy=True,
        dependencies=library_dependencies,
        **(library_kwargs or {}))

    # The python_distribution depends on:
    #   - the in-repo source target for this package (so its .py files
    #     are bundled), AND
    #   - synthetic per-package publish requirement targets on the
    #     `publish` resolve (which become install_requires in the wheel).
    #
    # NOTE: pants will also walk the inner python_sources's transitive
    # deps when computing install_requires, which currently includes the
    # pinned //py/deps:reqs#* set (on the default resolve) for tests.
    # Whether those leak into the wheel METADATA is what the wheel
    # METADATA test in //py/_test_publish_pkg is responsible for catching.
    # If the test fails, the structural fix is to stop attaching pinned
    # //py/deps:reqs#* deps to the inner python_sources and put them on
    # the test target only.
    _inner = _dep_on_myself(namespace)[0]
    excluded_reqs = [
        f"!!//py/deps:reqs#{_canonical_name(_req_bare_name(r))}"
        for r in _setup_cfg_install_requires(namespace)]
    publish_req_deps = _publish_req_dependencies(namespace)
    toolshed_distribution(
        name="package",
        dependencies=[
            _inner,
            *publish_req_deps,
            *excluded_reqs,
        ],
        provides=setup_py(
            name=namespace,
            **(setup_kwargs or {})),
        wheel=True,
        sdist=True,
        **kwargs)


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
    if "//py/deps:reqs#pytest-abstracts" not in dependencies:
        dependencies.append("//py/deps:reqs#pytest-abstracts")
    if "//py/deps:reqs#pytest-asyncio" not in dependencies:
        dependencies.append("//py/deps:reqs#pytest-asyncio")
    if "//py/deps:reqs#pytest-iters" not in dependencies:
        dependencies.append("//py/deps:reqs#pytest-iters")
    if "//py/deps:reqs#pytest-patches" not in dependencies:
        dependencies.append("//py/deps:reqs#pytest-patches")

    python_tests(
        dependencies=dependencies,
        skip_mypy=True,
        **kwargs)
