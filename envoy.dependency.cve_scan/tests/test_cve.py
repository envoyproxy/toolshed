
from unittest.mock import MagicMock, PropertyMock

import pytest

import abstracts

from envoy.dependency.cve_scan import ACVE, CVEError


@abstracts.implementer(ACVE)
class DummyCVE:

    @property
    def cpe_class(self):
        return super().cpe_class

    @property
    def version_matcher_class(self):
        return super().version_matcher_class


def test_cve_constructor():

    with pytest.raises(TypeError):
        ACVE()

    cve = DummyCVE("CVE", "TRACKED_CPES")
    assert cve.cve_data == "CVE"
    assert cve.tracked_cpes == "TRACKED_CPES"

    with pytest.raises(NotImplementedError):
        cve.cpe_class

    with pytest.raises(NotImplementedError):
        cve.version_matcher_class


def test_cve_dunder_gt(patches):
    cve = DummyCVE("CVE", "TRACKED_CPES")
    patched = patches(
        ("ACVE.id", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.cve")

    with patched as (m_id, ):
        m_other = MagicMock()
        m_other.id = 7
        m_id.return_value = 23
        assert cve.__gt__(m_other)
        m_other.id = 23
        m_id.return_value = 7
        assert not cve.__gt__(m_other)


def test_cve_cpes(patches):
    cve = DummyCVE("CVE", "TRACKED_CPES")
    patched = patches(
        "set",
        ("ACVE.nodes", dict(new_callable=PropertyMock)),
        "ACVE.gather_cpes",
        prefix="envoy.dependency.cve_scan.abstract.cve")

    with patched as (m_set, m_nodes, m_gather):
        assert cve.cpes == m_set.return_value

    assert (
        list(m_gather.call_args)
        == [(m_nodes.return_value, m_set.return_value), {}])
    assert "cpes" in cve.__dict__


def test_cve_fail_template(patches):
    cve = DummyCVE("CVE", "TRACKED_CPES")
    patched = patches(
        "jinja2",
        ("ACVE.fail_tpl", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.cve")

    with patched as (m_jinja, m_tpl):
        assert cve.fail_template == m_jinja.Template.return_value

    assert (
        list(m_jinja.Template.call_args)
        == [(m_tpl.return_value, ), {}])
    assert "fail_template" in cve.__dict__


def test_cve_fail_tpl(patches):
    cve = DummyCVE("CVE", "TRACKED_CPES")
    patched = patches(
        "CVE_FAIL_TPL",
        prefix="envoy.dependency.cve_scan.abstract.cve")

    with patched as (m_tpl, ):
        assert cve.fail_tpl == m_tpl.lstrip.return_value

    assert "fail_tpl" not in cve.__dict__


def test_cve_formatted_description(patches):
    cve = DummyCVE("CVE", "TRACKED_CPES")
    patched = patches(
        "textwrap",
        ("ACVE.description", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.cve")
    wrapped = [f"XX{i}" for i in range(0, 5)]

    with patched as (m_wrap, m_description):
        m_wrap.wrap.return_value = wrapped
        assert (
            cve.formatted_description
            == "\n  ".join(wrapped))

    assert (
        list(m_wrap.wrap.call_args)
        == [(m_description.return_value, ), {}])
    assert "formatted_description" not in cve.__dict__


def test_cve_description():
    cve = DummyCVE(MagicMock(), "TRACKED_CPES")
    assert (
        cve.description
        == (cve.cve_data.__getitem__.return_value
                        .__getitem__.return_value
                        .__getitem__.return_value
                        .__getitem__.return_value
                        .__getitem__.return_value))
    assert (
        list(cve.cve_data.__getitem__.call_args)
        == [("cve", ), {}])
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__getitem__.call_args)
        == [("description", ), {}])
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__getitem__.return_value
                         .__getitem__.call_args)
        == [("description_data", ), {}])
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__getitem__.return_value
                         .__getitem__.return_value
                         .__getitem__.call_args)
        == [(0, ), {}])
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__getitem__.return_value
                         .__getitem__.return_value
                         .__getitem__.return_value
                         .__getitem__.call_args)
        == [("value", ), {}])
    assert "description" not in cve.__dict__


