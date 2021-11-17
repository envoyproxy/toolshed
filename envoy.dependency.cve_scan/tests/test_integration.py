
import gzip
import json
import pathlib
from functools import cached_property
from unittest.mock import AsyncMock, PropertyMock
from typing import Type

import yaml

import pytest

import abstracts

from envoy.dependency import cve_scan


#
# As `envoy.dependency.cve_scan` only provides an abstract
# implementation, all classes need to be overridden and wired together.
#
# The advantage of this is that implementations have all of the
# required classes available for customisation or debugging, and
# the structure of the package is explicit.
#
# The integration tests here provide a reference implementation
#

#
# *CVEChecker implementation*
#

@abstracts.implementer(cve_scan.ACVE)
class DummyCVE:

    @property
    def cpe_class(self):
        return DummyCPE

    @property
    def version_matcher_class(self) -> Type[cve_scan.ACVEVersionMatcher]:
        return DummyCVEVersionMatcher


@abstracts.implementer(cve_scan.ACPE)
class DummyCPE:
    pass


@abstracts.implementer(cve_scan.ADependency)
class DummyDependency:
    pass


@abstracts.implementer(cve_scan.ACVEChecker)
class DummyCVEChecker:

    @property
    def cpe_class(self):
        return DummyCPE

    @property
    def cve_class(self):
        return DummyCVE

    @property
    def dependency_class(self):
        return DummyDependency

    # implementations should cache this
    @property
    def dependency_metadata(self):
        # super needs to be mocked for these tests
        return super().dependency_metadata

    @cached_property
    def ignored_cves(self):
        return super().ignored_cves


@abstracts.implementer(cve_scan.ACVEVersionMatcher)
class DummyCVEVersionMatcher:
    pass


#
# *Test data*
#

TEST_DATA = {
    k: {f"{k}:{p.name.split('.')[0]}": p
        for p in pathlib.Path(
            f"envoy.dependency.cve_scan/tests/integration/{k}").glob(
                f"*.{suffix}")}
    for k, suffix
    in (("config", "yaml"),
        ("nist", "json"),
        ("deps", "json"),
        ("outcome", "json"))}

TEST_OUTCOMES = {
    "default": "nothing",
    "deps:mixed0-nist:mixed-config:minimal": "no_fail",
    "deps:mixed1-nist:minimal-config:minimal": "no_fail",
    "deps:mixed0-nist:minimal-config:minimal": "no_fail",
    "deps:mixed1-nist:mixed-config:minimal": "fail"}
TEST_FAILURES = [
    "deps:mixed1-nist:mixed-config:minimal"
]


#
# *Parametrized integration test*
#

@pytest.mark.parametrize("config_name", TEST_DATA["config"].keys())
@pytest.mark.parametrize("nist_data_name", TEST_DATA["nist"].keys())
@pytest.mark.parametrize("deps_data_name", TEST_DATA["deps"].keys())
def test_integration(patches, config_name, nist_data_name, deps_data_name):
    test_name = f"{deps_data_name}-{nist_data_name}-{config_name}"
    should_fail = test_name in TEST_FAILURES
    outcome = TEST_OUTCOMES.get(test_name, TEST_OUTCOMES["default"])
    outcome_data = json.loads(
        TEST_DATA["outcome"].get(f"outcome:{outcome}").read_text())
    config = yaml.safe_load(TEST_DATA["config"][config_name].read_text())
    nist_data = TEST_DATA["nist"][nist_data_name].read_bytes()
    deps_data = json.loads(TEST_DATA["deps"][deps_data_name].read_text())
    patched = patches(
        "utils",
        ("ACVEChecker.nist_downloads",
         dict(new_callable=PropertyMock)),
        ("ACVEChecker.dependency_metadata",
         dict(new_callable=PropertyMock)),
        ("ACVEChecker.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.checker")

    def dep_items():
        return deps_data.items()

    async def nist_data_download():
        return gzip.compress(nist_data)

    def nist_downloads():
        download = AsyncMock()
        download.return_value.read = nist_data_download
        download.return_value.url = "NIST_URL"
        yield download()

    with patched as (m_utils, m_downloads, m_deps, m_log):
        m_utils.typed.return_value = config
        m_deps.return_value.items.side_effect = dep_items
        m_downloads.side_effect = nist_downloads
        checker = DummyCVEChecker("CONFIG_PATH")
        if config_name.startswith("config:bad_"):
            with pytest.raises(cve_scan.CVECheckError):
                assert checker.config
            return
        else:
            assert checker.config
        if should_fail:
            assert checker() == 1
        else:
            assert checker() == 0

    def get_logs_data():
        return {
            k: json.loads(
                json.dumps(
                    list(list(c)
                         for c
                         in getattr(
                             m_log.return_value,
                             k).call_args_list)))
            for k in ["error", "info", "notice", "warning"]}

    logs_data = get_logs_data()

    # Comment this out, but keep
    # It can be useful for both updating outcomes, and for
    # comparing actual outcomes to test expectations.
    #
    # OUTCOME_DIR = "/tmp/outcome"
    # outcome_path = f"{OUTCOME_DIR}/{test_name}.json"
    # pathlib.Path(outcome_path).write_text(
    #     json.dumps(logs_data, indent=4))

    assert logs_data == outcome_data
