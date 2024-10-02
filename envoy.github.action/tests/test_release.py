
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import gidgethub

from aio.core import tasks
from aio.core.functional import async_property

from envoy.github.abstract import exceptions
from envoy.github.action import (
    GithubAction, GithubActionAssetsFetcher, GithubActionAssetsPusher)


def test_action_constructor():
    action = GithubAction("MANAGER", "VERSION")
    assert action.manager == "MANAGER"
    assert action.version == "VERSION"

    assert action.fetcher == GithubActionAssetsFetcher
    assert "fetcher" not in action.__dict__
    assert action.pusher == GithubActionAssetsPusher
    assert "pusher" not in action.__dict__


def _check_manager_property(prop, arg=None):
    _manager = MagicMock()
    checker = GithubAction(_manager, "VERSION")
    assert getattr(checker, prop) == getattr(_manager, arg or prop)
    assert prop not in checker.__dict__


@pytest.mark.parametrize(
    "prop",
    [("github",),
     ("log",),
     ("actions_url",),
     ("session",)])
def test_action_manager_props(prop):
    _check_manager_property(*prop)


async def test_action_asset_names(patches):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        ("GithubAction.assets", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.action")
    _assets = [MagicMock(), MagicMock()]

    with patched as (m_assets, ):
        m_assets.side_effect = AsyncMock(return_value=_assets)
        assert (
            await action.asset_names
            == set(m.__getitem__.return_value for m in _assets))

    for _asset in _assets:
        assert (
            _asset.__getitem__.call_args
            == [('name',), {}])

    assert "asset_names" in action.__async_prop_cache__


@pytest.mark.parametrize(
    "raises",
    [None, BaseException, gidgethub.GitHubException])
async def test_action_assets(patches, raises):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        ("GithubAction.assets_url", dict(new_callable=PropertyMock)),
        ("GithubAction.github", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.action")

    with patched as (m_url, m_github):
        _get = AsyncMock()
        _url = AsyncMock()
        m_github.return_value.getitem.side_effect = _get
        m_url.side_effect = _url
        if raises:
            _get.side_effect = raises("AN ERROR OCCURRED")
            _raises = (
                exceptions.GithubActionError
                if raises == gidgethub.GitHubException
                else raises)
            with pytest.raises(_raises):
                await action.assets
        else:
            assert (
                await action.assets
                == _get.return_value)

    assert (
        _get.call_args
        == [(_url.return_value,), {}])
    if not raises:
        assert "assets" in action.__async_prop_cache__


async def test_action_assets_url(patches):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        ("GithubAction.action", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.action")

    with patched as (m_action, ):
        _action = AsyncMock()
        m_action.side_effect = _action
        assert (
            await action.assets_url
            == _action.return_value.__getitem__.return_value)

    assert (
        _action.return_value.__getitem__.call_args
        == [('assets_url',), {}])
    assert "assets_url" in getattr(action, async_property.cache_name)


async def test_action_delete_url(patches):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        ("GithubAction.actions_url", dict(new_callable=PropertyMock)),
        ("GithubAction.action_id", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.action")

    with patched as (m_url, m_id):
        _id = AsyncMock()
        m_id.side_effect = _id
        assert (
            await action.delete_url
            == m_url.return_value.joinpath.return_value)

    assert (
        m_url.return_value.joinpath.call_args
        == [(str(_id.return_value), ), {}])
    assert "delete_url" in getattr(action, async_property.cache_name)


@pytest.mark.parametrize("version", [f"VERSION{i}" for i in range(0, 7)])
async def test_action_exists(patches, version):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        ("GithubAction.action_names", dict(new_callable=PropertyMock)),
        ("GithubAction.version_name", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.action")
    _versions = [f"VERSION{i}" for i in range(3, 5)]

    with patched as (m_action, m_name):
        m_name.return_value = version
        m_action.side_effect = AsyncMock(return_value=_versions)
        assert await action.exists == (version in _versions)

    assert not hasattr(action, async_property.cache_name)


async def test_action_action(patches):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        ("GithubAction.get", dict(new_callable=AsyncMock)),
        prefix="envoy.github.action.action")

    with patched as (m_get, ):
        assert await action.action == m_get.return_value

    assert "action" in getattr(action, async_property.cache_name)


async def test_action_action_id(patches):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        ("GithubAction.action", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.action")

    with patched as (m_action, ):
        _action = AsyncMock()
        m_action.side_effect = _action
        assert (
            await action.action_id
            == _action.return_value.__getitem__.return_value)

    assert (
        _action.return_value.__getitem__.call_args
        == [('id',), {}])
    assert "action_id" in getattr(action, async_property.cache_name)


async def test_action_action_names(patches):
    _manager = MagicMock()

    _action_names = [dict(tag_name=f"TAG{i}") for i in range(0, 3)]

    async def _actions():
        return _action_names

    _manager.actions = _actions()
    action = GithubAction(_manager, "VERSION")
    assert (
        await action.action_names
        == tuple(t["tag_name"] for t in _action_names))


async def test_action_upload_url(patches):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        ("GithubAction.action", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.action")

    with patched as (m_action, ):
        _action = AsyncMock()
        m_action.side_effect = _action
        split = _action.return_value.__getitem__.return_value.split
        assert (
            await action.upload_url
            == split.return_value.__getitem__.return_value)

    assert (
        _action.return_value.__getitem__.call_args
        == [('upload_url',), {}])
    assert (
        split.call_args
        == [('{',), {}])
    assert (
        split.return_value.__getitem__.call_args
        == [(0,), {}])
    assert "upload_url" in action.__async_prop_cache__


def test_action_version_name(patches):
    _manager = MagicMock()
    action = GithubAction(_manager, "VERSION")
    action.version_name == _manager.format_version.return_value
    assert (
        _manager.format_version.call_args
        == [("VERSION",), {}])


def test_action_version_url(patches):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        ("GithubAction.actions_url", dict(new_callable=PropertyMock)),
        ("GithubAction.version_name", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.action")

    with patched as (m_actions, m_version):
        assert (
            action.version_url
            == m_actions.return_value.joinpath.return_value)

    assert (
        m_actions.return_value.joinpath.call_args
        == [("tags", m_version.return_value), {}])
    assert "version_url" in action.__dict__


@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize(
    "assets",
    [None, [], [f"ASSET{i}" for i in range(0, 3)]])
@pytest.mark.parametrize(
    "raises",
    [None, BaseException, gidgethub.GitHubException])
async def test_action_create(patches, exists, assets, raises):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        "GithubAction.fail",
        ("GithubAction.push", dict(new_callable=AsyncMock)),
        ("GithubAction.exists", dict(new_callable=PropertyMock)),
        ("GithubAction.github", dict(new_callable=PropertyMock)),
        ("GithubAction.log", dict(new_callable=PropertyMock)),
        ("GithubAction.actions_url", dict(new_callable=PropertyMock)),
        ("GithubAction.version_name", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.action")
    args = (
        (assets, )
        if assets is not None
        else ())

    with patched as patchy:
        (m_fail, m_push, m_exists, m_github,
         m_log, m_url, m_version) = patchy
        m_exists.side_effect = AsyncMock(return_value=exists)
        m_push.return_value = dict(PUSHED=True)
        m_github.return_value.post = AsyncMock()
        if raises:
            m_github.return_value.post.side_effect = raises(
                "AN ERROR OCCURRED")
        if raises and not exists:
            _raises = (
                exceptions.GithubActionError
                if raises == gidgethub.GitHubException
                else raises)
            with pytest.raises(_raises):
                await action.create(*args)
        else:
            result = await action.create(*args)

    expected = {}
    if not exists:
        assert (
            m_log.return_value.notice.call_args
            == [("Creating action VERSION", ), {}])
        assert (
            m_github.return_value.post.call_args
            == [(str(m_url.return_value), ),
                dict(data=dict(tag_name=m_version.return_value))])
        assert not m_fail.called
        if not raises:
            expected["action"] = m_github.return_value.post.return_value
            assert (
                m_log.return_value.success.call_args
                == [("Action created VERSION", ), {}])
        else:
            assert not m_log.return_value.success.called
    else:
        assert not m_github.return_value.post.called
        assert not m_log.called
        assert (
            m_fail.call_args
            == [(f"Action {m_version.return_value} already exists", ), {}])

    if not exists and raises:
        assert not m_push.called
        return
    if assets:
        expected["PUSHED"] = True
        assert (
            m_push.call_args
            == [(assets, ), {}])
    else:
        assert not m_push.called
    assert result == expected


@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize(
    "raises",
    [None, BaseException, gidgethub.GitHubException])
async def test_action_delete(patches, exists, raises):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        ("GithubAction.delete_url", dict(new_callable=PropertyMock)),
        ("GithubAction.exists", dict(new_callable=PropertyMock)),
        ("GithubAction.github", dict(new_callable=PropertyMock)),
        ("GithubAction.log", dict(new_callable=PropertyMock)),
        ("GithubAction.version_name", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.action")

    with patched as (m_url, m_exists, m_github, m_log, m_version):
        _url = AsyncMock()
        m_url.side_effect = _url
        m_exists.side_effect = AsyncMock(return_value=exists)
        m_github.return_value.delete = AsyncMock()
        if raises:
            m_github.return_value.delete.side_effect = raises(
                "AN ERROR OCCURRED")

        if exists and not raises:
            assert not await action.delete()
        elif raises == BaseException:
            with pytest.raises(BaseException) as e:
                await action.delete()
        else:
            with pytest.raises(exceptions.GithubActionError) as e:
                await action.delete()

        if not exists:
            assert (
                e.value.args[0]
                == (f"Unable to delete version {m_version.return_value} "
                    "as it does not exist"))
            assert not m_log.called
            assert not m_github.called
            return
        assert (
            m_log.return_value.notice.call_args
            == [(f"Deleting action version: {m_version.return_value}", ), {}])
        assert (
            m_github.return_value.delete.call_args
            == [(str(_url.return_value), ), {}])
        if raises:
            assert not m_log.return_value.success.called
            return
        assert (
            m_log.return_value.success.call_args
            == [(f"Action version deleted: {m_version.return_value}", ), {}])


def test_action_fail():
    manager = MagicMock()
    action = GithubAction(manager, "VERSION")
    assert action.fail("FAILURE") == manager.fail.return_value
    assert (
        manager.fail.call_args
        == [("FAILURE", ), {}])


@pytest.mark.parametrize(
    "asset_types",
    [None, (), tuple(f"ASSET_TYPE{i}" for i in range(0, 3))])
@pytest.mark.parametrize("errors", [[], [0], [2, 4], range(0, 5)])
async def test_action_fetch(patches, asset_types, errors):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        ("GithubAction.fetcher", dict(new_callable=PropertyMock)),
        ("GithubAction.log", dict(new_callable=PropertyMock)),
        ("GithubAction.version_name", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.action")

    kwargs = {} if asset_types is None else dict(asset_types=asset_types)
    fetched = MagicMock()

    async def _fetcher(_actionr, path, asset_types, append=False):
        fetched(_actionr, path, asset_types, append)
        for x in range(0, 5):
            response = dict(name=f"FETCHED{x}")
            if x in errors:
                response["error"] = f"ERROR{x}"
            else:
                response["outfile"] = f"OUTFILE{x}"
            yield response
    expected = dict(
        errors=[
            dict(name=f"FETCHED{i}", error=f"ERROR{i}")
            for i in errors],
        assets=[
            dict(name=f"FETCHED{i}", outfile=f"OUTFILE{i}")
            for i in range(0, 5) if i not in errors])

    with patched as (m_fetcher, m_log, m_version):
        m_fetcher.return_value = _fetcher
        assert await action.fetch("PATH", **kwargs) == expected

    assert (
        m_log.return_value.notice.call_args
        == [(("Downloading assets for action version: "
              f"{m_version.return_value} -> PATH"), ), {}])
    assert (
        fetched.call_args
        == [(action, 'PATH', asset_types, False), {}])


@pytest.mark.parametrize(
    "raises",
    [None, BaseException, gidgethub.GitHubException])
async def test_action_get(patches, raises):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        ("GithubAction.version_url", dict(new_callable=PropertyMock)),
        ("GithubAction.github", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.action")

    with patched as (m_url, m_github):
        m_github.return_value.getitem = AsyncMock()
        if raises:
            m_github.return_value.getitem.side_effect = raises(
                "AN ERROR OCCURRED")
            _raises = (
                exceptions.GithubActionError
                if raises == gidgethub.GitHubException
                else raises)
            with pytest.raises(_raises):
                await action.get()
        else:
            assert (
                await action.get()
                == m_github.return_value.getitem.return_value)
    assert (
        m_github.return_value.getitem.call_args
        == [(str(m_url.return_value), ), {}])


@pytest.mark.parametrize(
    "raises",
    [None, BaseException, tasks.ConcurrentError])
@pytest.mark.parametrize("errors", [[], [1, 3], range(0, 5)])
async def test_action_push(patches, raises, errors):
    action = GithubAction("MANAGER", "VERSION")
    patched = patches(
        ("GithubAction.log", dict(new_callable=PropertyMock)),
        ("GithubAction.pusher", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.action")
    artefacts = [f"ARTEFACTS{i}" for i in range(0, 5)]
    expected = dict(assets=[], errors=[])

    for i in range(0, 5):
        for x in range(0, 5):
            result = dict(
                name=f"ARTEFACTS{i}_ASSET{x}",
                foo=f"ARTEFACTS{i}_BAR{x}")
            if x in errors:
                result["error"] = f"GOT AN ERROR ARTEFACTS{i} {x}"
                expected["errors"].append(result)
            else:
                expected["assets"].append(result)

    class SomeError(Exception):
        pass

    async def _pusher(path):
        if raises:
            raise raises(SomeError("AN ERROR OCCURRED"))
        for i in range(0, 5):
            response = dict(
                name=f"{path}_ASSET{i}",
                foo=f"{path}_BAR{i}")
            if i in errors:
                response["error"] = f"GOT AN ERROR {path} {i}"
            yield response

    with patched as (m_log, m_pusher):
        m_pusher.return_value.side_effect = lambda _self, path: _pusher(path)
        if raises:
            exception = (
                BaseException
                if raises == BaseException
                else SomeError)
            with pytest.raises(exception):
                await action.push(artefacts)
        else:
            assert await action.push(artefacts) == expected

    assert (
        m_log.return_value.notice.call_args
        == [("Pushing assets for VERSION", ), {}])

    if raises:
        assert (
            m_pusher.return_value.call_args_list
            == [[(action, 'ARTEFACTS0'), {}]])
        assert not m_log.return_value.info.called
    else:
        assert (
            m_pusher.return_value.call_args_list
            == [[(action, f'ARTEFACTS{x}'), {}] for x in range(0, 5)])

    if raises or errors:
        assert not m_log.return_value.success.called
    else:
        assert (
            m_log.return_value.success.call_args
            == [("Assets uploaded: VERSION", ), {}])
        assert (
            m_log.return_value.info.call_args_list
            == [[(f'Action file uploaded ARTEFACTS{i}_ASSET{x}',), {}]
                for i in range(0, 5)
                for x in range(0, 5)])
