# Dev dependency audit: `py/deps/requirements.in`

Generated: 2026-05-10 23:04 UTC
Source: `py/deps/requirements.in` @ `544fa189bb2340748783a6831cdc30e074479e00`

## Summary
- Total entries (non-empty lines): 69
- Unique package names: 68
- ✅ Used: 51
- 🔁 Transitive only: 9
- 🛠️ CLI/build tool: 5
- ❌ Unused: 2
- ❓ Unclear: 1

## Method
- Checked BUILD-level usage by searching for `//py/deps:reqs#<name>` across repository BUILD files.
- Checked Python usage by scanning import statements in `py/**/*.py` (including tests).
- Checked non-Python usage in repo config/build/CI files (`.bzl`, workflow yaml, shell/toml/ini/cfg/json/txt/md`) excluding `py/deps/requirements.in`, `py/deps/requirements.txt`, and `py/deps/deps.lock`.
- Used `py/deps/requirements.txt` `# via` provenance for transitive-dependency analysis.

## Removal candidates (TL;DR)
- `envoy.distribution.release` — published CLI package with no in-repo `//py/deps:reqs#...` consumers
- `envoy.distribution.verify` — published CLI package with no in-repo `//py/deps:reqs#...` consumers
- `envoy.gpg.sign` — published CLI package with no in-repo `//py/deps:reqs#...` consumers
- `pyjwt` — only transitive via gidgethub
- `multidict` — only transitive via aio-api-github, aiohttp, yarl
- `sphinxcontrib-applehelp` — only transitive via sphinx
- `sphinxcontrib-devhelp` — only transitive via sphinx
- `sphinxcontrib-htmlhelp` — only transitive via sphinx
- `sphinxcontrib-qthelp` — only transitive via sphinx
- `types-setuptools` — no BUILD refs, imports, or transitive requirement chain found
- `urllib3` — only transitive via requests
- `wheel-inspect` — no BUILD refs, imports, or transitive requirement chain found
- `yarl` — only transitive via aio-api-github, aiohttp
- `types-docutils` — only transitive via types-pygments

## Per-package findings

### `abstracts`
- **requirements.in line(s)**: 1
- **Status**: ✅ Used
- **BUILD refs**: `py/aio.api.bazel/aio/api/bazel/BUILD`, `py/aio.api.bazel/tests/BUILD`, `py/aio.api.github/aio/api/github/BUILD`, `py/aio.api.github/tests/BUILD`, `py/aio.api.nist/aio/api/nist/BUILD` (+21 more)
- **Python imports**: `py/abstracts/abstracts/abstraction.py`, `py/abstracts/abstracts/decorators.py`, `py/abstracts/abstracts/implements.py`, `py/abstracts/abstracts/interface.py`, `py/abstracts/tests/test_decorators.py` (+132 more)
- **Other build/config/CI refs**: `.github/workflows/releasing.yml`, `ci/requirements.txt`, `mypy.ini`, `py/README.md`, `py/abstracts/setup.cfg` (+23 more)
- **Transitive via (`requirements.txt`)**: `aio-api-bazel`, `aio-api-github`, `aio-api-nist`, `aio-core`, `aio-run-checker`, `aio-run-runner`, `envoy-base-utils`, `envoy-distribution-release` (+3 more)
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `aio.api.bazel`
- **requirements.in line(s)**: 2
- **Status**: ✅ Used
- **BUILD refs**: none
- **Python imports**: `py/aio.api.bazel/aio/api/bazel/abstract/base.py`, `py/aio.api.bazel/aio/api/bazel/abstract/env.py`, `py/aio.api.bazel/aio/api/bazel/abstract/query.py`, `py/aio.api.bazel/aio/api/bazel/abstract/run.py`, `py/aio.api.bazel/aio/api/bazel/abstract/worker.py` (+3 more)
- **Other build/config/CI refs**: `py/README.md`, `py/aio.api.bazel/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `aio.api.github`
- **requirements.in line(s)**: 3
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.base.utils/envoy/base/utils/BUILD`, `py/envoy.base.utils/tests/BUILD`, `py/envoy.ci.report/envoy/ci/report/BUILD`, `py/envoy.dependency.check/envoy/dependency/check/BUILD`, `py/envoy.dependency.check/tests/BUILD`
- **Python imports**: `py/aio.api.github/aio/api/github/abstract/actions/actions.py`, `py/aio.api.github/aio/api/github/abstract/api.py`, `py/aio.api.github/aio/api/github/abstract/base.py`, `py/aio.api.github/aio/api/github/abstract/commit.py`, `py/aio.api.github/aio/api/github/abstract/issues/issues.py` (+8 more)
- **Other build/config/CI refs**: `.github/workflows/releasing.yml`, `ci/requirements.txt`, `py/README.md`, `py/aio.api.github/setup.cfg`, `py/envoy.base.utils/setup.cfg` (+2 more)
- **Transitive via (`requirements.txt`)**: `envoy-base-utils`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `aio.api.nist`
- **requirements.in line(s)**: 4
- **Status**: ✅ Used
- **BUILD refs**: none
- **Python imports**: `py/aio.api.nist/aio/api/nist/abstract/cpe.py`, `py/aio.api.nist/aio/api/nist/abstract/cve.py`, `py/aio.api.nist/aio/api/nist/abstract/downloader.py`, `py/aio.api.nist/aio/api/nist/abstract/matcher.py`, `py/aio.api.nist/aio/api/nist/abstract/parser.py` (+1 more)
- **Other build/config/CI refs**: `py/README.md`, `py/aio.api.nist/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `aio.core`
- **requirements.in line(s)**: 5
- **Status**: ✅ Used
- **BUILD refs**: `py/aio.api.bazel/aio/api/bazel/BUILD`, `py/aio.api.bazel/tests/BUILD`, `py/aio.api.github/aio/api/github/BUILD`, `py/aio.api.github/tests/BUILD`, `py/aio.api.nist/aio/api/nist/BUILD` (+18 more)
- **Python imports**: `py/aio.api.bazel/aio/api/bazel/abstract/worker.py`, `py/aio.api.bazel/aio/api/bazel/interface.py`, `py/aio.api.bazel/tests/test_abstract_worker.py`, `py/aio.api.github/aio/api/github/abstract/issues/tracker.py`, `py/aio.api.github/aio/api/github/abstract/iterator.py` (+86 more)
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/README.md`, `py/aio.api.bazel/setup.cfg`, `py/aio.api.github/setup.cfg`, `py/aio.api.nist/setup.cfg` (+8 more)
- **Transitive via (`requirements.txt`)**: `aio-api-bazel`, `aio-api-github`, `aio-api-nist`, `aio-run-runner`, `envoy-base-utils`, `envoy-distribution-release`, `envoy-github-abstract`, `envoy-github-release` (+1 more)
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `aio.run.checker`
- **requirements.in line(s)**: 6
- **Status**: ✅ Used
- **BUILD refs**: `py/dependatool/dependatool/BUILD`, `py/envoy.code.check/envoy/code/check/BUILD`, `py/envoy.code.check/tests/BUILD`, `py/envoy.dependency.check/envoy/dependency/check/BUILD`, `py/envoy.dependency.check/tests/BUILD` (+4 more)
- **Python imports**: `py/aio.run.checker/aio/run/checker/abstract.py`, `py/aio.run.checker/aio/run/checker/checker.py`, `py/aio.run.checker/tests/test_abstract.py`, `py/aio.run.checker/tests/test_checker.py`, `py/envoy.dependency.check/tests/test_abstract_checker.py` (+1 more)
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/README.md`, `py/aio.run.checker/setup.cfg`, `py/dependatool/setup.cfg`, `py/envoy.code.check/setup.cfg` (+2 more)
- **Transitive via (`requirements.txt`)**: `envoy-distribution-distrotest`, `envoy-distribution-verify`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `aio.run.runner`
- **requirements.in line(s)**: 7
- **Status**: ✅ Used
- **BUILD refs**: `py/aio.api.bazel/aio/api/bazel/BUILD`, `py/aio.api.bazel/tests/BUILD`, `py/aio.run.checker/aio/run/checker/BUILD`, `py/aio.run.checker/tests/BUILD`, `py/envoy.base.utils/envoy/base/utils/BUILD` (+11 more)
- **Python imports**: `py/aio.run.checker/tests/test_checker.py`, `py/aio.run.runner/tests/test_abstract.py`, `py/envoy.base.utils/tests/test_fetch_runner.py`, `py/envoy.base.utils/tests/test_parallel_runner.py`, `py/envoy.base.utils/tests/test_project_runner.py` (+1 more)
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/README.md`, `py/aio.api.bazel/setup.cfg`, `py/aio.run.checker/setup.cfg`, `py/aio.run.runner/setup.cfg` (+6 more)
- **Transitive via (`requirements.txt`)**: `aio-api-bazel`, `aio-run-checker`, `envoy-base-utils`, `envoy-distribution-release`, `envoy-github-abstract`, `envoy-github-release`, `envoy-gpg-sign`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `aiodocker`
- **requirements.in line(s)**: 8
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.docker.utils/envoy/docker/utils/BUILD`
- **Python imports**: `py/envoy.distribution.verify/envoy/distribution/distrotest/distrotest.py`, `py/envoy.distribution.verify/envoy/distribution/verify/checker.py`, `py/envoy.distribution.verify/tests/distrotest/test_distrotest.py`, `py/envoy.docker.utils/envoy/docker/utils/utils.py`
- **Other build/config/CI refs**: `mypy.ini`, `py/envoy.distribution.verify/setup.cfg`, `py/envoy.docker.utils/setup.cfg`
- **Transitive via (`requirements.txt`)**: `envoy-distribution-verify`, `envoy-docker-utils`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `aiofiles`
- **requirements.in line(s)**: 9
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.github.release/envoy/github/release/BUILD`
- **Python imports**: `py/aio.api.github/aio/api/github/abstract/stream/_reader.py`, `py/aio.api.github/aio/api/github/abstract/stream/_writer.py`, `py/aio.api.github/aio/api/github/abstract/stream/base.py`, `py/envoy.github.release/envoy/github/release/stream/_reader.py`, `py/envoy.github.release/envoy/github/release/stream/_writer.py` (+1 more)
- **Other build/config/CI refs**: `py/envoy.github.release/setup.cfg`
- **Transitive via (`requirements.txt`)**: `envoy-github-release`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `aiohttp`
- **requirements.in line(s)**: 10
- **Status**: ✅ Used
- **BUILD refs**: `py/_test_publish_pkg/_test_publish_pkg/BUILD`, `py/aio.api.github/aio/api/github/BUILD`, `py/aio.api.github/tests/BUILD`, `py/aio.api.nist/aio/api/nist/BUILD`, `py/envoy.base.utils/envoy/base/utils/BUILD` (+4 more)
- **Python imports**: `py/aio.api.github/aio/api/github/abstract/api.py`, `py/aio.api.github/aio/api/github/abstract/stream/_writer.py`, `py/aio.api.github/aio/api/github/interface.py`, `py/aio.api.nist/aio/api/nist/abstract/downloader.py`, `py/aio.api.nist/aio/api/nist/typing.py` (+16 more)
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/_test_publish_pkg/setup.cfg`, `py/aio.api.github/setup.cfg`, `py/aio.api.nist/setup.cfg`, `py/envoy.base.utils/setup.cfg` (+2 more)
- **Transitive via (`requirements.txt`)**: `aio-api-github`, `aio-api-nist`, `aiodocker`, `envoy-base-utils`, `envoy-github-abstract`, `envoy-github-release`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `colorama`
- **requirements.in line(s)**: 11
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/BUILD`, `py/envoy.docs.sphinx_runner/tests/BUILD`
- **Python imports**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py`
- **Other build/config/CI refs**: `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `coloredlogs`
- **requirements.in line(s)**: 12
- **Status**: ✅ Used
- **BUILD refs**: `py/aio.run.runner/aio/run/runner/BUILD`
- **Python imports**: `py/aio.run.runner/aio/run/runner/runner.py`
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/aio.run.runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: `aio-run-runner`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `docutils`
- **requirements.in line(s)**: 13
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/BUILD`
- **Python imports**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/validating_code_block.py`, `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/sphinx_tabs/tabs.py`, `py/envoy.docs.sphinx_runner/tests/test_extensions.py`
- **Other build/config/CI refs**: `bazel/website/requirements.txt`, `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: `readme-renderer`, `sphinx`, `sphinx-rtd-theme`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `envoy.base.utils`
- **requirements.in line(s)**: 14
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.code.check/envoy/code/check/BUILD`, `py/envoy.code.check/tests/BUILD`, `py/envoy.dependency.check/envoy/dependency/check/BUILD`, `py/envoy.dependency.check/tests/BUILD`, `py/envoy.distribution.release/envoy/distribution/release/BUILD` (+8 more)
- **Python imports**: `py/envoy.base.utils/envoy/base/utils/abstract/project/changelog.py`, `py/envoy.base.utils/envoy/base/utils/abstract/project/inventory.py`, `py/envoy.base.utils/envoy/base/utils/abstract/project/project.py`, `py/envoy.base.utils/envoy/base/utils/abstract/protobuf.py`, `py/envoy.base.utils/envoy/base/utils/interface.py` (+14 more)
- **Other build/config/CI refs**: `.github/workflows/releasing.yml`, `ci/requirements.txt`, `py/README.md`, `py/envoy.base.utils/setup.cfg`, `py/envoy.code.check/setup.cfg` (+6 more)
- **Transitive via (`requirements.txt`)**: `envoy-distribution-distrotest`, `envoy-distribution-release`, `envoy-distribution-verify`, `envoy-github-release`, `envoy-gpg-sign`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `envoy.distribution.release`
- **requirements.in line(s)**: 15
- **Status**: 🛠️ CLI/build tool
- **BUILD refs**: none
- **Python imports**: `py/envoy.distribution.release/tests/test_commands.py`, `py/envoy.distribution.release/tests/test_runner.py`
- **Other build/config/CI refs**: `py/README.md`, `py/envoy.distribution.release/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Published CLI package from this repo; no `//py/deps:reqs#envoy-distribution-release` consumers found (only self-package tests import it). Likely removable from dev resolve.

### `envoy.distribution.verify`
- **requirements.in line(s)**: 16
- **Status**: 🛠️ CLI/build tool
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: `py/README.md`, `py/envoy.distribution.verify/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Published CLI/checker package from this repo; no direct consumers found in BUILD/import usage. Likely removable from dev resolve.

### `envoy.docker.utils`
- **requirements.in line(s)**: 17
- **Status**: 🛠️ CLI/build tool
- **BUILD refs**: `py/envoy.distribution.verify/envoy/distribution/distrotest/BUILD`, `py/envoy.distribution.verify/tests/distrotest/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `py/README.md`, `py/envoy.distribution.verify/setup.cfg`, `py/envoy.docker.utils/setup.cfg`
- **Transitive via (`requirements.txt`)**: `envoy-distribution-distrotest`
- **Notes**: CLI/runtime helper package is consumed by `envoy.distribution.verify` distrotest BUILD targets, so currently needed in dev resolve.

### `envoy.github.release`
- **requirements.in line(s)**: 18
- **Status**: 🛠️ CLI/build tool
- **BUILD refs**: `py/envoy.distribution.release/envoy/distribution/release/BUILD`, `py/envoy.distribution.release/tests/BUILD`
- **Python imports**: `py/envoy.distribution.release/envoy/distribution/release/runner.py`, `py/envoy.distribution.release/tests/test_runner.py`, `py/envoy.github.release/envoy/github/release/assets.py`, `py/envoy.github.release/envoy/github/release/manager.py`, `py/envoy.github.release/envoy/github/release/release.py` (+4 more)
- **Other build/config/CI refs**: `py/README.md`, `py/envoy.distribution.release/setup.cfg`, `py/envoy.github.release/setup.cfg`
- **Transitive via (`requirements.txt`)**: `envoy-distribution-release`
- **Notes**: CLI/runtime release package is consumed by `envoy.distribution.release` BUILD/test targets, so currently needed in dev resolve.

### `envoy.gpg.sign`
- **requirements.in line(s)**: 19
- **Status**: 🛠️ CLI/build tool
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: `py/README.md`, `py/envoy.gpg.sign/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Published CLI package from this repo; no in-repo consumers found. Strong removal candidate from dev resolve.

### `flake8`
- **requirements.in line(s)**: 20
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.code.check/envoy/code/check/BUILD`, `py/envoy.code.check/tests/BUILD`
- **Python imports**: `py/envoy.code.check/envoy/code/check/abstract/__init__.py`, `py/envoy.code.check/envoy/code/check/abstract/flake8.py`, `py/envoy.code.check/tests/test_abstract_flake8.py`
- **Other build/config/CI refs**: `.github/copilot-instructions.md`, `.github/dependabot.yml`, `.github/workflows/py.yml`, `DEVELOPER.md`, `ci/requirements.txt` (+24 more)
- **Transitive via (`requirements.txt`)**: `pep8-naming`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `frozendict`
- **requirements.in line(s)**: 21
- **Status**: ✅ Used
- **BUILD refs**: `py/aio.run.runner/aio/run/runner/BUILD`, `py/envoy.base.utils/envoy/base/utils/BUILD`
- **Python imports**: `py/aio.run.runner/aio/run/runner/runner.py`, `py/envoy.base.utils/envoy/base/utils/abstract/project/changelog.py`, `py/envoy.base.utils/envoy/base/utils/project_runner.py`
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/aio.run.checker/setup.cfg`, `py/aio.run.runner/setup.cfg`, `py/envoy.base.utils/setup.cfg`
- **Transitive via (`requirements.txt`)**: `aio-run-runner`, `envoy-base-utils`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `gidgethub`
- **requirements.in line(s)**: 22
- **Status**: ✅ Used
- **BUILD refs**: `py/aio.api.github/aio/api/github/BUILD`, `py/aio.api.github/tests/BUILD`, `py/envoy.dependency.check/envoy/dependency/check/BUILD`, `py/envoy.github.release/envoy/github/abstract/BUILD`, `py/envoy.github.release/envoy/github/release/BUILD`
- **Python imports**: `py/aio.api.github/aio/api/github/abstract/actions/actions.py`, `py/aio.api.github/aio/api/github/abstract/api.py`, `py/aio.api.github/aio/api/github/abstract/issues/issues.py`, `py/aio.api.github/aio/api/github/abstract/iterator.py`, `py/aio.api.github/aio/api/github/abstract/repo.py` (+19 more)
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/aio.api.github/setup.cfg`, `py/envoy.dependency.check/setup.cfg`, `py/envoy.github.release/setup.cfg`
- **Transitive via (`requirements.txt`)**: `aio-api-github`, `envoy-distribution-release`, `envoy-github-abstract`, `envoy-github-release`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `pyjwt`
- **requirements.in line(s)**: 23
- **Status**: 🔁 Transitive only
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: `ci/requirements.txt`
- **Transitive via (`requirements.txt`)**: `gidgethub`
- **Notes**: No direct in-repo usage found; currently present because another dependency pulls it in transitively. Likely removable from `requirements.in`.

### `jinja2`
- **requirements.in line(s)**: 24
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.base.utils/envoy/base/utils/BUILD`, `py/envoy.dependency.check/envoy/dependency/check/BUILD`
- **Python imports**: `py/envoy.base.utils/envoy/base/utils/abstract/project/changelog.py`, `py/envoy.base.utils/envoy/base/utils/jinja_env.py`
- **Other build/config/CI refs**: `bazel/website/requirements.txt`, `ci/requirements.txt`, `py/envoy.base.utils/setup.cfg`, `py/envoy.dependency.check/setup.cfg`
- **Transitive via (`requirements.txt`)**: `envoy-base-utils`, `sphinx`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `multidict`
- **requirements.in line(s)**: 25
- **Status**: 🔁 Transitive only
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/aio.api.github/setup.cfg`, `py/aio.api.nist/setup.cfg`, `py/envoy.dependency.check/setup.cfg`
- **Transitive via (`requirements.txt`)**: `aio-api-github`, `aiohttp`, `yarl`
- **Notes**: No direct in-repo usage found; currently present because another dependency pulls it in transitively. Likely removable from `requirements.in`.

### `mypy`
- **requirements.in line(s)**: 26
- **Status**: ✅ Used
- **BUILD refs**: `py/mypy-abstracts/mypy_abstracts/BUILD`, `py/mypy-abstracts/tests/BUILD`
- **Python imports**: `py/mypy-abstracts/mypy_abstracts/__init__.py`
- **Other build/config/CI refs**: `.github/copilot-instructions.md`, `.github/dependabot.yml`, `.github/workflows/py.yml`, `mypy.ini`, `pants.toml` (+30 more)
- **Transitive via (`requirements.txt`)**: `mypy-abstracts`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `mypy-abstracts`
- **requirements.in line(s)**: 27
- **Status**: ✅ Used
- **BUILD refs**: none
- **Python imports**: `py/mypy-abstracts/tests/test_mypy_abstracts.py`
- **Other build/config/CI refs**: `mypy.ini`, `py/README.md`, `py/dependatool/mypy.ini`, `py/dependatool/setup.cfg`, `py/deps/mypy/requirements.txt` (+11 more)
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `orjson`
- **requirements.in line(s)**: 28
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.base.utils/envoy/base/utils/BUILD`
- **Python imports**: `py/aio.core/aio/core/functional/utils.py`, `py/envoy.base.utils/envoy/base/utils/utils.py`
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/envoy.base.utils/setup.cfg`
- **Transitive via (`requirements.txt`)**: `envoy-base-utils`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `packaging`
- **requirements.in line(s)**: 29
- **Status**: ✅ Used
- **BUILD refs**: `py/_test_publish_pkg/_test_publish_pkg/BUILD`, `py/aio.api.github/aio/api/github/BUILD`, `py/aio.api.github/tests/BUILD`, `py/aio.api.nist/aio/api/nist/BUILD`, `py/envoy.base.utils/envoy/base/utils/BUILD` (+9 more)
- **Python imports**: `py/aio.api.github/aio/api/github/abstract/release.py`, `py/aio.api.github/aio/api/github/interface.py`, `py/aio.api.github/tests/test_abstract_release.py`, `py/aio.api.nist/aio/api/nist/abstract/matcher.py`, `py/aio.api.nist/aio/api/nist/typing.py` (+23 more)
- **Other build/config/CI refs**: `bazel/sysroot/build_sysroot.sh`, `bazel/website/requirements.txt`, `ci/requirements.txt`, `py/_test_publish_pkg/setup.cfg`, `py/aio.api.github/setup.cfg` (+6 more)
- **Transitive via (`requirements.txt`)**: `aio-api-github`, `aio-api-nist`, `envoy-base-utils`, `envoy-github-abstract`, `envoy-github-release`, `pytest`, `sphinx`, `wheel-inspect`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `pep8-naming`
- **requirements.in line(s)**: 30
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.code.check/tests/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `py/envoy.code.check/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `protobuf`
- **requirements.in line(s)**: 31
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.base.utils/envoy/base/utils/BUILD`, `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/BUILD`
- **Python imports**: `py/envoy.base.utils/envoy/base/utils/__init__.py`, `py/envoy.base.utils/envoy/base/utils/abstract/__init__.py`
- **Other build/config/CI refs**: `bazel-registry/modules/libprotobuf-mutator/1.5.envoy/presubmit.yml`, `bazel-registry/modules/libprotobuf-mutator/1.5.envoy/source.json`, `bazel-registry/modules/libprotobuf-mutator/metadata.json`, `bazel-registry/modules/protobuf/33.4.envoy/source.json`, `bazel-registry/modules/protobuf/metadata.json` (+2 more)
- **Transitive via (`requirements.txt`)**: `envoy-base-utils`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `pygments`
- **requirements.in line(s)**: 32
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/BUILD`
- **Python imports**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/httpdomain.py`, `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/powershell_lexer.py`, `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/sphinx_tabs/tabs.py`
- **Other build/config/CI refs**: `bazel/website/requirements.txt`, `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: `pytest`, `readme-renderer`, `sphinx`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `pytest`
- **requirements.in line(s)**: 33
- **Status**: ✅ Used
- **BUILD refs**: `py/pants-toolshed/toolshed_publish_reqs/BUILD`, `py/tools/publish_check/BUILD`
- **Python imports**: `py/abstracts/tests/test_decorators.py`, `py/abstracts/tests/test_implements.py`, `py/aio.api.bazel/tests/test_abstract_base.py`, `py/aio.api.bazel/tests/test_abstract_env.py`, `py/aio.api.bazel/tests/test_abstract_query.py` (+101 more)
- **Other build/config/CI refs**: `.github/copilot-instructions.md`, `.github/dependabot.yml`, `.github/workflows/py.yml`, `DEVELOPER.md`, `pants.toml` (+26 more)
- **Transitive via (`requirements.txt`)**: `pytest-abstracts`, `pytest-asyncio`, `pytest-iters`, `pytest-patches`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `pytest-abstracts`
- **requirements.in line(s)**: 34
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.distribution.verify/tests/distrotest/BUILD`, `py/envoy.github.release/tests/abstract/BUILD`, `py/envoy.gpg.sign/tests/identity/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `py/README.md`, `py/aio.api.github/setup.cfg`, `py/deps/pytest/requirements.txt`, `py/envoy.base.utils/setup.cfg`, `py/pytest-abstracts/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `pytest-iters`
- **requirements.in line(s)**: 35
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.distribution.verify/tests/distrotest/BUILD`, `py/envoy.github.release/tests/abstract/BUILD`, `py/envoy.gpg.sign/tests/identity/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `py/README.md`, `py/aio.api.github/setup.cfg`, `py/aio.api.nist/setup.cfg`, `py/aio.core/setup.cfg`, `py/aio.run.checker/setup.cfg` (+6 more)
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `pytest-patches`
- **requirements.in line(s)**: 36
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.distribution.verify/tests/distrotest/BUILD`, `py/envoy.github.release/tests/abstract/BUILD`, `py/envoy.gpg.sign/tests/identity/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `py/README.md`, `py/abstracts/setup.cfg`, `py/aio.api.bazel/setup.cfg`, `py/aio.api.github/setup.cfg`, `py/aio.api.nist/setup.cfg` (+17 more)
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `pytest-asyncio`
- **requirements.in line(s)**: 37
- **Status**: ✅ Used
- **BUILD refs**: `py/aio.api.github/tests/BUILD`, `py/envoy.distribution.verify/tests/distrotest/BUILD`, `py/envoy.docker.utils/tests/BUILD`, `py/envoy.github.release/tests/abstract/BUILD`, `py/envoy.gpg.sign/tests/identity/BUILD` (+3 more)
- **Python imports**: none
- **Other build/config/CI refs**: `py/aio.api.bazel/setup.cfg`, `py/aio.api.github/setup.cfg`, `py/aio.api.nist/setup.cfg`, `py/aio.core/setup.cfg`, `py/aio.run.checker/setup.cfg` (+10 more)
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `python-gnupg`
- **requirements.in line(s)**: 38
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.base.utils/envoy/base/utils/BUILD`, `py/envoy.gpg.sign/envoy/gpg/identity/BUILD`
- **Python imports**: `py/envoy.base.utils/envoy/base/utils/fetch_runner.py`, `py/envoy.gpg.sign/envoy/gpg/identity/identity.py`
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/envoy.base.utils/setup.cfg`, `py/envoy.gpg.sign/setup.cfg`
- **Transitive via (`requirements.txt`)**: `envoy-base-utils`, `envoy-gpg-identity`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `pyyaml`
- **requirements.in line(s)**: 39
- **Status**: ✅ Used
- **BUILD refs**: `py/_test_publish_pkg/_test_publish_pkg/BUILD`, `py/aio.core/aio/core/BUILD`, `py/envoy.base.utils/envoy/base/utils/BUILD`, `py/envoy.base.utils/tests/BUILD`
- **Python imports**: `py/aio.core/aio/core/utils/data.py`, `py/envoy.base.utils/envoy/base/utils/abstract/project/changelog.py`, `py/envoy.base.utils/envoy/base/utils/abstract/project/inventory.py`, `py/envoy.base.utils/envoy/base/utils/abstract/protobuf.py`, `py/envoy.base.utils/envoy/base/utils/utils.py` (+9 more)
- **Other build/config/CI refs**: `bazel/website/requirements.txt`, `ci/requirements.txt`, `py/_test_publish_pkg/setup.cfg`, `py/aio.core/setup.cfg`, `py/envoy.base.utils/setup.cfg` (+1 more)
- **Transitive via (`requirements.txt`)**: `aio-core`, `envoy-base-utils`, `yamllint`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `setuptools`
- **requirements.in line(s)**: 40
- **Status**: ✅ Used
- **BUILD refs**: `py/pants-toolshed/tests/BUILD`
- **Python imports**: `py/_test_publish_pkg/setup.py`, `py/abstracts/setup.py`, `py/aio.api.bazel/setup.py`, `py/aio.api.github/setup.py`, `py/aio.api.nist/setup.py` (+18 more)
- **Other build/config/CI refs**: none
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `sphinx`
- **requirements.in line(s)**: 41
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/BUILD`, `py/envoy.docs.sphinx_runner/tests/BUILD`
- **Python imports**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/powershell_lexer.py`, `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/validating_code_block.py`, `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/runner.py`, `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/sphinx_tabs/tabs.py`, `py/envoy.docs.sphinx_runner/tests/test_extensions.py`
- **Other build/config/CI refs**: `py/README.md`, `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/sphinx_tabs/README.md`, `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: `sphinx-copybutton`, `sphinx-rtd-theme`, `sphinxcontrib-httpdomain`, `sphinxcontrib-jquery`, `sphinxext-rediraffe`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `sphinx-copybutton`
- **requirements.in line(s)**: 42
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/BUILD`, `py/envoy.docs.sphinx_runner/tests/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `sphinx-rtd-theme`
- **requirements.in line(s)**: 43
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `sphinxcontrib-applehelp`
- **requirements.in line(s)**: 44
- **Status**: 🔁 Transitive only
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: `sphinx`
- **Notes**: No direct in-repo usage found; currently present because another dependency pulls it in transitively. Likely removable from `requirements.in`.

### `sphinxcontrib-jquery`
- **requirements.in line(s)**: 45
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: `sphinx-rtd-theme`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `sphinxcontrib-httpdomain`
- **requirements.in line(s)**: 46
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/BUILD`, `py/envoy.docs.sphinx_runner/tests/BUILD`
- **Python imports**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/ext/httpdomain.py`
- **Other build/config/CI refs**: `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `sphinxcontrib-devhelp`
- **requirements.in line(s)**: 47
- **Status**: 🔁 Transitive only
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: `sphinx`
- **Notes**: No direct in-repo usage found; currently present because another dependency pulls it in transitively. Likely removable from `requirements.in`.

### `sphinxcontrib-htmlhelp`
- **requirements.in line(s)**: 48
- **Status**: 🔁 Transitive only
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: `sphinx`
- **Notes**: No direct in-repo usage found; currently present because another dependency pulls it in transitively. Likely removable from `requirements.in`.

### `sphinxcontrib-qthelp`
- **requirements.in line(s)**: 49
- **Status**: 🔁 Transitive only
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: `sphinx`
- **Notes**: No direct in-repo usage found; currently present because another dependency pulls it in transitively. Likely removable from `requirements.in`.

### `sphinxcontrib-serializinghtml`
- **requirements.in line(s)**: 50
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/BUILD`, `py/envoy.docs.sphinx_runner/tests/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: `sphinx`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `sphinxext-rediraffe`
- **requirements.in line(s)**: 51
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/BUILD`, `py/envoy.docs.sphinx_runner/tests/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `trycast`
- **requirements.in line(s)**: 52
- **Status**: ✅ Used
- **BUILD refs**: `py/aio.core/aio/core/BUILD`, `py/envoy.base.utils/envoy/base/utils/BUILD`, `py/envoy.base.utils/tests/BUILD`
- **Python imports**: `py/aio.core/aio/core/functional/utils.py`, `py/envoy.base.utils/envoy/base/utils/utils.py`
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/aio.core/setup.cfg`, `py/envoy.base.utils/setup.cfg`
- **Transitive via (`requirements.txt`)**: `aio-core`, `envoy-base-utils`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `types-orjson`
- **requirements.in line(s)**: 53, 67
- **Duplicate entry**: yes (2 occurrences)
- **Status**: ✅ Used
- **BUILD refs**: `py/aio.core/aio/core/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/envoy.base.utils/setup.cfg`
- **Transitive via (`requirements.txt`)**: `aio-core`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `types-setuptools`
- **requirements.in line(s)**: 54
- **Status**: ❌ Unused
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: none
- **Transitive via (`requirements.txt`)**: none
- **Notes**: No direct usage and no transitive requirement chain found from lockfile provenance; candidate for removal from `requirements.in`.

### `urllib3`
- **requirements.in line(s)**: 55
- **Status**: 🔁 Transitive only
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: none
- **Transitive via (`requirements.txt`)**: `requests`
- **Notes**: No direct in-repo usage found; currently present because another dependency pulls it in transitively. Likely removable from `requirements.in`.

### `uvloop`
- **requirements.in line(s)**: 56
- **Status**: ✅ Used
- **BUILD refs**: `py/aio.run.runner/aio/run/runner/BUILD`
- **Python imports**: `py/aio.run.runner/aio/run/runner/runner.py`
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/aio.run.runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: `aio-run-runner`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `verboselogs`
- **requirements.in line(s)**: 57
- **Status**: ✅ Used
- **BUILD refs**: `py/aio.run.runner/aio/run/runner/BUILD`, `py/envoy.github.release/envoy/github/abstract/BUILD`, `py/envoy.github.release/envoy/github/release/BUILD`, `py/envoy.gpg.sign/envoy/gpg/sign/BUILD`
- **Python imports**: `py/aio.run.runner/aio/run/runner/runner.py`, `py/aio.run.runner/tests/test_runner.py`, `py/envoy.distribution.verify/envoy/distribution/distrotest/distrotest.py`, `py/envoy.github.release/envoy/github/abstract/manager.py`, `py/envoy.github.release/envoy/github/release/manager.py` (+2 more)
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/aio.run.runner/setup.cfg`, `py/envoy.github.release/setup.cfg`, `py/envoy.gpg.sign/setup.cfg`
- **Transitive via (`requirements.txt`)**: `aio-run-runner`, `envoy-github-abstract`, `envoy-github-release`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `wheel-inspect`
- **requirements.in line(s)**: 58
- **Status**: ❌ Unused
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: none
- **Transitive via (`requirements.txt`)**: none
- **Notes**: No direct usage and no transitive requirement chain found from lockfile provenance; candidate for removal from `requirements.in`.

### `yamllint`
- **requirements.in line(s)**: 59
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.code.check/envoy/code/check/BUILD`
- **Python imports**: `py/envoy.code.check/envoy/code/check/abstract/__init__.py`, `py/envoy.code.check/envoy/code/check/abstract/checker.py`, `py/envoy.code.check/envoy/code/check/abstract/yamllint.py`
- **Other build/config/CI refs**: `.github/workflows/lint.yml`, `ci/requirements.txt`, `py/envoy.code.check/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `yapf`
- **requirements.in line(s)**: 60
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.code.check/envoy/code/check/BUILD`, `py/envoy.code.check/tests/BUILD`
- **Python imports**: `py/envoy.code.check/envoy/code/check/abstract/__init__.py`, `py/envoy.code.check/envoy/code/check/abstract/yapf.py`, `py/envoy.code.check/tests/test_abstract_yapf.py`
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/envoy.code.check/setup.cfg`, `pytest.ini`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `yarl`
- **requirements.in line(s)**: 61
- **Status**: 🔁 Transitive only
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/aio.api.github/setup.cfg`, `py/aio.api.nist/setup.cfg`, `py/envoy.dependency.check/setup.cfg`
- **Transitive via (`requirements.txt`)**: `aio-api-github`, `aiohttp`
- **Notes**: No direct in-repo usage found; currently present because another dependency pulls it in transitively. Likely removable from `requirements.in`.

### `zstandard`
- **requirements.in line(s)**: 62
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.base.utils/envoy/base/utils/BUILD`
- **Python imports**: `py/envoy.base.utils/envoy/base/utils/tar.py`
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/envoy.base.utils/setup.cfg`
- **Transitive via (`requirements.txt`)**: `envoy-base-utils`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `types-aiofiles`
- **requirements.in line(s)**: 64
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.github.release/envoy/github/release/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: none
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `types-docutils`
- **requirements.in line(s)**: 65
- **Status**: 🔁 Transitive only
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: `types-pygments`
- **Notes**: No direct in-repo usage found; currently present because another dependency pulls it in transitively. Likely removable from `requirements.in`.

### `types-frozendict`
- **requirements.in line(s)**: 66
- **Status**: ❓ Unclear
- **BUILD refs**: none
- **Python imports**: none
- **Other build/config/CI refs**: `py/aio.run.checker/setup.cfg`, `py/aio.run.runner/setup.cfg`, `py/envoy.base.utils/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: No direct BUILD/import usage found; appears only in package metadata/config references. Maintainer decision needed on whether explicit pin is still required.

### `types-protobuf`
- **requirements.in line(s)**: 68
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.base.utils/envoy/base/utils/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/envoy.base.utils/setup.cfg`
- **Transitive via (`requirements.txt`)**: `envoy-base-utils`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `types-pygments`
- **requirements.in line(s)**: 69
- **Status**: ✅ Used
- **BUILD refs**: `py/envoy.docs.sphinx_runner/envoy/docs/sphinx_runner/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `py/envoy.docs.sphinx_runner/setup.cfg`
- **Transitive via (`requirements.txt`)**: none
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.

### `types-pyyaml`
- **requirements.in line(s)**: 70
- **Status**: ✅ Used
- **BUILD refs**: `py/aio.core/aio/core/BUILD`, `py/envoy.code.check/envoy/code/check/BUILD`
- **Python imports**: none
- **Other build/config/CI refs**: `ci/requirements.txt`, `py/envoy.base.utils/setup.cfg`
- **Transitive via (`requirements.txt`)**: `aio-core`
- **Notes**: Directly referenced in repo (BUILD and/or imports), so keep as explicitly listed dev dependency.