def test_cve_id():
    cve = DummyCVE(MagicMock(), "TRACKED_CPES")
    assert (
        cve.id
        == (cve.cve_data.__getitem__.return_value
                        .__getitem__.return_value
                        .__getitem__.return_value))
    assert (
        list(cve.cve_data.__getitem__.call_args)
        == [("cve", ), {}])
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__getitem__.call_args)
        == [("CVE_data_meta", ), {}])
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__getitem__.return_value
                         .__getitem__.call_args)
        == [("ID", ), {}])
    assert "id" not in cve.__dict__


def test_cve_is_v3():
    cve = DummyCVE(MagicMock(), "TRACKED_CPES")
    assert (
        cve.is_v3
        == (cve.cve_data.__getitem__.return_value.__contains__.return_value))
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__contains__.call_args)
        == [("baseMetricV3", ), {}])
    assert "is_v3" not in cve.__dict__


def test_cve_last_modified_date(patches):
    cve = DummyCVE(MagicMock(), "TRACKED_CPES")
    patched = patches(
        "ACVE.parse_cve_date",
        prefix="envoy.dependency.cve_scan.abstract.cve")

    with patched as (m_date, ):
        assert cve.last_modified_date == m_date.return_value
    assert (
        list(m_date.call_args)
        == [(cve.cve_data.__getitem__.return_value, ), {}])
    assert (
        list(cve.cve_data.__getitem__.call_args)
        == [("lastModifiedDate", ), {}])
    assert "last_modified_date" not in cve.__dict__


def test_cve_nodes():
    cve = DummyCVE(MagicMock(), "TRACKED_CPES")
    assert (
        cve.nodes
        == (cve.cve_data.__getitem__.return_value
                        .__getitem__.return_value))
    assert (
        list(cve.cve_data.__getitem__.call_args)
        == [("configurations", ), {}])
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__getitem__.call_args)
        == [("nodes", ), {}])
    assert "nodes" not in cve.__dict__


def test_cve_published_date(patches):
    cve = DummyCVE(MagicMock(), "TRACKED_CPES")
    patched = patches(
        "ACVE.parse_cve_date",
        prefix="envoy.dependency.cve_scan.abstract.cve")

    with patched as (m_date, ):
        assert cve.published_date == m_date.return_value
    assert (
        list(m_date.call_args)
        == [(cve.cve_data.__getitem__.return_value, ), {}])
    assert (
        list(cve.cve_data.__getitem__.call_args)
        == [("publishedDate", ), {}])
    assert "published_date" not in cve.__dict__


def test_cve_score():
    cve = DummyCVE(MagicMock(), "TRACKED_CPES")
    assert (
        cve.score
        == (cve.cve_data.__getitem__.return_value
                        .__getitem__.return_value
                        .__getitem__.return_value
                        .__getitem__.return_value))
    assert (
        list(cve.cve_data.__getitem__.call_args)
        == [("impact", ), {}])
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__getitem__.call_args)
        == [("baseMetricV3", ), {}])
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__getitem__.return_value
                         .__getitem__.call_args)
        == [("cvssV3", ), {}])
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__getitem__.return_value
                         .__getitem__.return_value
                         .__getitem__.call_args)
        == [("baseScore", ), {}])
    assert "score" not in cve.__dict__


def test_cve_severity():
    cve = DummyCVE(MagicMock(), "TRACKED_CPES")
    assert (
        cve.severity
        == (cve.cve_data.__getitem__.return_value
                        .__getitem__.return_value
                        .__getitem__.return_value
                        .__getitem__.return_value))
    assert (
        list(cve.cve_data.__getitem__.call_args)
        == [("impact", ), {}])
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__getitem__.call_args)
        == [("baseMetricV3", ), {}])
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__getitem__.return_value
                         .__getitem__.call_args)
        == [("cvssV3", ), {}])
    assert (
        list(cve.cve_data.__getitem__.return_value
                         .__getitem__.return_value
                         .__getitem__.return_value
                         .__getitem__.call_args)
        == [("baseSeverity", ), {}])
    assert "severity" not in cve.__dict__


