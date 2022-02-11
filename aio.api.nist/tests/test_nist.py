
import pytest

from aio.api import nist


def test_nist_matcher_constructor(patches):
    patched = patches(
        "nist.ACVEMatcher.__init__",
        prefix="aio.api.nist.nist")

    with patched as (m_super, ):
        m_super.return_value = None
        matcher = nist.CVEMatcher("CPE_MATCH")

    assert isinstance(matcher, nist.ACVEMatcher)
    assert (
        m_super.call_args
        == [("CPE_MATCH", ), {}])


def test_nist_cpe_constructor(patches):
    patched = patches(
        "nist.ACPE.__init__",
        prefix="aio.api.nist.nist")

    with patched as (m_super, ):
        m_super.return_value = None
        cpe = nist.CPE()

    assert isinstance(cpe, nist.ACPE)
    assert (
        m_super.call_args
        == [(), {}])


def test_nist_cve_constructor(patches):
    patched = patches(
        "nist.ACVE.__init__",
        prefix="aio.api.nist.nist")

    with patched as (m_super, ):
        m_super.return_value = None
        cve = nist.CVE("CVE_DATA", "TRACKED CPES")

    assert isinstance(cve, nist.ACVE)
    assert (
        m_super.call_args
        == [("CVE_DATA", "TRACKED CPES"), {}])


@pytest.mark.parametrize("ignored_cves", [None, (), ["IGNORED"]])
def test_downloader_constructor(patches, ignored_cves):
    patched = patches(
        "nist.ANISTDownloader.__init__",
        prefix="aio.api.nist.nist")
    kwargs = (
        dict(ignored_cves=ignored_cves)
        if ignored_cves is not None
        else {})

    with patched as (m_super, ):
        m_super.return_value = None
        downloader = nist.NISTDownloader("URLS", **kwargs)

    assert isinstance(downloader, nist.ANISTDownloader)
    assert (
        m_super.call_args
        == [("URLS", ), kwargs])
    assert downloader.parser_class == nist.NISTParser
    assert "parser_class" not in downloader.__dict__


@pytest.mark.parametrize("ignored_cves", [None, (), ["IGNORED"]])
def test_parser_constructor(patches, ignored_cves):
    patched = patches(
        "nist.ANISTParser.__init__",
        prefix="aio.api.nist.nist")
    kwargs = (
        dict(ignored_cves=ignored_cves)
        if ignored_cves is not None
        else {})

    with patched as (m_super, ):
        m_super.return_value = None
        parser = nist.NISTParser("URLS", **kwargs)

    assert isinstance(parser, nist.ANISTParser)
    assert (
        m_super.call_args
        == [("URLS", ), kwargs])
    assert parser.cve_class == nist.CVE
    assert "cve_class" not in parser.__dict__
    assert parser.cpe_class == nist.CPE
    assert "cpe_class" not in parser.__dict__
    assert parser.matcher_class == nist.CVEMatcher
    assert "matcher_class" not in parser.__dict__
