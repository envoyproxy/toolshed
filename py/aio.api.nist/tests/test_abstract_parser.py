
import types
from unittest.mock import MagicMock, PropertyMock

import pytest

import abstracts

from aio.api import nist


@abstracts.implementer(nist.ANISTParser)
class DummyNISTParser:

    @property
    def cpe_class(self):
        return super().cpe_class

    @property
    def cve_class(self):
        return super().cve_class

    @property
    def matcher_class(self):
        return super().matcher_class


@pytest.mark.parametrize(
    "ignored_cves", [None, False, (), "IGNORED_CVES"])
def test_parser_constructor(ignored_cves):
    kwargs = {}
    if ignored_cves is not None:
        kwargs["ignored_cves"] = ignored_cves

    with pytest.raises(TypeError):
        nist.ANISTParser("TRACKED_CPES", **kwargs)
        return

    parser = DummyNISTParser("TRACKED_CPES", **kwargs)
    assert parser._tracked_cpes == "TRACKED_CPES"
    assert parser.ignored_cves == (ignored_cves or set())
    assert parser.cves == {}
    assert "cves" in parser.__dict__
    assert parser.cpe_revmap == {}
    assert "cpe_revmap" in parser.__dict__
    iface_props = ["cve_class", "cpe_class", "matcher_class"]
    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(parser, prop)


def test_parser_dunder_call(patches):
    parser = DummyNISTParser("TRACKED_CPES")
    patched = patches(
        "ANISTParser.parse_cve_data",
        prefix="aio.api.nist.abstract.parser")
    data = MagicMock()

    with patched as (m_parse, ):
        assert parser(data) == m_parse.return_value

    assert (
        m_parse.call_args
        == [(data, ), {}])


def test_parser_query_fields(patches):
    parser = DummyNISTParser("TRACKED_CPES")
    patched = patches(
        "qdict",
        prefix="aio.api.nist.abstract.parser")

    with patched as (m_qdict, ):
        assert (
            parser.query_fields
            == m_qdict.return_value)

    assert (
        m_qdict.call_args
        == [(),
            dict(
                id="cve/CVE_data_meta/ID",
                nodes="configurations/nodes",
                published_date="publishedDate")])
    assert "query_fields" in parser.__dict__


def test_parser_tracked_cpes(iters, patches):
    tracked_cpes = MagicMock()
    parser = DummyNISTParser(tracked_cpes)
    patched = patches(
        "ANISTParser._tracked_cpe",
        prefix="aio.api.nist.abstract.parser")
    cpes = iters(dict).items()
    tracked_cpes.items.return_value = cpes

    with patched as (m_tracked, ):
        assert (
            parser.tracked_cpes
            == {k: m_tracked.return_value
                for k, v in cpes})

    assert (
        m_tracked.call_args_list
        == [[(k, v), {}]
            for k, v in cpes])
    assert "tracked_cpes" in parser.__dict__