@pytest.mark.parametrize(
    "matches",
    [[],
     [False] * 5,
     [False, True, False, False, False],
     [False, False, True, False, True],
     [False, "*", True, False, True],
     [False, "*", False, False, False]])
def test_cve_dependency_match(patches, matches):
    cve = DummyCVE("CVE", "TRACKED CPES")
    patched = patches(
        ("ACVE.cpes",
         dict(new_callable=PropertyMock)),
        "ACVE.wildcard_version_match",
        prefix="envoy.dependency.cve_scan.abstract.cve")
    dep = MagicMock()
    cpes = []
    for cpe_match in matches:
        cpe = MagicMock()
        cpe.dependency_match.return_value = cpe_match
        cpe.version = cpe_match
        cpes.append(cpe)

    expected = []
    for cpe_match in matches:
        expected.append(cpe_match)
        if cpe_match:
            break

    with patched as (m_cpes, m_match):
        m_cpes.return_value = cpes
        if not expected or expected[-1] is False:
            assert not cve.dependency_match(dep)
        else:
            assert (
                cve.dependency_match(dep)
                == (m_match.return_value
                    if expected[-1] == "*"
                    else True))

    if expected and expected[-1] == "*":
        assert (
            list(list(c) for c in m_match.call_args_list)
            == [[(dep, ), {}]])
    else:
        assert not m_match.called

    for i, cpe in enumerate(cpes):
        if i == 0:
            previous_result = False
        else:
            try:
                previous_result = expected[i - 1]
            except IndexError:
                previous_result = True
        if not previous_result:
            assert (
                list(cpe.dependency_match.call_args)
                == [(dep,), {}])
        else:
            assert not cpe.dependency_match.called


