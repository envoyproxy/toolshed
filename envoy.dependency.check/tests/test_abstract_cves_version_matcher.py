
from unittest.mock import MagicMock, PropertyMock

import pytest

import abstracts

from envoy.dependency import check


@abstracts.implementer(check.ADependencyCVEVersionMatcher)
class DummyDependencyCVEVersionMatcher:
    pass


def test_matcher_constructor():
    matcher = DummyDependencyCVEVersionMatcher("CPE_MATCH")
    assert matcher._cpe_match == "CPE_MATCH"


@pytest.mark.parametrize("release_version", [None, 0, 7, 23])
@pytest.mark.parametrize("end_exc", [None, 0, 7, 23])
@pytest.mark.parametrize("end_inc", [None, 0, 7, 23])
@pytest.mark.parametrize("start_exc", [None, 0, 7, 23])
@pytest.mark.parametrize("start_inc", [None, 0, 7, 23])
def test_matcher_dunder_call(
        patches, release_version, end_exc, end_inc, start_exc, start_inc):
    matcher = DummyDependencyCVEVersionMatcher("CPE_MATCH")
    patched = patches(
        ("ADependencyCVEVersionMatcher.version_info",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.version_matcher")
    dependency = MagicMock()
    dependency.release_version = release_version
    expected = True

    if release_version:
        if end_exc is not None and release_version >= end_exc:
            expected = False
        elif end_inc is not None and release_version > end_inc:
            expected = False
        elif start_exc is not None and release_version <= start_exc:
            expected = False
        elif start_inc is not None and release_version < start_inc:
            expected = False

    version_dict = dict(
        end_exc=end_exc,
        end_inc=end_inc,
        start_exc=start_exc,
        start_inc=start_inc)

    with patched as (m_version, ):
        m_version.return_value.__getitem__.side_effect = (
            lambda k: version_dict[k])
        assert matcher(dependency) == expected


def test_matcher_version_info(patches):
    matcher = DummyDependencyCVEVersionMatcher("CPE_MATCH")
    patched = patches(
        "ADependencyCVEVersionMatcher._cpe_version",
        prefix="envoy.dependency.check.abstract.cves.version_matcher")

    version_dict = dict(
        end_exc="END_EXC",
        end_inc="END_INC",
        start_exc="START_EXC",
        start_inc="START_INC")

    with patched as (m_cpe_version, ):
        m_cpe_version.side_effect = lambda k1, k2: version_dict[f"{k1}_{k2}"]
        assert (
            matcher.version_info
            == version_dict)

    assert "version_info" in matcher.__dict__


@pytest.mark.parametrize("version_info", [None, 0, 23])
def test_matcher__cpe_version(patches, version_info):
    cpe_match = MagicMock()
    matcher = DummyDependencyCVEVersionMatcher(cpe_match)
    patched = patches(
        "version",
        "utils",
        prefix="envoy.dependency.check.abstract.cves.version_matcher")

    with patched as (m_version, m_utils):
        cpe_match.get.return_value = version_info
        assert (
            matcher._cpe_version("action", "ending")
            == (m_version.Version.return_value
                if version_info is not None
                else None))

    assert (
        cpe_match.get.call_args
        == [("versionActionEndingluding", None), {}])
    if version_info is None:
        assert not m_version.Version.called
        assert not m_utils.typed.called
        return
    assert (
        m_version.Version.call_args
        == [(m_utils.typed.return_value, ), {}])
    assert (
        m_utils.typed.call_args
        == [(str, cpe_match.get.return_value), {}])
