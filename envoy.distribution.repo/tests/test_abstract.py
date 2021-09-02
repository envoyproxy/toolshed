
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from envoy.base.runner import AsyncRunner
from envoy.base import utils
from envoy.distribution import repo


@abstracts.implementer(repo.ARepoBuildingRunner)
class DummyRepoBuildingRunner:

    def add_arguments(self, parser):
        super().add_arguments(parser)

    async def run(self):
        return await super().run()


@abstracts.implementer(repo.ARepoManager)
class DummyRepoManager:

    @classmethod
    def add_arguments(cls, parser):
        repo.ARepoManager.add_arguments(cls, parser)

    async def publish(self):
        return await super().publish()


def test_repo_buildingrunner_constructor():
    runner = DummyRepoBuildingRunner()
    assert isinstance(runner, AsyncRunner)

    assert runner._repo_types == ()
    repo_types = tuple(
        (f"TYPE{i}", f"MATCH{i}")
        for i in range(0, 5))
    runner._repo_types = repo_types
    assert runner.repo_types == dict(repo_types)
    assert "repo_types" in runner.__dict__


def test_repo_buildingrunner_register_repo_type():
    assert DummyRepoBuildingRunner._repo_types == ()

    class RepoType1(object):
        pass

    class RepoType2(object):
        pass

    DummyRepoBuildingRunner.register_repo_type("repo_type1", RepoType1)
    assert (
        DummyRepoBuildingRunner._repo_types
        == (('repo_type1', RepoType1),))

    DummyRepoBuildingRunner.register_repo_type("repo_type2", RepoType2)
    assert (
        DummyRepoBuildingRunner._repo_types
        == (('repo_type1', RepoType1),
            ('repo_type2', RepoType2),))