def test_cve_format_failure(patches):
    cve = DummyCVE("CVE", "TRACKED_CPES")
    patched = patches(
        ("ACVE.fail_template", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.cve")
    dependency = MagicMock()

    with patched as (m_template, ):
        assert (
            cve.format_failure(dependency)
            == m_template.return_value.render.return_value)

    assert (
        list(m_template.return_value.render.call_args)
        == [(), {'cve': cve, 'dependency': dependency}])


@pytest.mark.parametrize("include", ["odd", "even"])
def test_cve_gather_cpes(patches, include):
    cve = DummyCVE("CVE", "TRACKED_CPES")
    patched = patches(
        ("ACVE.cpe_class", dict(new_callable=PropertyMock)),
        "ACVE.include_version",
        prefix="envoy.dependency.cve_scan.abstract.cve")
    nodes = [
        dict(),
        dict(
            children=[],
            cpe_match=[]),
        dict(
            children=[],
            cpe_match=[dict(cpe23Uri="URI0", data="DATA0")]),
        dict(
            children=[],
            cpe_match=[
                dict(cpe23Uri="URI1", data="DATA1"),
                dict(cpe23Uri="URI2", data="DATA2")]),
        dict(
            children=[
                dict(
                    cpe_match=[
                        dict(cpe23Uri="URIa3", data="DATAa3"),
                        dict(cpe23Uri="URIa4", data="DATAa4")])],
            cpe_match=[
                dict(cpe23Uri="URI3", data="DATA3"),
                dict(cpe23Uri="URI4", data="DATA4")]),
        dict(
            children=[
                dict(
                    cpe_match=[
                        dict(cpe23Uri="URIa5", data="DATAa5"),
                        dict(cpe23Uri="URIa6", data="DATAa6")],
                    children=[
                        dict(
                            cpe_match=[
                                dict(cpe23Uri="URIab5", data="DATAab5"),
                                dict(cpe23Uri="URIab6", data="DATAab6")])])])]
    cpe_set = MagicMock()

    def include_cpe(cpe_match, obj):
        is_even = bool(int(cpe_match["data"][-1]) % 2)
        return (
            is_even
            if include == "even"
            else not is_even)

    with patched as (m_class, m_include):
        m_include.side_effect = include_cpe
        assert not cve.gather_cpes(nodes, cpe_set)

    assert (
        list(list(c) for c in m_class.return_value.from_string.call_args_list)
        == [[('URI0',), {}],
            [('URI1',), {}], [('URI2',), {}],
            [('URI3',), {}], [('URI4',), {}],
            [('URIa3',), {}], [('URIa4',), {}],
            [('URIa5',), {}], [('URIa6',), {}],
            [('URIab5',), {}], [('URIab6',), {}]])
    cpe_obj = m_class.return_value.from_string.return_value
    assert (
        list(list(c) for c in m_include.call_args_list)
        == [[({'data': 'DATA0'}, cpe_obj), {}],
            [({'data': 'DATA1'}, cpe_obj), {}],
            [({'data': 'DATA2'}, cpe_obj), {}],
            [({'data': 'DATA3'}, cpe_obj), {}],
            [({'data': 'DATA4'}, cpe_obj), {}],
            [({'data': 'DATAa3'}, cpe_obj), {}],
            [({'data': 'DATAa4'}, cpe_obj), {}],
            [({'data': 'DATAa5'}, cpe_obj), {}],
            [({'data': 'DATAa6'}, cpe_obj), {}],
            [({'data': 'DATAab5'}, cpe_obj), {}],
            [({'data': 'DATAab6'}, cpe_obj), {}]])
    expected_cpe_count = (
        6
        if include == "odd"
        else 5)
    assert (
        list(list(c) for c in cpe_set.add.call_args_list)
        == [[(cpe_obj,), {}]] * expected_cpe_count)


@pytest.mark.parametrize("tracked", [True, False])
@pytest.mark.parametrize("matches", [True, False])
def test_cve_include_version(patches, tracked, matches):
    tracked_cpes = MagicMock()
    tracked_cpes.__contains__.return_value = tracked
    cve = DummyCVE("CVE", tracked_cpes)
    patched = patches(
        ("ACVE.version_matcher_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.cve")
    cpe_match = MagicMock()
    cpe = MagicMock()

    with patched as (m_matcher, ):
        m_matcher.return_value.return_value.return_value = matches
        assert (
            cve.include_version(cpe_match, cpe)
            == (tracked and matches))

    assert (
        list(tracked_cpes.__contains__.call_args)
        == [(str(cpe),), {}])
    if not tracked:
        assert not m_matcher.called
        return
    assert (
        list(m_matcher.return_value.call_args)
        == [(cpe_match,), {}])
    assert (
        list(m_matcher.return_value.return_value.call_args)
        == [(tracked_cpes.__getitem__.return_value,), {}])
    assert (
        list(tracked_cpes.__getitem__.call_args)
        == [(str(cpe),), {}])


@pytest.mark.parametrize("is_utc", [True, False])
def test_cve_parse_cve_date(patches, is_utc):
    cve = DummyCVE("CVE", "TRACKED CPES")
    patched = patches(
        "date",
        prefix="envoy.dependency.cve_scan.abstract.cve")
    date_str = MagicMock()
    date_str.endswith.return_value = is_utc

    with patched as (m_date, ):
        if not is_utc:
            with pytest.raises(CVEError) as e:
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
        list(m_date.fromisoformat.call_args)
        == [(date_str.split.return_value.__getitem__.return_value,), {}])
    assert (
        list(date_str.split.call_args)
        == [("T", ), {}])
    assert (
        list(date_str.split.return_value.__getitem__.call_args)
        == [(0, ), {}])


@pytest.mark.parametrize("release_date", [0, 7, 23])
@pytest.mark.parametrize("published_date", [0, 7, 23])
def test_cve_wildcard_version_match(patches, release_date, published_date):
    cve = DummyCVE("CVE", "TRACKED CPES")
    patched = patches(
        "date",
        ("ACVE.published_date",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.cve")
    dep = MagicMock()

    with patched as (m_date, m_published):
        m_date.fromisoformat.return_value = release_date
        m_published.return_value = published_date
        assert (
            cve.wildcard_version_match(dep)
            == (release_date <= published_date))

    assert (
        list(m_date.fromisoformat.call_args)
        == [(dep.release_date, ), {}])