def test_parser_add_cpe_revmap(iters, patches):
    parser = DummyNISTParser("TRACKED_CPES")
    patched = patches(
        ("ANISTParser.cpe_revmap",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.parser")
    cve = MagicMock()
    cve.cpes = iters(cb=lambda i: MagicMock())

    with patched as (m_revmap, ):
        assert not parser.add_cpe_revmap(cve)

    assert (
        m_revmap.return_value.__setitem__.call_args_list
        == [[(cve_cpe.vendor_normalized,
              m_revmap.return_value.get.return_value), {}]
            for cve_cpe in cve.cpes])
    assert (
        m_revmap.return_value.get.call_args_list
        == [[(cve_cpe.vendor_normalized,
              set()), {}]
            for cve_cpe in cve.cpes])
    assert (
        m_revmap.return_value.__getitem__.call_args_list
        == [[(cve_cpe.vendor_normalized, ), {}]
            for cve_cpe in cve.cpes])
    assert (
        m_revmap.return_value.__getitem__.return_value.add.call_args_list
        == [[(cve.id, ), {}]
            for cve_cpe in cve.cpes])


@pytest.mark.parametrize("cpes", [True, False])
def test_parser_add_cve(patches, cpes):
    cve_fields = MagicMock()
    parser = DummyNISTParser("TRACKED_CPES", cve_fields=cve_fields)
    patched = patches(
        ("ANISTParser.cpe_class",
         dict(new_callable=PropertyMock)),
        ("ANISTParser.cve_class",
         dict(new_callable=PropertyMock)),
        ("ANISTParser.cves",
         dict(new_callable=PropertyMock)),
        ("ANISTParser.tracked_cpes",
         dict(new_callable=PropertyMock)),
        "ANISTParser.add_cpe_revmap",
        prefix="aio.api.nist.abstract.parser")
    data = MagicMock()
    item = MagicMock()

    with patched as (m_cpe_class, m_class, m_cves,  m_tracked, m_add_revmap):
        m_class.return_value.return_value.cpes = cpes
        assert not parser.add_cve(data, item)

    cve = m_class.return_value.return_value
    assert (
        m_class.return_value.call_args
        == [(item,
             m_tracked.return_value,
             m_cpe_class.return_value,
             cve_fields),
            {}])
    if not cpes:
        assert not cve.cve_dict.__delitem__.called
        assert not m_add_revmap.called
        assert not m_cves.return_value.__setitem__.called
        return
    assert (
        m_add_revmap.call_args
        == [(cve, ), {}])
    assert (
        m_cves.return_value.__setitem__.call_args
        == [(cve.id, cve.cve_dict), {}])


@pytest.mark.parametrize("ignored", [True, False])
@pytest.mark.parametrize("is_v3", [True, False])
@pytest.mark.parametrize("nodes", [True, False])
def test_parser_include_cve(patches, is_v3, ignored, nodes):
    ignored_cves = MagicMock()
    ignored_cves.__contains__.return_value = ignored
    parser = DummyNISTParser("TRACKED_CPES", ignored_cves=ignored_cves)
    patched = patches(
        "logger",
        "bool",
        prefix="aio.api.nist.abstract.parser")
    cve = MagicMock()
    meta = MagicMock()

    def getitem(item):
        if item == "nodes":
            return nodes
        return meta

    cve.__getitem__.return_value.__getitem__.side_effect = getitem

    with patched as (m_logger, m_bool):
        m_bool.return_value = is_v3
        assert (
            parser.include_cve(cve)
            == (nodes and is_v3 and not ignored))

    get_calls = [[("configurations", ), {}]]
    if nodes:
        get_calls.append([("impact", ), {}])
        get_calls.append([("cve", ), {}])
    assert (
        cve.__getitem__.call_args_list
        == get_calls)
    if not nodes:
        assert not cve.__getitem__.return_value.get.called
        assert not ignored_cves.__contains__.called
        assert not m_bool.called
        assert not m_logger.called
        assert (
            cve.__getitem__.return_value.__getitem__.call_args_list
            == [[("nodes", ), {}]])
        return
    assert (
        m_bool.call_args
        == [(cve.__getitem__.return_value.get.return_value, ), {}])
    assert (
        cve.__getitem__.return_value.get.call_args
        == [("baseMetricV3", ), {}])
    assert (
        cve.__getitem__.return_value.__getitem__.call_args_list
        == [[("nodes", ), {}],
            [("CVE_data_meta", ), {}]])
    assert (
        meta.__getitem__.call_args
        == [("ID", ), {}])
    if not is_v3:
        assert not m_logger.called
        assert not ignored_cves.__contains__.called
        return
    assert (
        ignored_cves.__contains__.call_args
        == [(meta.__getitem__.return_value, ),
            {}])
    if not ignored:
        assert not m_logger.called
        return
    assert (
        m_logger.debug.call_args
        == [(f"Excluding {meta.__getitem__.return_value} (v3: {is_v3})", ),
            {}])


@pytest.mark.parametrize("include", range(1, 10))
def test_parser_iter_cve_json(iters, patches, include):
    parser = DummyNISTParser("TRACKED_CPES")
    patched = patches(
        ("ANISTParser.query_fields",
         dict(new_callable=PropertyMock)),
        "ANISTParser.include_cve",
        "ANISTParser._junzip_items",
        prefix="aio.api.nist.abstract.parser")
    data = MagicMock()
    cves = iters(cb=lambda i: MagicMock(), count=7)

    def parser_returns(x):
        if x % include:
            return cves[x]

    with patched as (m_fields, m_include, m_junzip):
        m_junzip.return_value = range(0, 7)
        m_include.side_effect = parser_returns
        iterator = parser.iter_cve_json(data)
        assert isinstance(iterator, types.GeneratorType)
        results = list(iterator)

    assert (
        results
        == [(item, m_fields.return_value.return_value)
            for item
            in range(0, 7)
            if item % include])
    assert (
        m_junzip.call_args
        == [(data, ), {}])
    assert (
        m_fields.return_value.call_args_list
        == [[(i, ), {}]
            for i
            in range(0, 7)
            if i % include])


def test_parser_parse_cve_data(iters, patches):
    parser = DummyNISTParser("TRACKED_CPES")
    patched = patches(
        ("ANISTParser.cpe_revmap",
         dict(new_callable=PropertyMock)),
        ("ANISTParser.cves",
         dict(new_callable=PropertyMock)),
        "ANISTParser.add_cve",
        "ANISTParser.iter_cve_json",
        prefix="aio.api.nist.abstract.parser")
    data = MagicMock()
    cves = iters(dict, cb=lambda i: (i, MagicMock())).items()

    with patched as (m_revmap, m_cves, m_add, m_iter):
        m_iter.return_value = cves
        assert (
            parser.parse_cve_data(data)
            == (m_cves.return_value,
                m_revmap.return_value))

    assert m_iter.call_args == [(data, ), {}]
    assert (
        m_add.call_args_list
        == [[item, {}] for item in cves])


@pytest.mark.parametrize("date_str", [None, "", "DATE"])
def test_parser__iso_date(patches, date_str):
    parser = DummyNISTParser("TRACKED_CPES")
    patched = patches(
        ("ANISTParser.cve_class",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.nist.abstract.parser")

    with patched as (m_class, ):
        assert (
            parser._iso_date(date_str)
            == (m_class.return_value.parse_date.return_value
                if date_str
                else None))

    if not date_str:
        assert not m_class.return_value.parse_date.called
    else:
        assert (
            m_class.return_value.parse_date.call_args
            == [(date_str, ), {}])


def test_parser__junzip_items(patches):
    parser = DummyNISTParser("TRACKED_CPES")
    patched = patches(
        "utils",
        prefix="aio.api.nist.abstract.parser")

    with patched as (m_utils, ):
        assert (
            parser._junzip_items("DATA")
            == m_utils.junzip.return_value.__getitem__.return_value)

    assert (
        m_utils.junzip.call_args
        == [("DATA", ), {}])
    assert (
        m_utils.junzip.return_value.__getitem__.call_args
        == [("CVE_Items", ), {}])


def test_parser__tracked_cpe(patches):
    parser = DummyNISTParser("TRACKED_CPES")
    patched = patches(
        "dict",
        ("ANISTParser.cpe_class",
         dict(new_callable=PropertyMock)),
        ("ANISTParser.matcher_class",
         dict(new_callable=PropertyMock)),
        "ANISTParser._iso_date",
        prefix="aio.api.nist.abstract.parser")
    cpe_name = MagicMock()
    cpe_filter = MagicMock()

    with patched as (m_dict, m_cpe_class, m_matcher_class, m_date):
        assert (
            parser._tracked_cpe(cpe_name, cpe_filter)
            == m_matcher_class.return_value.return_value)

    assert (
        m_matcher_class.return_value.call_args
        == [(m_dict.return_value, ), {}])
    assert (
        m_dict.call_args
        == [(),
            dict(version=cpe_filter.get.return_value,
                 cpe=m_cpe_class.return_value.from_string.return_value,
                 date=m_date.return_value)])
    assert (
        cpe_filter.get.call_args_list
        == [[("version", ), {}],
            [("date", ), {}]])
    assert (
        m_cpe_class.return_value.from_string.call_args
        == [(cpe_name, ), {}])
    assert (
        m_date.call_args
        == [(cpe_filter.get.return_value, ), {}])
