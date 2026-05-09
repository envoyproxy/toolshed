
import pytest

import abstracts

from aio.core import event


@abstracts.implementer(event.IReactive)
class DummyReactiveIface():

    @property
    def loop(self):
        return event.IReactive.loop.fget(self)

    @property
    def pool(self):
        return event.IReactive.loop.fget(self)


@abstracts.implementer(event.IReactive)
class DummyReactive(event.AReactive):
    pass


def test_event_reactive_iface_constructor():

    with pytest.raises(TypeError):
        event.IReactive()

    reactive = DummyReactiveIface()
    for iface_prop in ["loop", "pool"]:
        with pytest.raises(NotImplementedError):
            getattr(reactive, iface_prop)


def test_event_reactive_constructor():
    reactive = DummyReactive()
    assert reactive._loop is None
    assert reactive._pool is None


def test_event_reactive_loop_injected(patches):
    reactive = DummyReactive()
    reactive._loop = "INJECTED_LOOP"
    patched = patches(
        "asyncio",
        prefix="aio.core.event.reactive")

    with patched as (m_aio, ):
        assert reactive.loop == "INJECTED_LOOP"

    assert not m_aio.get_event_loop_policy.called
    assert not m_aio.new_event_loop.called
    assert not m_aio.set_event_loop.called
    assert "loop" in reactive.__dict__


def test_event_reactive_loop_existing(patches):
    reactive = DummyReactive()
    patched = patches(
        "asyncio",
        prefix="aio.core.event.reactive")

    with patched as (m_aio, ):
        assert (
            reactive.loop
            == (
                m_aio.get_event_loop_policy
                .return_value
                .get_event_loop
                .return_value))

    assert (
        m_aio.get_event_loop_policy.return_value.get_event_loop.call_args
        == [(), {}])
    assert not m_aio.new_event_loop.called
    assert not m_aio.set_event_loop.called
    assert "loop" in reactive.__dict__


def test_event_reactive_loop_creates(patches):
    reactive = DummyReactive()
    patched = patches(
        "asyncio",
        prefix="aio.core.event.reactive")

    with patched as (m_aio, ):
        m_aio.get_event_loop_policy.return_value.get_event_loop.side_effect = (
            RuntimeError())
        assert reactive.loop == m_aio.new_event_loop.return_value

    assert (
        m_aio.get_event_loop_policy.return_value.get_event_loop.call_args
        == [(), {}])
    assert (
        m_aio.new_event_loop.call_args
        == [(), {}])
    assert (
        m_aio.set_event_loop.call_args
        == [(m_aio.new_event_loop.return_value,), {}])
    assert "loop" in reactive.__dict__


def test_event_reactive_pool(patches):
    reactive = DummyReactive()
    patched = patches(
        "futures",
        prefix="aio.core.event.reactive")

    with patched as (m_futures, ):
        assert (
            reactive.pool
            == m_futures.ProcessPoolExecutor.return_value)

    assert (
        m_futures.ProcessPoolExecutor.call_args
        == [(), {}])
    assert "pool" in reactive.__dict__
