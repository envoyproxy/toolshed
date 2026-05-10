
python_tests(
    name="publish_check",
    sources=["test_publish_requirements.py"],
    dependencies=[
        "//py/deps:reqs#packaging",
        "//py/deps:reqs#pytest",
        "//py/deps:reqs#pytest-asyncio",
        # dev resolve lockfile for Check B
        "//py/deps:dev_requirements",
        # per-package setup.cfg (via build_artefacts resources) for Check B
        "//py/_test_publish_pkg:build_artefacts",
        "//py/abstracts:build_artefacts",
        "//py/aio.api.bazel:build_artefacts",
        "//py/aio.api.github:build_artefacts",
        "//py/aio.api.nist:build_artefacts",
        "//py/aio.core:build_artefacts",
        "//py/aio.run.checker:build_artefacts",
        "//py/aio.run.runner:build_artefacts",
        "//py/dependatool:build_artefacts",
        "//py/envoy.base.utils:build_artefacts",
        "//py/envoy.ci.report:build_artefacts",
        "//py/envoy.code.check:build_artefacts",
        "//py/envoy.dependency.check:build_artefacts",
        "//py/envoy.distribution.release:build_artefacts",
        "//py/envoy.distribution.verify:build_artefacts",
        "//py/envoy.docker.utils:build_artefacts",
        "//py/envoy.docs.sphinx_runner:build_artefacts",
        "//py/envoy.github.release:build_artefacts",
        "//py/envoy.gpg.sign:build_artefacts",
        "//py/mypy-abstracts:build_artefacts",
        "//py/pytest-abstracts:build_artefacts",
        "//py/pytest-iters:build_artefacts",
        "//py/pytest-patches:build_artefacts",
    ],
)

python_tests(
    name="publish_wheel_metadata_check",
    sources=["test_publish_wheel_metadata.py"],
    skip_mypy=True,
    runtime_package_dependencies=["//py/_test_publish_pkg:package"],
    dependencies=[
        "//py/deps:reqs#packaging",
        "//py/deps:reqs#pytest",
        "//py/deps:reqs#pytest-asyncio",
    ],
)
