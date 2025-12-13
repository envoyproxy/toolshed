
from unittest.mock import MagicMock, PropertyMock

import pytest

import abstracts

from aio.api import nist


@abstracts.implementer(nist.ACVEMatcher)
class DummyCVEMatcher:
    pass


def test_matcher_constructor():
    matcher = DummyCVEMatcher("FILTER_DICT")
    assert matcher._filter_dict == "FILTER_DICT"


@pytest.mark.parametrize("matched", [True, False])
def test_matcher_dunder_call(patches, matched):
    matcher = DummyCVEMatcher("FILTER_DICT")
    patched = patches(
        "logger",
        "ACVEMatcher.match_cpe",
        "ACVEMatcher._match_debug",
        prefix="aio.api.nist.abstract.matcher")

    with patched as (m_log, m_match, m_debug):
        m_match.return_value = matched
        assert (
            matcher("CVE", "CPE", "CPE_MATCH")
            == matched)

    assert (
        m_match.call_args
        == [("CVE", "CPE", "CPE_MATCH"), {}])
    if matched:
        assert (
            m_log.debug.call_args
            == [(f"Matched\n  {m_debug.return_value}", ), {}])
    else:
        assert (
            m_log.debug.call_args
            == [(f"No match\n  {m_debug.return_value}", ), {}])
    assert (
        m_debug.call_args
        == [("CVE", "CPE", "CPE_MATCH"), {}])


def test_matcher_dunder_str(patches):
    matcher = DummyCVEMatcher("FILTER_DICT")
    patched = patches(
        "str",
        ("ACVEMatcher.tracked_cpe",
         dict(new_callable=PropertyMock)),
        ("ACVEMatcher.tracked_date",
         dict(new_callable=PropertyMock)),
        ("ACVEMatcher.tracked_version",
         dict(new_callable=PropertyMock)),
        "ACVEMatcher._truncate_cpe",
        prefix="aio.api.nist.abstract.matcher")

    with patched as (m_str, m_cpe, m_date, m_version, m_trunc):
        m_trunc.return_value = "TRUNCATED"
        m_str.return_value = "STR"
        assert (
            matcher.__str__()
            == "/".join([
                "TRUNCATED",
                "STR",
                "STR"]))

    assert (
        m_trunc.call_args
        == [(m_cpe.return_value, ), {}])
    assert (
        m_str.call_args_list
        == [[(m_date.return_value, ), {}],
            [(m_version.return_value, ), {}]])


def test_matcher_tracked_cpe():
    filter_dict = MagicMock()
    matcher = DummyCVEMatcher(filter_dict)
    assert (
        matcher.tracked_cpe
        == filter_dict.__getitem__.return_value)
    assert (
        filter_dict.__getitem__.call_args
        == [("cpe", ), {}])
    assert "tracked_cpe" not in matcher.__dict__


def test_matcher_tracked_date():
    filter_dict = MagicMock()
    matcher = DummyCVEMatcher(filter_dict)
    assert (
        matcher.tracked_date
        == filter_dict.__getitem__.return_value)
    assert (
        filter_dict.__getitem__.call_args
        == [("date", ), {}])
    assert "tracked_date" not in matcher.__dict__


def test_matcher_tracked_version():
    filter_dict = MagicMock()
    matcher = DummyCVEMatcher(filter_dict)
    assert (
        matcher.tracked_version
        == filter_dict.get.return_value)
    assert (
        filter_dict.get.call_args
        == [("version", ), {}])
    assert "tracked_version" not in matcher.__dict__


def test_matcher_get_version_info(patches):
    matcher = DummyCVEMatcher("FILTER_DICT")
    patched = patches(
        "ACVEMatcher._cpe_version",
        prefix="aio.api.nist.abstract.matcher")
    cpe = MagicMock()

    version_dict = dict(
        end_exc="END_EXC",
        end_inc="END_INC",
        start_exc="START_EXC",
        start_inc="START_INC")

    with patched as (m_cpe_version, ):
        m_cpe_version.side_effect = (
            lambda c, k1, k2: version_dict[f"{k1}_{k2}"])
        assert (
            matcher.get_version_info(cpe)
            == version_dict)


@pytest.mark.parametrize("date", [True, False])
@pytest.mark.parametrize("parts", [True, False])
@pytest.mark.parametrize("version", [True, False])
def test_matcher_match_cpe(patches, date, parts, version):
    matcher = DummyCVEMatcher("FILTER_DICT")
    patched = patches(
        "ACVEMatcher.match_date",
        "ACVEMatcher.match_parts",
        "ACVEMatcher.match_version",
        prefix="aio.api.nist.abstract.matcher")
    cve = MagicMock()
    cpe = MagicMock()
    cpe_match = MagicMock()

    with patched as (m_date, m_parts, m_version):
        m_date.return_value = date
        m_parts.return_value = parts
        m_version.return_value = version
        assert (
            matcher.match_cpe(cve, cpe, cpe_match)
            == (date and parts and version))

    assert (
        m_date.call_args
        == [(cve, cpe, cpe_match), {}])
    if not date:
        assert not m_parts.called
        assert not m_version.called
        return
    assert (
        m_parts.call_args
        == [(cve, cpe, cpe_match), {}])
    if not parts:
        assert not m_version.called
        return
    assert (
        m_version.call_args
        == [(cve, cpe, cpe_match), {}])


