
from unittest.mock import MagicMock, PropertyMock

import pytest

from envoy.base import utils


def test_env_parser_create(patches):
    patched = patches(
        "argparse",
        prefix="envoy.base.utils.data_env")

    with patched as (m_parse, ):
        assert (
            utils.DataEnvironment.parser_create
            == m_parse.ArgumentParser.return_value)

    assert (
        m_parse.ArgumentParser.call_args
        == [(), {}])
    assert (
        m_parse.ArgumentParser.return_value.add_argument.call_args_list
        == [[("data", ), {}],
            [("outpath", ), {}],
            [("-f", "--format"), dict(default="json")]])


def test_env_parser_load(patches):
    patched = patches(
        "argparse",
        prefix="envoy.base.utils.data_env")

    with patched as (m_parse, ):
        assert (
            utils.DataEnvironment.parser_load
            == m_parse.ArgumentParser.return_value)

    assert (
        m_parse.ArgumentParser.call_args
        == [(), {}])
    assert (
        m_parse.ArgumentParser.return_value.add_argument.call_args_list
        == [[("pickle", ), {}]])


def test_env_create(iters, patches):
    patched = patches(
        "open",
        "pickle",
        ("DataEnvironment.parser_create",
         dict(new_callable=PropertyMock)),
        "DataEnvironment._data",
        prefix="envoy.base.utils.data_env")
    args = iters()

    with patched as (m_open, m_pickle, m_parser, m_data):
        assert not utils.DataEnvironment.create(*args)

    assert (
        m_parser.return_value.parse_args.call_args
        == [(tuple(args), ), {}])
    parsed = m_parser.return_value.parse_args.return_value
    assert (
        m_open.call_args
        == [(parsed.outpath, "wb"), {}])
    assert (
        m_pickle.dump.call_args
        == [(m_data.return_value,
             m_open.return_value.__enter__.return_value,
             m_pickle.HIGHEST_PROTOCOL), {}])
    assert (
        m_data.call_args
        == [(parsed.data, parsed.format), {}])


def test_env_load(iters, patches):
    patched = patches(
        "open",
        "pickle",
        ("DataEnvironment.parser_load",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.data_env")
    args = iters()

    with patched as (m_open, m_pickle, m_parser):
        assert (
            utils.DataEnvironment.load(*args)
            == m_pickle.load.return_value)

    assert (
        m_parser.return_value.parse_args.call_args
        == [(tuple(args), ), {}])
    parsed = m_parser.return_value.parse_args.return_value
    assert (
        m_open.call_args
        == [(parsed.pickle, "rb"), {}])
    assert (
        m_pickle.load.call_args
        == [(m_open.return_value.__enter__.return_value, ), {}])


@pytest.mark.parametrize("format", [None, "json", "FOO", "yaml"])
def test_env__data(patches, format):
    patched = patches(
        "utils",
        prefix="envoy.base.utils.data_env")
    data = MagicMock()
    format = format

    with patched as (m_utils, ):
        expected_fun = (
            m_utils.from_yaml
            if format == "yaml"
            else m_utils.from_json)
        unexpected_fun = (
            m_utils.from_yaml
            if format != "yaml"
            else m_utils.from_json)
        assert (
            utils.DataEnvironment._data(data, format)
            == expected_fun.return_value)

    assert (
        expected_fun.call_args
        == [(data, ), {}])
    assert not unexpected_fun.called