def test_repo_buildingrunner_asset_types(patches):
    runner = DummyRepoBuildingRunner()
    patched = patches(
        "re",
        ("ARepoBuildingRunner.repo_types",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.abstract")

    class DummyManager:

        def __init__(self, file_types):
            self.file_types = file_types

    repo_types = {
        f"TYPE{i}": DummyManager(f"MATCH{i}")
        for i in range(0, 5)}

    with patched as (m_re, m_types):
        m_types.return_value = repo_types
        assert (
            runner.asset_types
            == {f"TYPE{i}": m_re.compile.return_value
                for i in range(0, 5)})

    assert (
        list(list(c) for c in m_re.compile.call_args_list)
        == [[(v.file_types, ), {}] for v in repo_types.values()])
    assert "asset_types" in runner.__dict__


def test_repo_buildingrunner_path(patches):
    runner = DummyRepoBuildingRunner()
    patched = patches(
        "pathlib",
        ("ARepoBuildingRunner.tempdir",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.abstract")

    with patched as (m_plib, m_temp):
        assert (
            runner.path
            == m_plib.Path.return_value)

    assert (
        list(m_plib.Path.call_args)
        == [(m_temp.return_value.name, ), {}])
    assert "path" in runner.__dict__


@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("casts", [True, False])
def test_repo_buildingrunner_release_config(patches, exists, casts):
    runner = DummyRepoBuildingRunner()
    patched = patches(
        "utils",
        ("ARepoBuildingRunner.release_config_file",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.abstract")

    with patched as (m_utils, m_config):
        m_utils.TypeCastingError = utils.TypeCastingError
        if not exists:
            m_config.return_value.exists.return_value = False
        if not casts:
            m_utils.typed.side_effect = utils.TypeCastingError
        if not exists or not casts:
            with pytest.raises(repo.RepoError) as e:
                runner.release_config
        else:
            assert (
                runner.release_config
                == m_utils.typed.return_value)

    assert (
        list(m_config.return_value.exists.call_args)
        == [(), {}])

    if not exists:
        assert (
            e.value.args[0]
            == ("Unable to find release configuration: "
                f"{m_config.return_value}"))
        assert not m_utils.typed.called
        assert not m_utils.from_yaml.called
        return
    assert (
        list(m_utils.typed.call_args)
        == [(repo.ReleaseConfigDict,
             m_utils.from_yaml.return_value),
            {}])
    assert (
        list(m_utils.from_yaml.call_args)
        == [(m_config.return_value, ), {}])
    if not casts:
        assert (
            e.value.args[0]
            == ("Unable to parse release configuration: "
                f"{m_config.return_value}"))
        return

    assert "release_config" in runner.__dict__


def test_repo_buildingrunner_releaes_config_file(patches):
    runner = DummyRepoBuildingRunner()
    patched = patches(
        "pathlib",
        prefix="envoy.distribution.repo.abstract")

    with patched as (m_plib, ):
        assert (
            runner.release_config_file
            == m_plib.Path.return_value)

    assert (
        list(m_plib.Path.call_args)
        == [(repo.abstract.PUBLISH_YAML, ), {}])
    assert "release_config_file" not in runner.__dict__


def test_repo_buildingrunner_repos(patches):
    runner = DummyRepoBuildingRunner()
    patched = patches(
        "ARepoBuildingRunner._kwargs_for_type",
        ("ARepoBuildingRunner.log",
         dict(new_callable=PropertyMock)),
        ("ARepoBuildingRunner.path",
         dict(new_callable=PropertyMock)),
        ("ARepoBuildingRunner.release_config",
         dict(new_callable=PropertyMock)),
        ("ARepoBuildingRunner.repo_types",
         dict(new_callable=PropertyMock)),
        ("ARepoBuildingRunner.stdout",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.abstract")
    repo_types = {
        f"TYPE{i}": MagicMock()
        for i in range(0, 5)}

    with patched as patchy:
        (m_kwargs, m_log, m_path, m_config,
         m_types, m_stdout) = patchy
        m_types.return_value = repo_types
        assert (
            runner.repos
            == {k: v.return_value
                for k, v in repo_types.items()})

    for k, v in repo_types.items():
        assert (
            list(v.call_args)
            == [(k,
                 m_path.return_value,
                 m_config.return_value,
                 m_log.return_value,
                 m_stdout.return_value),
                {}])


@pytest.mark.asyncio
async def test_repo_buildingrunner_published_repos(patches):
    runner = DummyRepoBuildingRunner()
    patched = patches(
        ("ARepoBuildingRunner.repos",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.abstract")
    repos = [AsyncMock() for i in range(0, 5)]
    results = []

    with patched as (m_repos, ):
        m_repos.return_value.values.return_value = repos
        async for published in runner.published_repos:
            results.append(published)

    assert results == [m.publish.return_value for m in repos]
    for m in repos:
        assert (
            list(m.publish.call_args)
            == [(), {}])


def test_repo_buildingrunner_add_arguments(patches):
    runner = DummyRepoBuildingRunner()
    patched = patches(
        "runner.AsyncRunner.add_arguments",
        ("ARepoBuildingRunner.repo_types",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.abstract")
    repo_types = {
        f"TYPE{i}": MagicMock()
        for i in range(0, 5)}
    parser = MagicMock()

    with patched as (m_super, m_types):
        m_types.return_value = repo_types
        assert not runner.add_arguments(parser)

    assert (
        list(m_super.call_args)
        == [(parser, ), {}])

    for manager in repo_types.values():
        assert (
            list(manager.add_arguments.call_args)
            == [(parser, ), {}])


@pytest.mark.asyncio
async def test_repo_buildingrunner_cleanup(patches):
    runner = DummyRepoBuildingRunner()
    patched = patches(
        "runner.AsyncRunner.cleanup",
        prefix="envoy.distribution.repo.abstract")

    with patched as (m_super, ):
        assert not await runner.cleanup()

    assert (
        list(m_super.call_args)
        == [(), {}])


@pytest.mark.asyncio
async def test_repo_buildingrunner_run():
    runner = DummyRepoBuildingRunner()

    with pytest.raises(NotImplementedError):
        await runner.run()


@pytest.mark.parametrize(
    "repo_type", [f"TYPE{i}" for i in range(0, 4)])
def test_repo_buildingrunner__kwargs_for_type(patches, repo_type):
    runner = DummyRepoBuildingRunner()
    patched = patches(
        ("ARepoBuildingRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.repo.abstract")

    class DummyArgs:

        def __init__(self):
            self.TYPE1_a = "VAL1A"
            self.TYPE1_b = "VAL1B"
            self.TYPE1_c = "VAL1C"
            self.TYPE2_a = "VAL2"
            self.TYPE3_a = "VAL3"

    args = DummyArgs()

    expected = {}
    for k, v in vars(args).items():
        if k.startswith(repo_type):
            expected[k[len(repo_type) + 1:]] = v

    with patched as (m_args, ):
        m_args.return_value = DummyArgs()
        assert (
            runner._kwargs_for_type(repo_type)
            == expected)


def test_repo_manager_constructor():
    manager = DummyRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")
    assert manager.file_types == r"^$"
    assert manager.name == "NAME"
    assert manager.path == "PATH"
    assert manager.config == "CONFIG"
    assert manager.log == "LOG"
    assert manager.stdout == "STDOUT"


def test_repo_manager_add_arguments():
    with pytest.raises(NotImplementedError):
        DummyRepoManager.add_arguments("PARSER")


def test_repo_manager_architectures():
    config = dict(architectures="ARCHITECTURES")
    manager = DummyRepoManager(
        "NAME", "PATH", config, "LOG", "STDOUT")
    assert manager.architectures == "ARCHITECTURES"


def test_repo_manager_versions():
    config = dict(
        versions=dict(
            V1=dict(NAME="foo", OTHER="bar"),
            V2=dict(OTHER="bar"),
            V3=dict(NAME="baz", OTHER="bar")))
    manager = DummyRepoManager(
        "NAME", "PATH", config, "LOG", "STDOUT")
    assert (
        manager.versions
        == {'V1': 'foo', 'V3': 'baz'})


@pytest.mark.asyncio
async def test_repo_manager_publish():
    manager = DummyRepoManager(
        "NAME", "PATH", "CONFIG", "LOG", "STDOUT")

    with pytest.raises(NotImplementedError):
        assert not await manager.publish()
