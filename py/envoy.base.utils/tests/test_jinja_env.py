
import types
from unittest.mock import MagicMock, PropertyMock

import pytest

from envoy.base import utils


def test_env_parser_create(patches):
    patched = patches(
        "argparse",
        prefix="envoy.base.utils.jinja_env")

    with patched as (m_parse, ):
        assert (
            utils.JinjaEnvironment.parser_create
            == m_parse.ArgumentParser.return_value)

    assert (
        m_parse.ArgumentParser.call_args
        == [(), {}])
    assert (
        m_parse.ArgumentParser.return_value.add_argument.call_args_list
        == [[("outpath", ), {}],
            [("-t", "--template"), dict(nargs="+")],
            [("-f", "--filter"), dict(action="append")]])


def test_env_parser_load(patches):
    patched = patches(
        "argparse",
        prefix="envoy.base.utils.jinja_env")

    with patched as (m_parse, ):
        assert (
            utils.JinjaEnvironment.parser_load
            == m_parse.ArgumentParser.return_value)

    assert (
        m_parse.ArgumentParser.call_args
        == [(), {}])
    assert (
        m_parse.ArgumentParser.return_value.add_argument.call_args_list
        == [[("template_py", ), {}],
            [("-f", "--filter"), dict(action="append")]])


@pytest.mark.parametrize("template", [None, [], True])
def test_env_create(iters, patches, template):
    patched = patches(
        "list",
        "pathlib",
        "set",
        "jinja2",
        ("JinjaEnvironment.parser_create",
         dict(new_callable=PropertyMock)),
        "JinjaEnvironment._env",
        prefix="envoy.base.utils.jinja_env")
    args = iters()
    if template:
        template = iters(start=7)

    with patched as (m_list, m_plib, m_set, m_jinja, m_parser, m_env):
        m_parser.return_value.parse_args.return_value.template = template
        assert not utils.JinjaEnvironment.create(*args)
        resultgen = m_set.call_args[0][0]
        resultlist = list(resultgen)

    assert (
        m_parser.return_value.parse_args.call_args
        == [(tuple(args), ), {}])
    assert (
        m_env.call_args
        == [(m_jinja.FileSystemLoader.return_value,
             m_parser.return_value.parse_args.return_value.filter), {}])
    assert (
        m_env.return_value.compile_templates.call_args
        == [(m_parser.return_value.parse_args.return_value.outpath, ), {}])
    assert (
        m_jinja.FileSystemLoader.call_args
        == [(m_list.return_value, ), {}])
    assert (
        m_list.call_args
        == [(m_set.return_value, ), {}])
    assert isinstance(resultgen, types.GeneratorType)
    assert (
        m_set.call_args
        == [(resultgen, ), {}])
    assert (
        resultlist
        == [m_plib.Path.return_value.parent
            for t
            in (template or [])])
    assert (
        m_plib.Path.call_args_list
        == [[(t, ), {}]
            for t
            in (template or [])])


def test_env_load(iters, patches):
    patched = patches(
        "jinja2",
        ("JinjaEnvironment.parser_load",
         dict(new_callable=PropertyMock)),
        "JinjaEnvironment._env",
        prefix="envoy.base.utils.jinja_env")
    args = iters()
    kwargs = iters(dict)

    with patched as (m_jinja, m_parser, m_env):
        assert (
            utils.JinjaEnvironment.load(*args, **kwargs)
            == m_env.return_value)

    assert (
        m_parser.return_value.parse_args.call_args
        == [(tuple(args), ), {}])
    assert (
        m_env.call_args
        == [(m_jinja.ModuleLoader.return_value,
             m_parser.return_value.parse_args.return_value.filter),
            kwargs])
    assert (
        m_jinja.ModuleLoader.call_args
        == [(m_parser.return_value.parse_args.return_value.template_py, ), {}])


def test_env__env(iters, patches):
    patched = patches(
        "jinja2",
        "JinjaEnvironment._filters",
        prefix="envoy.base.utils.jinja_env")
    loader = MagicMock()
    filters = MagicMock()
    kwargs = iters(dict)

    with patched as (m_jinja, m_filters):
        assert (
            utils.JinjaEnvironment._env(loader, filters, **kwargs)
            == m_jinja.Environment.return_value)

    assert (
        m_jinja.Environment.call_args
        == [(), dict(loader=loader, **kwargs)])
    assert (
        m_jinja.Environment.return_value.filters.update.call_args
        == [(m_filters.return_value, ), {}])
    assert (
        m_filters.call_args
        == [(filters, ), {}])


def test_env__filter(iters, patches):
    patched = patches(
        "getattr",
        "importlib",
        prefix="envoy.base.utils.jinja_env")
    filter_path = MagicMock()
    module_parts = iters()

    def parts(part):
        if part == -1:
            return "FILTER"
        return module_parts

    filter_path.split.return_value.__getitem__.side_effect = parts

    with patched as (m_getattr, m_import):
        assert (
            utils.JinjaEnvironment._filter(filter_path)
            == m_getattr.return_value)

    assert (
        filter_path.split.call_args
        == [(".", ), {}])
    assert (
        m_getattr.call_args
        == [(m_import.import_module.return_value, "FILTER"), {}])
    assert (
        m_import.import_module.call_args
        == [(".".join(module_parts), ), {}])
    assert (
        filter_path.split.return_value.__getitem__.call_args_list
        == [[(slice(None, -1), ), {}],
            [(-1, ), {}]])


@pytest.mark.parametrize("filters", [None, [], True])
def test_env__filters(iters, patches, filters):
    patched = patches(
        "JinjaEnvironment._filter",
        prefix="envoy.base.utils.jinja_env")
    if filters:
        filters = iters(cb=lambda i: MagicMock())

    with patched as (m_filter, ):
        assert (
            utils.JinjaEnvironment._filters(filters)
            == {(f.split.return_value
                        .__getitem__.return_value): m_filter.return_value
                for f in (filters or [])})

    for f in filters or []:
        assert (
            f.split.call_args
            == [(":", ), {}])
        assert (
            f.split.return_value.__getitem__.call_args_list
            == [[(0, ), {}],
                [(1, ), {}]])
    assert (
        m_filter.call_args_list
        == [[(f.split.return_value.__getitem__.return_value, ), {}]
            for f in (filters or [])])
