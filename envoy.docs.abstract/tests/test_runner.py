
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from envoy.docs import abstract


@abstracts.implementer(abstract.ADocsBuildingRunner)
class DummyDocsBuildingRunner:

    @property
    def builders(self):
        return super().builders

    async def run(self):
        return await super().run()


def test_runner_constructor():
    with pytest.raises(TypeError):
        abstract.ADocsBuildingRunner()

    DummyDocsBuildingRunner()


def test_runner_cls_register_builder():
    assert abstract.ADocsBuildingRunner._builders == ()

    class Builder1(object):
        pass

    class Builder2(object):
        pass

    abstract.ADocsBuildingRunner.register_builder("builder1", Builder1)
    assert (
        abstract.ADocsBuildingRunner._builders
        == (('builder1', Builder1),))

    abstract.ADocsBuildingRunner.register_builder("builder2", Builder2)
    assert (
        abstract.ADocsBuildingRunner._builders
        == (('builder1', Builder1),
            ('builder2', Builder2),))


@pytest.mark.asyncio
async def test_runner_run(patches):
    runner = DummyDocsBuildingRunner()
    patched = patches(
        ("ADocsBuildingRunner.builders",
         dict(new_callable=PropertyMock)),
        ("ADocsBuildingRunner.tar",
         dict(new_callable=PropertyMock)),
        prefix="envoy.docs.abstract.runner")
    builders = [AsyncMock() for i in range(0, 5)]

    with patched as (m_builders, m_tar):
        m_builders.return_value.values.return_value = builders
        assert not await runner.run()

    assert (
        list(m_builders.return_value.values.call_args)
        == [(), {}])
    for builder in builders:
        assert (
            list(builder.build.call_args)
            == [(), {}])
    assert (
        list(m_tar.return_value.close.call_args)
        == [(), {}])


def test_runner_write_tar(patches):
    runner = DummyDocsBuildingRunner()
    patched = patches(
        "io",
        "utils",
        "tarfile",
        ("ADocsBuildingRunner.tar",
         dict(new_callable=PropertyMock)),
        prefix="envoy.docs.abstract.runner")
    path = MagicMock()
    content = MagicMock()
    content.__len__.return_value = 23

    with patched as (m_io, m_utils, m_tarfile, m_tar):
        assert not runner.write_tar(path, content)

    assert (
        list(m_tarfile.TarInfo.call_args)
        == [(str(path), ), {}])
    assert m_tarfile.TarInfo.return_value.size == 23
    assert (
        list(m_io.BytesIO.call_args)
        == [(m_utils.to_bytes.return_value, ), {}])
    assert (
        list(m_utils.to_bytes.call_args)
        == [(content, ), {}])
    assert (
        list(m_tar.return_value.addfile.call_args)
        == [(m_tarfile.TarInfo.return_value,
             m_io.BytesIO.return_value), {}])
