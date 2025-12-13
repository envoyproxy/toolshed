
from unittest.mock import MagicMock, PropertyMock
import types

import pytest

import abstracts

from envoy.dependency import check


@abstracts.implementer(check.ADependencyCVE)
class DummyDependencyCVE:
    pass


def test_cve_constructor():
    cve = DummyDependencyCVE("CVE_DATA", "CPE_CLASS")
    assert cve.cve_data == "CVE_DATA"
    assert cve.cpe_class == "CPE_CLASS"


def test_cve_dunder_gt(patches):
    cve = DummyDependencyCVE("CVE_DATA", "CPE_CLASS")
    patched = patches(
        ("ADependencyCVE.id", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cve")

    with patched as (m_id, ):
        m_other = MagicMock()
        m_other.id = 7
        m_id.return_value = 23
        assert cve.__gt__(m_other)
        m_other.id = 23
        m_id.return_value = 7
        assert not cve.__gt__(m_other)


@pytest.mark.parametrize("data", ["description", "id", "severity"])
def test_cve_data(data):
    cve_data = MagicMock()
    cve = DummyDependencyCVE(cve_data, "CPE_CLASS")
    assert (
        getattr(cve, data)
        == cve_data.__getitem__.return_value)
    assert (
        cve_data.__getitem__.call_args
        == [(data, ), {}])
    assert data not in cve.__dict__


def test_cve_cpes(iters, patches):
    cve_data = MagicMock()
    cpe_class = MagicMock()
    cpes = iters(cb=lambda i: dict(CPE=f"CPE{i}"))
    cve_data.__getitem__.return_value = cpes
    cve = DummyDependencyCVE(cve_data, cpe_class)
    patched = patches(
        "set",
        prefix="envoy.dependency.check.abstract.cves.cve")

    with patched as (m_set, ):
        assert cve.cpes == m_set.return_value
        gen = m_set.call_args[0][0]
        assert isinstance(gen, types.GeneratorType)
        assert (
            list(gen)
            == [cpe_class.return_value] * len(cpes))

    assert (
        m_set.call_args
        == [(gen, ), {}])
    assert (
        cpe_class.call_args_list
        == [[(), cpe] for cpe in cpes])
    assert "cpes" in cve.__dict__


def test_cve_fail_template(patches):
    cve = DummyDependencyCVE("CVE_DATA", "CPE_CLASS")
    patched = patches(
        "jinja2",
        ("ADependencyCVE.fail_tpl", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cve")

    with patched as (m_jinja, m_tpl):
        assert cve.fail_template == m_jinja.Template.return_value

    assert (
        m_jinja.Template.call_args
        == [(m_tpl.return_value, ), {}])
    assert "fail_template" in cve.__dict__


def test_cve_fail_tpl(patches):
    cve = DummyDependencyCVE("CVE", "TRACKED_CPES")
    patched = patches(
        "CVE_FAIL_TPL",
        prefix="envoy.dependency.check.abstract.cves.cve")

    with patched as (m_tpl, ):
        assert cve.fail_tpl == m_tpl.lstrip.return_value

    assert "fail_tpl" not in cve.__dict__


def test_cve_formatted_description(iters, patches):
    cve = DummyDependencyCVE("CVE_DATA", "CPE_CLASS")
    patched = patches(
        "textwrap",
        ("ADependencyCVE.description", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cve")
    wrapped = iters(cb=lambda i: f"XX{i}")

    with patched as (m_wrap, m_description):
        m_wrap.wrap.return_value = wrapped
        assert (
            cve.formatted_description
            == "\n  ".join(wrapped))

    assert (
        m_wrap.wrap.call_args
        == [(m_description.return_value, ), {}])
    assert "formatted_description" not in cve.__dict__


def test_cve_last_modified_date(patches):
    cve = DummyDependencyCVE(MagicMock(), "CPE_CLASS")
    patched = patches(
        "ADependencyCVE.parse_cve_date",
        prefix="envoy.dependency.check.abstract.cves.cve")

    with patched as (m_date, ):
        assert cve.last_modified_date == m_date.return_value
    assert (
        m_date.call_args
        == [(cve.cve_data.__getitem__.return_value, ), {}])
    assert (
        cve.cve_data.__getitem__.call_args
        == [("last_modified_date", ), {}])
    assert "last_modified_date" not in cve.__dict__


def test_cve_published_date(patches):
    cve = DummyDependencyCVE(MagicMock(), "CPE_CLASS")
    patched = patches(
        "ADependencyCVE.parse_cve_date",
        prefix="envoy.dependency.check.abstract.cves.cve")

    with patched as (m_date, ):
        assert cve.published_date == m_date.return_value
    assert (
        m_date.call_args
        == [(cve.cve_data.__getitem__.return_value, ), {}])
    assert (
        cve.cve_data.__getitem__.call_args
        == [("published_date", ), {}])
    assert "published_date" not in cve.__dict__


def test_cve_score(patches):
    cve = DummyDependencyCVE(MagicMock(), "CPE_CLASS")
    patched = patches(
        "float",
        prefix="envoy.dependency.check.abstract.cves.cve")

    with patched as (m_float, ):
        assert cve.score == m_float.return_value
    assert (
        m_float.call_args
        == [(cve.cve_data.__getitem__.return_value, ), {}])
    assert (
        cve.cve_data.__getitem__.call_args
        == [("score", ), {}])
    assert "score" not in cve.__dict__


def test_cve_format_failure(patches):
    cve = DummyDependencyCVE("CVE_DATA", "CPE_CLASS")
    patched = patches(
        ("ADependencyCVE.fail_template", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.cves.cve")
    dependency = MagicMock()

    with patched as (m_template, ):
        assert (
            cve.format_failure(dependency)
            == m_template.return_value.render.return_value)

    assert (
        m_template.return_value.render.call_args
        == [(), {'cve': cve, 'dependency': dependency}])


@pytest.mark.parametrize("is_utc", [True, False])
def test_cve_parse_cve_date(patches, is_utc):
    cve = DummyDependencyCVE("CVE_DATA", "CPE_CLASS")
    patched = patches(
        "date",
        prefix="envoy.dependency.check.abstract.cves.cve")
    date_str = MagicMock()
    date_str.endswith.return_value = is_utc

    with patched as (m_date, ):
        if not is_utc:
            with pytest.raises(check.exceptions.CVEError) as e:
                cve.parse_cve_date(date_str)
            assert not m_date.fromisoformat.called
            assert (
                e.value.args[0]
                == 'CVE dates should be UTC and in isoformat')
            return
        assert (
            cve.parse_cve_date(date_str)
            == m_date.fromisoformat.return_value)

    assert (
        m_date.fromisoformat.call_args
        == [(date_str.split.return_value.__getitem__.return_value,), {}])
    assert (
        date_str.split.call_args
        == [("T", ), {}])
    assert (
        date_str.split.return_value.__getitem__.call_args
        == [(0, ), {}])
