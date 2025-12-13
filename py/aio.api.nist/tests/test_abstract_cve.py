

from unittest.mock import MagicMock, PropertyMock

import pytest

import abstracts

from aio.api import nist


@abstracts.implementer(nist.ACVE)
class DummyCVE:
    pass


def test_cve_parse_date(patches):
    patched = patches(
        "date",
        prefix="aio.api.nist.abstract.cve")
    date_str = MagicMock()

    with patched as (m_date, ):
        assert (
            nist.CVE.parse_date(date_str)
            == m_date.fromisoformat.return_value)

    assert (
        m_date.fromisoformat.call_args
        == [(date_str.split.return_value.__getitem__.return_value, ),
            {}])
    assert (
        date_str.split.call_args
        == [("T", ), {}])
    assert (
        date_str.split.return_value.__getitem__.call_args
        == [(0, ), {}])


def test_cve_constructor():
    cve = DummyCVE("CVE", "TRACKED_CPES", "CPE_CLASS")
    assert cve.cve_data == "CVE"
    assert cve.tracked_cpes == "TRACKED_CPES"
    assert cve.cpe_class == "CPE_CLASS"


def test_cve_cpes(patches):
    cve = DummyCVE("CVE", "TRACKED_CPES", "CPE_CLASS")
    patched = patches(
        "set",
        ("ACVE.nodes", dict(new_callable=PropertyMock)),
        "ACVE.gather_cpes",
        prefix="aio.api.nist.abstract.cve")

    with patched as (m_set, m_nodes, m_gather):
        assert cve.cpes == m_set.return_value

    assert (
        m_gather.call_args
        == [(m_nodes.return_value, m_set.return_value), {}])
    assert "cpes" in cve.__dict__


def test_cve_cve_dict(iters, patches):
    cve_data = iters(dict)
    cve = DummyCVE(cve_data, "TRACKED_CPES", "CPE_CLASS")
    patched = patches(
        ("ACVE.cpes", dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.cve")
    cpes = iters(cb=lambda i: MagicMock())
    expected = dict(**cve_data)
    expected.update(
        **dict(cpes=tuple(
            dict(vendor=c.vendor,
                 part=c.part,
                 product=c.product,
                 version=c.version)
            for c in cpes)))

    with patched as (m_cpes, ):
        m_cpes.return_value = cpes
        assert (
            cve.cve_dict
            == expected)

    assert "cve_dict" in cve.__dict__


def test_cve_id():
    cve_data = MagicMock()
    cve = DummyCVE(cve_data, "TRACKED_CPES", "CPE_CLASS")
    assert cve.id == cve_data.__getitem__.return_value
    assert (
        cve_data.__getitem__.call_args
        == [("id", ), {}])
    assert "id" not in cve.__dict__


def test_cve_nodes():
    cve = DummyCVE(MagicMock(), "TRACKED_CPES", "CPE_CLASS")
    assert (
        cve.nodes
        == cve.cve_data.__getitem__.return_value)
    assert (
        cve.cve_data.__getitem__.call_args
        == [("nodes", ), {}])
    assert "nodes" not in cve.__dict__


def test_cve_published_date(patches):
    cve_data = MagicMock()
    cve = DummyCVE(cve_data, "TRACKED_CPES", "CPE_CLASS")
    patched = patches(
        "ACVE.parse_date",
        prefix="aio.api.nist.abstract.cve")

    with patched as (m_parse, ):
        assert (
            cve.published_date
            == m_parse.return_value)

    assert (
        m_parse.call_args
        == [(cve_data.__getitem__.return_value, ), {}])
    assert (
        cve_data.__getitem__.call_args
        == [("published_date", ), {}])
    assert "published_date" not in cve.__dict__


@pytest.mark.parametrize("include", ["odd", "even"])
def test_cve_gather_cpes(patches, include):
    cpe_class = MagicMock()
    cve = DummyCVE("CVE", "TRACKED_CPES", cpe_class)
    patched = patches(
        "ACVE.include_version",
        prefix="aio.api.nist.abstract.cve")
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

    with patched as (m_include, ):
        m_include.side_effect = include_cpe
        assert not cve.gather_cpes(nodes, cpe_set)

    assert (
        cpe_class.from_string.call_args_list
        == [[('URI0',), {}],
            [('URI1',), {}], [('URI2',), {}],
            [('URI3',), {}], [('URI4',), {}],
            [('URIa3',), {}], [('URIa4',), {}],
            [('URIa5',), {}], [('URIa6',), {}],
            [('URIab5',), {}], [('URIab6',), {}]])
    cpe_obj = cpe_class.from_string.return_value
    assert (
        m_include.call_args_list
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
        cpe_set.add.call_args_list
        == [[(cpe_obj,), {}]] * expected_cpe_count)


@pytest.mark.parametrize("tracked", [True, False])
@pytest.mark.parametrize("matches", [True, False])
def test_cve_include_version(tracked, matches):
    tracked_cpes = MagicMock()
    tracked_cpes.__contains__.return_value = tracked
    cve = DummyCVE("CVE", tracked_cpes, "CPE_CLASS")
    cpe_match = MagicMock()
    cpe = MagicMock()
    tracked_cpes.__getitem__.return_value.return_value = matches
    assert (
        cve.include_version(cpe_match, cpe)
        == (tracked and matches))
    assert (
        tracked_cpes.__contains__.call_args
        == [(str(cpe),), {}])
    if not tracked:
        assert not tracked_cpes.__getitem__.called
        return
    assert (
        tracked_cpes.__getitem__.call_args
        == [(str(cpe), ), {}])
    assert (
        tracked_cpes.__getitem__.return_value.call_args
        == [(cve, cpe, cpe_match), {}])


@pytest.mark.parametrize("delete", [True, False])
@pytest.mark.parametrize(
    "cve_fields",
    [None, {}, {f"FK{i}": f"VK{i}" for i in range(0, 5)}])
def test_cve_update_fields(patches, delete, cve_fields):
    kwargs = {}
    fields = MagicMock()
    if cve_fields is not None:
        fields.return_value = cve_fields
        kwargs["cve_fields"] = fields
    cve = DummyCVE("CVE_DATA", "TRACKED_CPES", "CPE_CLASS", **kwargs)
    patched = patches(
        ("ACVE.cve_dict", dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.cve")

    with patched as (m_dict, ):
        assert not cve.update_fields("DATA")

    assert (
        m_dict.return_value.__delitem__.call_args
        == [("nodes", ), {}])

    if cve_fields is not None:
        assert (
            m_dict.return_value.update.call_args
            == [(), cve_fields])
        assert (
            fields.call_args
            == [("DATA", ), {}])
    else:
        assert not m_dict.return_value.update.called
        assert not fields.called
