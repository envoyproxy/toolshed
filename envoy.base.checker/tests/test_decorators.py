
from unittest.mock import MagicMock, PropertyMock

import pytest


from envoy.base import checker


@pytest.mark.parametrize("when", [None, "WHEN"])
@pytest.mark.parametrize("name", [None, "NAME"])
@pytest.mark.parametrize("blocks", [None, "BLOCKS"])
@pytest.mark.parametrize("catches", [None, "CATCHES"])
@pytest.mark.parametrize("unless", [None, "UNLESS"])
@pytest.mark.parametrize("cabbage", [None, "CABBAGE"])
def test_preload_constructor(when, name, blocks, catches, unless, cabbage):
    kwargs = {}
    if when:
        kwargs["when"] = when
    if name:
        kwargs["name"] = name
    if blocks:
        kwargs["blocks"] = blocks
    if catches:
        kwargs["catches"] = catches
    if unless:
        kwargs["unless"] = unless
    if cabbage:
        kwargs["cabbage"] = cabbage
    if cabbage or not when:
        with pytest.raises(TypeError):
            checker.preload(**kwargs)
        return
    else:
        preloader = checker.preload(**kwargs)
    assert preloader._when == when
    assert preloader._blocks == blocks
    assert preloader._catches == catches
    assert preloader._name == name
    assert preloader._unless == unless


def test_preload_dunder_call():
    preloader = checker.preload("WHEN")
    fun = MagicMock()
    assert preloader(fun) is preloader
    assert preloader._fun == fun


def test_preload_dunder_set_name(patches):
    preloader = checker.preload("WHEN")
    patched = patches(
        "preload.get_preload_checks_data",
        prefix="envoy.base.checker.decorators")
    cls = MagicMock()

    with patched as (m_data, ):
        assert not preloader.__set_name__(cls, "NAME")

    assert cls._preload_checks_data == m_data.return_value
    assert (
        m_data.call_args
        == [(cls, ), {}])
    assert preloader.name == "NAME"


@pytest.mark.parametrize("cls", [None, "CLS"])
@pytest.mark.parametrize("instance", [None, "", "INSTANCE"])
def test_preload_dunder_get(patches, cls, instance):
    preloader = checker.preload("WHEN")
    patched = patches(
        ("preload.fun",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.checker.decorators")
    args = (
        (cls, )
        if cls
        else ())

    with patched as (m_fun, ):
        assert (
            preloader.__get__(instance, *args)
            == (m_fun.return_value
                if instance is not None
                else preloader))

    assert preloader._instance == instance


@pytest.mark.parametrize(
    "blocks",
    [None, (), [], [f"C{i}" for i in range(0, 5)]])
def test_preload_blocks(patches, blocks):
    preloader = checker.preload("WHEN")
    patched = patches(
        ("preload.when",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.checker.decorators")
    when = tuple(f"C{i}" for i in range(0, 5))
    preloader._blocks = blocks

    with patched as (m_when, ):
        m_when.return_value = when
        assert (
            preloader.blocks
            == (when + tuple(blocks or ())))

    assert "blocks" not in preloader.__dict__


@pytest.mark.parametrize(
    "catches",
    [None, (), [], [f"C{i}" for i in range(0, 5)]])
def test_preload_catches(patches, catches):
    preloader = checker.preload("WHEN")
    preloader._catches = catches
    assert (
        preloader.catches
        == tuple(catches or ()))
    assert "catches" not in preloader.__dict__


@pytest.mark.parametrize("name", [None, "", "NAME"])
def test_preload_tag_name(name):
    preloader = checker.preload("WHEN")
    preloader.name = "DEFAULT NAME"
    preloader._name = name
    assert (
        preloader.tag_name
        == (name or "DEFAULT NAME"))
    assert "tag_name" not in preloader.__dict__


@pytest.mark.parametrize(
    "unless",
    [None, (), [], [f"C{i}" for i in range(0, 5)]])
def test_preload_unless(patches, unless):
    preloader = checker.preload("WHEN")
    preloader._unless = unless
    assert (
        preloader.unless
        == tuple(unless or ()))
    assert "unless" not in preloader.__dict__


@pytest.mark.parametrize(
    "when",
    [(), [], [f"C{i}" for i in range(0, 5)]])
def test_preload_when(when):
    preloader = checker.preload("WHEN")
    preloader._when = when
    assert (
        preloader.when
        == tuple(when))
    assert "when" not in preloader.__dict__


@pytest.mark.parametrize("instance", [None, "", "INSTANCE"])
@pytest.mark.parametrize("args", [True, False])
@pytest.mark.parametrize("kwargs", [True, False])
def test_preload_fun(instance, args, kwargs):
    preloader = checker.preload("WHEN")
    preloader._instance = instance
    preloader._fun = MagicMock()
    args = (
        [f"ARG{i}" for i in range(0, 5)]
        if args
        else [])
    kwargs = (
        {f"K{i}": f"V{i}" for i in range(0, 5)}
        if kwargs
        else {})

    assert (
        preloader.fun(*args, **kwargs)
        == preloader._fun.return_value)

    if instance:
        assert (
            preloader._fun.call_args
            == [(instance, ) + tuple(args), kwargs])
    else:
        assert (
            preloader._fun.call_args
            == [tuple(args), kwargs])


def test_preload_get_preload_checks_data(patches):
    preloader = checker.preload("WHEN")
    patched = patches(
        "dict",
        "getattr",
        "tuple",
        ("preload.blocks",
         dict(new_callable=PropertyMock)),
        ("preload.catches",
         dict(new_callable=PropertyMock)),
        ("preload.fun",
         dict(new_callable=PropertyMock)),
        ("preload.tag_name",
         dict(new_callable=PropertyMock)),
        ("preload.unless",
         dict(new_callable=PropertyMock)),
        ("preload.when",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.checker.decorators")
    cls = MagicMock()

    with patched as patchy:
        (m_dict, m_get, m_tuple, m_blocks, m_catches,
         m_fun, m_tag, m_unless, m_when) = patchy
        assert (
            preloader.get_preload_checks_data(cls)
            == m_tuple.return_value)

    assert len(m_dict.call_args_list) == 2
    assert (
        m_dict.call_args_list[0]
        == [(m_get.return_value, ), {}])
    assert (
        m_get.call_args
        == [(cls, "_preload_checks_data", ()), {}])
    assert (
        m_dict.return_value.__setitem__.call_args
        == [(m_tag.return_value, m_dict.return_value), {}])
    assert (
        m_tuple.call_args
        == [(m_dict.return_value.items.return_value, ), {}])
    assert (
        m_dict.call_args_list[1]
        == [(),
            dict(name=m_tag.return_value,
                 blocks=m_blocks.return_value,
                 catches=m_catches.return_value,
                 fun=m_fun.return_value,
                 unless=m_unless.return_value,
                 when=m_when.return_value)])
    assert (
        m_dict.return_value.items.call_args
        == [(), {}])
