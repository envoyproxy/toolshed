

## Envoy toolshed

<img src="https://github.com/envoyproxy/toolshed/raw/2f3ada749e0d8052b3be2705ac808ed649fcf7e1/envoy-pytooling.png" width="100" align="left" />

Multi-language tooling and libraries for Envoy proxy's CI and development workflows

[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/envoyproxy/toolshed/badge)](https://securityscorecards.dev/viewer/?uri=github.com/envoyproxy/toolshed)

<br clear="both" />

### Contents

- **[py/](py/)** - Python packages, libraries, runners, checkers, and dependencies - see [py/README.md](py/README.md) for details
- **[bazel/](bazel/)** - Bazel build configurations and rules
- **[rust/](rust/)** - Rust tooling and libraries
- **[gh-actions/](gh-actions/)** - GitHub Actions workflows
- **[sh/](sh/)** - Shell scripts and utilities

### Development

See [DEVELOPER.md](DEVELOPER.md) for information on building, testing, and contributing to the toolshed.

<details>
<summary>Legacy: Detailed Python package list (click to expand)</summary>

This detailed package information is maintained for backward compatibility. For current information, please see [py/README.md](py/README.md).

#### [abstracts](py/abstracts)

version: 0.0.13.dev0

pypi: https://pypi.org/project/abstracts

---


#### [aio.api.bazel](py/aio.api.bazel)

version: 0.0.3.dev0

pypi: https://pypi.org/project/aio.api.bazel

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.10.1
- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3

---


#### [aio.api.github](py/aio.api.github)

version: 0.2.8.dev0

pypi: https://pypi.org/project/aio.api.github

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.10.1
- [aiohttp](https://pypi.org/project/aiohttp) >=3.8.1
- [gidgethub](https://pypi.org/project/gidgethub)
- [multidict](https://pypi.org/project/multidict) >=6.0.2
- [packaging](https://pypi.org/project/packaging) >=23.0
- [yarl](https://pypi.org/project/yarl) >=1.7.2

---


#### [aio.api.nist](py/aio.api.nist)

version: 0.0.5.dev0

pypi: https://pypi.org/project/aio.api.nist

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.10.1
- [aiohttp](https://pypi.org/project/aiohttp) >=3.8.1
- [multidict](https://pypi.org/project/multidict) >=6.0.2
- [packaging](https://pypi.org/project/packaging)
- [yarl](https://pypi.org/project/yarl) >=1.7.2

---


#### [aio.core](py/aio.core)

version: 0.10.4.dev0

pypi: https://pypi.org/project/aio.core

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [pytz](https://pypi.org/project/pytz)
- [pyyaml](https://pypi.org/project/pyyaml)
- [trycast](https://pypi.org/project/trycast) >=0.7.3

---


#### [aio.run.checker](py/aio.run.checker)

version: 0.5.8.dev0

pypi: https://pypi.org/project/aio.run.checker

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3

---


#### [aio.run.runner](py/aio.run.runner)

version: 0.3.4.dev0

pypi: https://pypi.org/project/aio.run.runner

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.10.1
- [coloredlogs](https://pypi.org/project/coloredlogs)
- [frozendict](https://pypi.org/project/frozendict)
- [uvloop](https://pypi.org/project/uvloop)
- [verboselogs](https://pypi.org/project/verboselogs)

---


#### [dependatool](py/dependatool)

version: 0.2.4.dev0

pypi: https://pypi.org/project/dependatool

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.10.1
- [aio.run.checker](https://pypi.org/project/aio.run.checker) >=0.5.7

---


#### [envoy.base.utils](py/envoy.base.utils)

version: 0.5.6.dev0

pypi: https://pypi.org/project/envoy.base.utils

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.api.github](https://pypi.org/project/aio.api.github) >=0.2.5
- [aio.core](https://pypi.org/project/aio.core) >=0.10.1
- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3
- [aiohttp](https://pypi.org/project/aiohttp) >=3.8.1
- [frozendict](https://pypi.org/project/frozendict)
- [jinja2](https://pypi.org/project/jinja2)
- [multidict](https://pypi.org/project/multidict) >=6.0.2
- [orjson](https://pypi.org/project/orjson)
- [packaging](https://pypi.org/project/packaging) >=23.0
- [protobuf](https://pypi.org/project/protobuf)
- [python-gnupg](https://pypi.org/project/python-gnupg)
- [pytz](https://pypi.org/project/pytz)
- [pyyaml](https://pypi.org/project/pyyaml)
- [trycast](https://pypi.org/project/trycast) >=0.7.3
- [yarl](https://pypi.org/project/yarl) >=1.7.2
- [zstandard](https://pypi.org/project/zstandard)

---


#### [envoy.ci.report](py/envoy.ci.report)

version: 0.0.1.dev0

pypi: https://pypi.org/project/envoy.ci.report

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.api.github](https://pypi.org/project/aio.api.github) >=0.2.7
- [aio.core](https://pypi.org/project/aio.core) >=0.10.3
- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3

---


#### [envoy.code.check](py/envoy.code.check)

version: 0.5.14.dev0

pypi: https://pypi.org/project/envoy.code.check

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.10.3
- [aio.run.checker](https://pypi.org/project/aio.run.checker) >=0.5.7
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.4.2
- [flake8](https://pypi.org/project/flake8) >=6
- [packaging](https://pypi.org/project/packaging) >=23.0
- [pep8-naming](https://pypi.org/project/pep8-naming)
- [yamllint](https://pypi.org/project/yamllint)
- [yapf](https://pypi.org/project/yapf)

---


#### [envoy.dependency.check](py/envoy.dependency.check)

version: 0.1.14.dev0

pypi: https://pypi.org/project/envoy.dependency.check

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.api.github](https://pypi.org/project/aio.api.github) >=0.2.6
- [aio.api.nist](https://pypi.org/project/aio.api.nist) >=0.0.4
- [aio.core](https://pypi.org/project/aio.core) >=0.10.1
- [aio.run.checker](https://pypi.org/project/aio.run.checker) >=0.5.7
- [aiohttp](https://pypi.org/project/aiohttp) >=3.8.1
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.3.10
- [gidgethub](https://pypi.org/project/gidgethub)
- [jinja2](https://pypi.org/project/jinja2)
- [multidict](https://pypi.org/project/multidict) >=6.0.2
- [packaging](https://pypi.org/project/packaging)
- [yarl](https://pypi.org/project/yarl) >=1.7.2

---


#### [envoy.distribution.distrotest](py/envoy.distribution.distrotest)

version: 0.0.11.dev0

pypi: https://pypi.org/project/envoy.distribution.distrotest

##### requirements:

- [aio.run.checker](https://pypi.org/project/aio.run.checker) >=0.5.7
- [aiodocker](https://pypi.org/project/aiodocker)
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.3.9
- [envoy.docker.utils](https://pypi.org/project/envoy.docker.utils) >=0.0.2

---


#### [envoy.distribution.release](py/envoy.distribution.release)

version: 0.0.10.dev0

pypi: https://pypi.org/project/envoy.distribution.release

##### requirements:

- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3
- [envoy.github.abstract](https://pypi.org/project/envoy.github.abstract) >=0.0.22
- [envoy.github.release](https://pypi.org/project/envoy.github.release) >=0.0.14

---


#### [envoy.distribution.repo](py/envoy.distribution.repo)

version: 0.0.9.dev0

pypi: https://pypi.org/project/envoy.distribution.repo

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.10.1
- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.3.9
- [envoy.github.abstract](https://pypi.org/project/envoy.github.abstract) >=0.0.22
- [envoy.github.release](https://pypi.org/project/envoy.github.release) >=0.0.14

---


#### [envoy.distribution.verify](py/envoy.distribution.verify)

version: 0.0.12.dev0

pypi: https://pypi.org/project/envoy.distribution.verify

##### requirements:

- [aio.run.checker](https://pypi.org/project/aio.run.checker) >=0.5.7
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.3.9
- [envoy.distribution.distrotest](https://pypi.org/project/envoy.distribution.distrotest) >=0.0.9

---


#### [envoy.docker.utils](py/envoy.docker.utils)

version: 0.0.3.dev0

pypi: https://pypi.org/project/envoy.docker.utils

##### requirements:

- [aiodocker](https://pypi.org/project/aiodocker)

---


#### [envoy.docs.sphinx_runner](py/envoy.docs.sphinx_runner)

version: 0.2.12.dev0

pypi: https://pypi.org/project/envoy.docs.sphinx_runner

##### requirements:

- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3
- [colorama](https://pypi.org/project/colorama)
- [docutils](https://pypi.org/project/docutils) ~=0.19.0
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.3.10
- [envoy.code.check](https://pypi.org/project/envoy.code.check) >=0.3.6
- [packaging](https://pypi.org/project/packaging) >=23.0
- [pygments](https://pypi.org/project/pygments) >=2.11.1
- [pyyaml](https://pypi.org/project/pyyaml)
- [sphinx-copybutton](https://pypi.org/project/sphinx-copybutton)
- [sphinx-rtd-theme](https://pypi.org/project/sphinx-rtd-theme) >=2.0.0rc2
- [sphinx](https://pypi.org/project/sphinx) >=7.2.2
- [sphinxcontrib-applehelp](https://pypi.org/project/sphinxcontrib-applehelp)
- [sphinxcontrib-devhelp](https://pypi.org/project/sphinxcontrib-devhelp)
- [sphinxcontrib-htmlhelp](https://pypi.org/project/sphinxcontrib-htmlhelp)
- [sphinxcontrib-httpdomain](https://pypi.org/project/sphinxcontrib-httpdomain)
- [sphinxcontrib-jquery](https://pypi.org/project/sphinxcontrib-jquery) >=3.0.0
- [sphinxcontrib-qthelp](https://pypi.org/project/sphinxcontrib-qthelp)
- [sphinxcontrib-serializinghtml](https://pypi.org/project/sphinxcontrib-serializinghtml)
- [sphinxext-rediraffe](https://pypi.org/project/sphinxext-rediraffe)

---


#### [envoy.github.abstract](py/envoy.github.abstract)

version: 0.0.23.dev0

pypi: https://pypi.org/project/envoy.github.abstract

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.10.1
- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.2.1
- [aiohttp](https://pypi.org/project/aiohttp)
- [gidgethub](https://pypi.org/project/gidgethub)
- [verboselogs](https://pypi.org/project/verboselogs)

---


#### [envoy.github.release](py/envoy.github.release)

version: 0.0.16.dev0

pypi: https://pypi.org/project/envoy.github.release

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.10.1
- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3
- [aiofiles](https://pypi.org/project/aiofiles)
- [aiohttp](https://pypi.org/project/aiohttp)
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.3.9
- [envoy.github.abstract](https://pypi.org/project/envoy.github.abstract) >=0.0.22
- [gidgethub](https://pypi.org/project/gidgethub)
- [packaging](https://pypi.org/project/packaging) >=23.0
- [verboselogs](https://pypi.org/project/verboselogs)

---


#### [envoy.gpg.identity](py/envoy.gpg.identity)

version: 0.1.2.dev0

pypi: https://pypi.org/project/envoy.gpg.identity

##### requirements:

- [aio.core](https://pypi.org/project/aio.core) >=0.10.1
- [python-gnupg](https://pypi.org/project/python-gnupg)

---


#### [envoy.gpg.sign](py/envoy.gpg.sign)

version: 0.2.1.dev0

pypi: https://pypi.org/project/envoy.gpg.sign

##### requirements:

- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.4.7
- [envoy.gpg.identity](https://pypi.org/project/envoy.gpg.identity) >=0.1.1

---


#### [mypy-abstracts](py/mypy-abstracts)

version: 0.0.7.dev0

pypi: https://pypi.org/project/mypy-abstracts

##### requirements:

- [mypy](https://pypi.org/project/mypy)

---


#### [pytest-abstracts](py/pytest-abstracts)

version: 0.0.5.dev0

pypi: https://pypi.org/project/pytest-abstracts

##### requirements:

- [abstracts](https://pypi.org/project/abstracts)
- [pytest](https://pypi.org/project/pytest) >=3.5.0

---


#### [pytest-iters](py/pytest-iters)

version: 0.0.4.dev0

pypi: https://pypi.org/project/pytest-iters

##### requirements:

- [pytest](https://pypi.org/project/pytest) >=3.5.0

---


#### [pytest-patches](py/pytest-patches)

version: 0.0.4.dev0

pypi: https://pypi.org/project/pytest-patches

##### requirements:

- [pytest](https://pypi.org/project/pytest) >=3.5.0

---

</details>

