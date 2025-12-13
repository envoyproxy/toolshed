
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio.core import event


@abstracts.implementer(event.ILoader)
class DummyLoaderIface():

    def __await__(self):
        return event.ILoader.__await__(self)

    def __enter__(self):
        return event.ILoader.__enter__(self)

    def __exit__(self, *exception):
        return event.ILoader.__exit__(self, *exception)

    @property
    def loaded(self):
        return event.ILoader.loaded.fget(self)

    @property
    def loading(self):
        return event.ILoader.loading.fget(self)

    def complete(self):
        return event.ILoader.complete(self)

    def start(self):
        return event.ILoader.start(self)

    async def wait(self):
        return await event.ILoader.wait(self)


@abstracts.implementer(event.ILoader)
class DummyLoader(event.ALoader):
    pass


async def test_event_loader_iface_constructor():

    with pytest.raises(TypeError):
        event.ILoader()

    loader = DummyLoaderIface()
    iface_props = ["loaded", "loading"]
    iface_methods = ["__await__", "__enter__", "complete", "start"]

    for iface_prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(loader, iface_prop)

    for iface_method in iface_methods:
        with pytest.raises(NotImplementedError):
            getattr(loader, iface_method)()

    with pytest.raises(NotImplementedError):
        loader.__exit__("EX", "CE", "PTION")

    with pytest.raises(NotImplementedError):
        await loader.wait()


def test_abstract_event_loader_constructor():
    loader = DummyLoader()
    assert isinstance(loader, event.ILoader)


@pytest.mark.parametrize("event_prop", ["_loading", "_loaded"])
def test_abstract_event_loader_event_props(patches, event_prop):
    loader = DummyLoader()
    patched = patches(
        "asyncio",
        prefix="aio.core.event.loader")

    with patched as (m_asyncio, ):
        assert (
            getattr(loader, event_prop)
            == m_asyncio.Event.return_value)

    assert (
        m_asyncio.Event.call_args
        == [(), {}])
    assert event_prop in loader.__dict__


@pytest.mark.parametrize("event_prop", ["loading", "loaded"])
def test_abstract_event_loader_event_props_set(patches, event_prop):
    loader = DummyLoader()
    patched = patches(
        (f"ALoader._{event_prop}",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.event.loader")

    with patched as (m_prop, ):
        assert (
            getattr(loader, event_prop)
            == m_prop.return_value.is_set.return_value)

    assert (
        m_prop.return_value.is_set.call_args
        == [(), {}])
    assert event_prop not in loader.__dict__


def test_abstract_event_loader_dunder_await(patches):
    loader = DummyLoader()
    patched = patches(
        ("ALoader.wait",
         dict(new_callable=MagicMock)),
        prefix="aio.core.event.loader")

    with patched as (m_wait, ):
        waiter = MagicMock()
        m_wait.return_value.__await__ = waiter
        assert (
            loader.__await__()
            == waiter.return_value)

    assert (
        m_wait.call_args
        == [(), {}])
    assert (
        waiter.call_args
        == [(), {}])


def test_abstract_event_loader_dunder_enter(patches):
    loader = DummyLoader()
    patched = patches(
        "ALoader.start",
        prefix="aio.core.event.loader")

    with patched as (m_start, ):
        assert not loader.__enter__()

    assert (
        m_start.call_args
        == [(), {}])


def test_abstract_event_loader_dunder_exit(patches):
    loader = DummyLoader()
    patched = patches(
        "ALoader.complete",
        prefix="aio.core.event.loader")

    with patched as (m_complete, ):
        assert not loader.__exit__()

    assert (
        m_complete.call_args
        == [(), {}])


def test_abstract_event_loader_start(patches):
    loader = DummyLoader()
    patched = patches(
        ("ALoader._loading",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.event.loader")

    with patched as (m_loading, ):
        assert not loader.start()

    assert (
        m_loading.return_value.set.call_args
        == [(), {}])


def test_abstract_event_loader_complete(patches):
    loader = DummyLoader()
    patched = patches(
        ("ALoader._loading",
         dict(new_callable=PropertyMock)),
        ("ALoader._loaded",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.event.loader")

    with patched as (m_loading, m_loaded):
        assert not loader.complete()

    assert (
        m_loading.return_value.clear.call_args
        == [(), {}])
    assert (
        m_loaded.return_value.set.call_args
        == [(), {}])


@pytest.mark.parametrize("loading", [True, False])
async def test_abstract_event_loader_wait(patches, loading):
    loader = DummyLoader()
    patched = patches(
        ("ALoader.loading",
         dict(new_callable=PropertyMock)),
        ("ALoader.loaded",
         dict(new_callable=PropertyMock)),
        ("ALoader._loaded",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.event.loader")

    with patched as (m_loading, m_loaded, m_event):
        m_loading.return_value = loading
        waiter = AsyncMock()
        m_event.return_value.wait = waiter
        assert (
            await loader.wait()
            == m_loaded.return_value)

    if not loading:
        assert not waiter.called
        return
    assert (
        waiter.call_args
        == [(), {}])