@pytest.mark.parametrize("tracked_date", [None, *range(0, 5)])
@pytest.mark.parametrize("published_date", [*range(0, 5)])
@pytest.mark.parametrize("version", [None, "", "OTHER", "*"])
def test_matcher_match_date(patches, tracked_date, published_date, version):
    matcher = DummyCVEMatcher("FILTER_DICT")
    patched = patches(
        ("ACVEMatcher.tracked_date",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.matcher")
    cve = MagicMock()
    cve.published_date = published_date
    cpe = MagicMock()
    cpe.version = version
    cpe_match = MagicMock()
    matches = True
    if tracked_date:
        if version == "*":
            if published_date < tracked_date:
                matches = False

    with patched as (m_date, ):
        m_date.return_value = tracked_date
        assert (
            matcher.match_date(cve, cpe, cpe_match)
            == matches)


@pytest.mark.parametrize("part", [None, "", "OTHER", "*", "PART"])
@pytest.mark.parametrize("vendor", [None, "", "OTHER", "*", "VENDOR"])
@pytest.mark.parametrize("product", [None, "", "OTHER", "*", "PRODUCT"])
def test_matcher_match_parts(patches, part, vendor, product):
    matcher = DummyCVEMatcher("FILTER_DICT")
    patched = patches(
        ("ACVEMatcher.tracked_cpe",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.matcher")
    cve = MagicMock()
    cpe = MagicMock()
    cpe.part = "PART"
    cpe.product = "PRODUCT"
    cpe.vendor = "VENDOR"
    cpe_match = MagicMock()
    tracked = MagicMock()
    tracked.product = product
    tracked.part = part
    tracked.vendor = vendor
    matches = False
    if part == "PART":
        if vendor == "VENDOR":
            if product in ["*", "PRODUCT"]:
                matches = True

    with patched as (m_tracked, ):
        m_tracked.return_value = tracked
        assert (
            matcher.match_parts(cve, cpe, cpe_match)
            == matches)


@pytest.mark.parametrize("version", [None, 0, 7, 23])
@pytest.mark.parametrize("end_exc", [None, 0, 7, 23])
@pytest.mark.parametrize("end_inc", [None, 0, 7, 23])
@pytest.mark.parametrize("start_exc", [None, 0, 7, 23])
@pytest.mark.parametrize("start_inc", [None, 0, 7, 23])
def test_matcher_match_version(
        patches, version, end_exc, end_inc, start_exc, start_inc):
    matcher = DummyCVEMatcher("FILTER_DICT")
    patched = patches(
        ("ACVEMatcher.tracked_version",
         dict(new_callable=PropertyMock)),
        "ACVEMatcher.get_version_info",
        prefix="aio.api.nist.abstract.matcher")
    expected = True

    if version:
        if end_exc is not None and version >= end_exc:
            expected = False
        elif end_inc is not None and version > end_inc:
            expected = False
        elif start_exc is not None and version <= start_exc:
            expected = False
        elif start_inc is not None and version < start_inc:
            expected = False

    version_dict = dict(
        end_exc=end_exc,
        end_inc=end_inc,
        start_exc=start_exc,
        start_inc=start_inc)

    with patched as (m_tracked, m_version):
        m_tracked.return_value = version
        m_version.return_value.__getitem__.side_effect = (
            lambda k: version_dict[k])
        assert (
            matcher.match_version("CVE", "CPE", "CPE_MATCH")
            == expected)

    if not version:
        assert not m_version.called
        return
    assert (
        m_version.call_args
        == [("CPE_MATCH", ), {}])


@pytest.mark.parametrize("version_info", [None, 0, 23])
def test_matcher__cpe_version(patches, version_info):
    matcher = DummyCVEMatcher("FILTER_DICT")
    patched = patches(
        "version",
        "utils",
        prefix="aio.api.nist.abstract.matcher")
    cpe_match = MagicMock()

    with patched as (m_version, m_utils):
        cpe_match.get.return_value = version_info
        assert (
            matcher._cpe_version(cpe_match, "action", "ending")
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


def test_matcher__match_debug(patches):
    matcher = DummyCVEMatcher("FILTER_DICT")
    patched = patches(
        "str",
        "ACVEMatcher.__str__",
        "ACVEMatcher._truncate_cpe",
        prefix="aio.api.nist.abstract.matcher")
    cve = MagicMock()
    cve.id = "ID"
    cpe = MagicMock()
    cpe_match = MagicMock()
    match_info = "/".join([
        "ID",
        "TRUNCATED",
        "STR",
        "STR"])

    with patched as (m_str, m_self, m_trunc):
        m_trunc.return_value = "TRUNCATED"
        m_str.return_value = "STR"
        m_self.return_value = "SELF"
        assert (
            matcher._match_debug(cve, cpe, cpe_match)
            == f"SELF\n  -> {match_info}")

    assert (
        m_trunc.call_args
        == [(cpe, ), {}])
    assert (
        m_trunc.call_args
        == [(cpe, ), {}])
    assert (
        m_str.call_args_list
        == [[(cve.published_date, ), {}],
            [(cpe_match, ), {}]])


def test_matcher__truncate_cpe(patches):
    matcher = DummyCVEMatcher("FILTER_DICT")
    patched = patches(
        "str",
        prefix="aio.api.nist.abstract.matcher")
    cpe = MagicMock()

    with patched as (m_str, ):
        assert (
            matcher._truncate_cpe(cpe)
            == m_str.return_value.split.return_value.__getitem__.return_value)

    assert (
        m_str.call_args
        == [(cpe, ), {}])
    assert (
        m_str.return_value.split.call_args
        == [(":", 2), {}])
    assert (
        m_str.return_value.split.return_value.__getitem__.call_args
        == [(2, ), {}])
