

## Envoy pytooling

<img src="https://github.com/envoyproxy/pytooling/raw/2f3ada749e0d8052b3be2705ac808ed649fcf7e1/envoy-pytooling.png" width="100" align="left" />

Python libraries, runners and checkers for Envoy proxy's CI

<br clear="both" />

### Packages


#### [abstracts](abstracts)

version: 0.0.13.dev0

pypi: https://pypi.org/project/abstracts

---


#### [aio.api.bazel](aio.api.bazel)

version: 0.0.3.dev0

pypi: https://pypi.org/project/aio.api.bazel

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.8.9
- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3

---


#### [aio.api.github](aio.api.github)

version: 0.1.5.dev0

pypi: https://pypi.org/project/aio.api.github

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.9.1
- [aiohttp](https://pypi.org/project/aiohttp) >=3.8.1
- [gidgethub](https://pypi.org/project/gidgethub)
- [multidict](https://pypi.org/project/multidict) >=6.0.2
- [packaging](https://pypi.org/project/packaging)
- [yarl](https://pypi.org/project/yarl) >=1.7.2

---


#### [aio.api.nist](aio.api.nist)

version: 0.0.4.dev0

pypi: https://pypi.org/project/aio.api.nist

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.9.1
- [aiohttp](https://pypi.org/project/aiohttp) >=3.8.1
- [multidict](https://pypi.org/project/multidict) >=6.0.2
- [packaging](https://pypi.org/project/packaging)
- [yarl](https://pypi.org/project/yarl) >=1.7.2

---


#### [aio.core](aio.core)

version: 0.9.2.dev0

pypi: https://pypi.org/project/aio.core

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [trycast](https://pypi.org/project/trycast) >=0.7.3

---


#### [aio.run.checker](aio.run.checker)

version: 0.5.8.dev0

pypi: https://pypi.org/project/aio.run.checker

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3

---


#### [aio.run.runner](aio.run.runner)

version: 0.3.4.dev0

pypi: https://pypi.org/project/aio.run.runner

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.8.6
- [coloredlogs](https://pypi.org/project/coloredlogs)
- [frozendict](https://pypi.org/project/frozendict)
- [uvloop](https://pypi.org/project/uvloop)
- [verboselogs](https://pypi.org/project/verboselogs)

---


#### [envoy.base.utils](envoy.base.utils)

version: 0.3.8

pypi: https://pypi.org/project/envoy.base.utils

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.api.github](https://pypi.org/project/aio.api.github) >=0.1.4
- [aio.core](https://pypi.org/project/aio.core) >=0.9.1
- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3
- [aiohttp](https://pypi.org/project/aiohttp) >=3.8.1
- [frozendict](https://pypi.org/project/frozendict)
- [jinja2](https://pypi.org/project/jinja2)
- [multidict](https://pypi.org/project/multidict) >=6.0.2
- [orjson](https://pypi.org/project/orjson)
- [packaging](https://pypi.org/project/packaging)
- [protobuf](https://pypi.org/project/protobuf)
- [pytz](https://pypi.org/project/pytz)
- [pyyaml](https://pypi.org/project/pyyaml)
- [trycast](https://pypi.org/project/trycast) >=0.7.3
- [yarl](https://pypi.org/project/yarl) >=1.7.2

---


#### [envoy.code.check](envoy.code.check)

version: 0.3.2.dev0

pypi: https://pypi.org/project/envoy.code.check

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.8.9
- [aio.run.checker](https://pypi.org/project/aio.run.checker) >=0.5.7
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.3.4
- [flake8](https://pypi.org/project/flake8) >=5.0.4
- [packaging](https://pypi.org/project/packaging)
- [pep8-naming](https://pypi.org/project/pep8-naming)
- [yamllint](https://pypi.org/project/yamllint)
- [yapf](https://pypi.org/project/yapf)

---


#### [envoy.dependency.check](envoy.dependency.check)

version: 0.1.6.dev0

pypi: https://pypi.org/project/envoy.dependency.check

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.api.github](https://pypi.org/project/aio.api.github) >=0.1.2
- [aio.api.nist](https://pypi.org/project/aio.api.nist) >=0.0.3
- [aio.core](https://pypi.org/project/aio.core) >=0.9.1
- [aio.run.checker](https://pypi.org/project/aio.run.checker) >=0.5.5
- [aiohttp](https://pypi.org/project/aiohttp) >=3.8.1
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.3.6
- [gidgethub](https://pypi.org/project/gidgethub)
- [jinja2](https://pypi.org/project/jinja2)
- [multidict](https://pypi.org/project/multidict) >=6.0.2
- [packaging](https://pypi.org/project/packaging)
- [yarl](https://pypi.org/project/yarl) >=1.7.2

---


#### [envoy.dependency.pip_check](envoy.dependency.pip_check)

version: 0.1.4.dev0

pypi: https://pypi.org/project/envoy.dependency.pip_check

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.run.checker](https://pypi.org/project/aio.run.checker) >=0.4.0
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.1.0

---


#### [envoy.distribution.distrotest](envoy.distribution.distrotest)

version: 0.0.10.dev0

pypi: https://pypi.org/project/envoy.distribution.distrotest

##### requirements:

- [aio.run.checker](https://pypi.org/project/aio.run.checker) >=0.3.0
- [aiodocker](https://pypi.org/project/aiodocker)
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.1.0
- [envoy.docker.utils](https://pypi.org/project/envoy.docker.utils) >=0.0.2

---


#### [envoy.distribution.release](envoy.distribution.release)

version: 0.0.9.dev0

pypi: https://pypi.org/project/envoy.distribution.release

##### requirements:

- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.2.1
- [envoy.github.abstract](https://pypi.org/project/envoy.github.abstract) >=0.0.21
- [envoy.github.release](https://pypi.org/project/envoy.github.release) >=0.0.11

---


#### [envoy.distribution.repo](envoy.distribution.repo)

version: 0.0.8.dev0

pypi: https://pypi.org/project/envoy.distribution.repo

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.3.0
- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.2.1
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.1.0
- [envoy.github.abstract](https://pypi.org/project/envoy.github.abstract) >=0.0.21
- [envoy.github.release](https://pypi.org/project/envoy.github.release) >=0.0.11

---


#### [envoy.distribution.verify](envoy.distribution.verify)

version: 0.0.11.dev0

pypi: https://pypi.org/project/envoy.distribution.verify

##### requirements:

- [aio.run.checker](https://pypi.org/project/aio.run.checker) >=0.3.0
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.1.0
- [envoy.distribution.distrotest](https://pypi.org/project/envoy.distribution.distrotest) >=0.0.7

---


#### [envoy.docker.utils](envoy.docker.utils)

version: 0.0.3.dev0

pypi: https://pypi.org/project/envoy.docker.utils

##### requirements:

- [aiodocker](https://pypi.org/project/aiodocker)

---


#### [envoy.docs.sphinx_runner](envoy.docs.sphinx_runner)

version: 0.1.11.dev0

pypi: https://pypi.org/project/envoy.docs.sphinx_runner

##### requirements:

- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3
- [colorama](https://pypi.org/project/colorama)
- [docutils](https://pypi.org/project/docutils) ~=0.16.0
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.3.6
- [envoy.code.check](https://pypi.org/project/envoy.code.check) >=0.2.2
- [packaging](https://pypi.org/project/packaging)
- [pygments](https://pypi.org/project/pygments) >=2.11.1
- [pyyaml](https://pypi.org/project/pyyaml)
- [sphinx](https://pypi.org/project/sphinx)
- [sphinx-copybutton](https://pypi.org/project/sphinx-copybutton)
- [sphinx-rtd-theme](https://pypi.org/project/sphinx-rtd-theme)
- [sphinx-tabs](https://pypi.org/project/sphinx-tabs)
- [sphinxcontrib-httpdomain](https://pypi.org/project/sphinxcontrib-httpdomain)
- [sphinxcontrib-serializinghtml](https://pypi.org/project/sphinxcontrib-serializinghtml)
- [sphinxext-rediraffe](https://pypi.org/project/sphinxext-rediraffe)

---


#### [envoy.github.abstract](envoy.github.abstract)

version: 0.0.23.dev0

pypi: https://pypi.org/project/envoy.github.abstract

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.12
- [aio.core](https://pypi.org/project/aio.core) >=0.4.0
- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.2.1
- [aiohttp](https://pypi.org/project/aiohttp)
- [gidgethub](https://pypi.org/project/gidgethub)
- [verboselogs](https://pypi.org/project/verboselogs)

---


#### [envoy.github.release](envoy.github.release)

version: 0.0.15.dev0

pypi: https://pypi.org/project/envoy.github.release

##### requirements:

- [abstracts](https://pypi.org/project/abstracts) >=0.0.13
- [aio.core](https://pypi.org/project/aio.core) >=0.9.1
- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.3
- [aiofiles](https://pypi.org/project/aiofiles)
- [aiohttp](https://pypi.org/project/aiohttp)
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.3.6
- [envoy.github.abstract](https://pypi.org/project/envoy.github.abstract) >=0.0.22
- [gidgethub](https://pypi.org/project/gidgethub)
- [packaging](https://pypi.org/project/packaging)
- [verboselogs](https://pypi.org/project/verboselogs)

---


#### [envoy.gpg.identity](envoy.gpg.identity)

version: 0.1.1.dev0

pypi: https://pypi.org/project/envoy.gpg.identity

##### requirements:

- [aio.core](https://pypi.org/project/aio.core) >=0.8.0
- [python-gnupg](https://pypi.org/project/python-gnupg)

---


#### [envoy.gpg.sign](envoy.gpg.sign)

version: 0.1.1.dev0

pypi: https://pypi.org/project/envoy.gpg.sign

##### requirements:

- [aio.run.runner](https://pypi.org/project/aio.run.runner) >=0.3.0
- [envoy.base.utils](https://pypi.org/project/envoy.base.utils) >=0.1.0
- [envoy.gpg.identity](https://pypi.org/project/envoy.gpg.identity) >=0.1.0

---


#### [mypy-abstracts](mypy-abstracts)

version: 0.0.7.dev0

pypi: https://pypi.org/project/mypy-abstracts

##### requirements:

- [mypy](https://pypi.org/project/mypy)

---


#### [pytest-abstracts](pytest-abstracts)

version: 0.0.5.dev0

pypi: https://pypi.org/project/pytest-abstracts

##### requirements:

- [abstracts](https://pypi.org/project/abstracts)
- [pytest](https://pypi.org/project/pytest) >=3.5.0

---


#### [pytest-iters](pytest-iters)

version: 0.0.4.dev0

pypi: https://pypi.org/project/pytest-iters

##### requirements:

- [pytest](https://pypi.org/project/pytest) >=3.5.0

---


#### [pytest-patches](pytest-patches)

version: 0.0.4.dev0

pypi: https://pypi.org/project/pytest-patches

##### requirements:

- [pytest](https://pypi.org/project/pytest) >=3.5.0

---

