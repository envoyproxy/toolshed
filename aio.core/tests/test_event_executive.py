
from unittest.mock import AsyncMock, PropertyMock

import pytest

import abstracts

from aio.core import event


@abstracts.implementer(event.IExecutive)
class DummyExecutiveIface():

    @property
    def loop(self):
        return event.IExecutive.loop.fget(self)

    @property
    def pool(self):
        return event.IExecutive.pool.fget(self)

    async def execute(self, *args, **kwargs):
        return await event.IExecutive.execute(*args, **kwargs)


@abstracts.implementer(event.IExecutive)
class DummyExecutive(event.AExecutive):
    pass


async def test_event_executive_iface_constructor():

    with pytest.raises(TypeError):
        event.IExecutive()

    executive = DummyExecutiveIface()
    for iface_prop in ["loop", "pool"]:
        with pytest.raises(NotImplementedError):
            getattr(executive, iface_prop)
    for async_iface_method in ["execute"]:
        with pytest.raises(NotImplementedError):
            await getattr(executive, async_iface_method)()


def test_event_executive_constructor():
    assert DummyExecutive()


@pytest.mark.parametrize(
    "args", [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs", [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
async def test_event_executive_execute(patches, args, kwargs):
    executive = DummyExecutive()
    patched = patches(
        ("AExecutive.loop",
         dict(new_callable=PropertyMock)),
        ("AExecutive.pool",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.event.executive")

    with patched as (m_loop, m_pool):
        execute = AsyncMock()
        m_loop.return_value.run_in_executor = execute
        assert (
            await executive.execute(*args, **kwargs)
            == m_loop.return_value.run_in_executor.return_value)

    assert (
        m_loop.return_value.run_in_executor.call_args
        == [(m_pool.return_value, *args), kwargs])
