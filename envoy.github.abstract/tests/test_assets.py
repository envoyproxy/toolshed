
from functools import partial
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio import tasks
from aio.functional import async_property

from envoy.github.abstract import assets, exceptions


class DummyGithubReleaseAssets(assets.AGithubReleaseAssets):

    async def __aiter__(self):
        async for asset in super().__aiter__():
            yield asset

    @property
    def awaitables(self):
        return super().awaitables

    @property
    def concurrency(self):
        return super().concurrency

    @property
    def path(self):
        return super().path

    async def run(self):
        async for result in super().run():
            yield result


class DummyGithubReleaseAssetsFetcher(
        DummyGithubReleaseAssets, assets.AGithubReleaseAssetsFetcher):

    async def download(self, asset):
        return super().download(asset)

    async def save(self, asset):
        raise NotImplementedError


class DummyGithubReleaseAssetsPusher(
        DummyGithubReleaseAssets, assets.AGithubReleaseAssetsPusher):

    @property
    def artefacts(self):
        return super().artefacts

    async def upload(self, artefact, url):
        return super().upload(artefact, url)


def test_assets_constructor():
    release_assets = DummyGithubReleaseAssets("RELEASE", "PATH")
    assert release_assets.release == "RELEASE"
    assert release_assets._path == "PATH"
    assert release_assets.concurrency == 4

    assert release_assets.path == "PATH"
    assert "path" not in release_assets.__dict__


def _check_assets_property(patches, prop, arg=None):
    release = MagicMock()
    release_assets = DummyGithubReleaseAssets(release, "VERSION")
    assert getattr(release_assets, prop) == getattr(release, arg or prop)
    assert prop not in release_assets.__dict__


@pytest.mark.parametrize(
    "prop",
    [("github",),
     ("session",),
     ("version",)])
def test_assets_props(patches, prop):
    _check_assets_property(patches, *prop)


def test_assets_context(patches):
    release = DummyGithubReleaseAssets("RELEASE", "PATH")
    patched = patches(
        "AGithubReleaseAssets.cleanup",
        prefix="envoy.github.abstract.assets")

    with patched as (m_cleanup, ):
        with release as _release:
            pass

    assert _release is release
    assert m_cleanup.called


@pytest.mark.parametrize(
    "raises",
    [None, BaseException, tasks.ConcurrentIteratorError])
async def test_assets_dunder_aiter(patches, raises):
    release_assets = DummyGithubReleaseAssets("RELEASE", "PATH")
    patched = patches(
        "AGithubReleaseAssets.__enter__",
        "AGithubReleaseAssets.__exit__",
        ("AGithubReleaseAssets.run", dict(new_callable=MagicMock)),
        prefix="envoy.github.abstract.assets")
    _results = []

    async def _run():
        for x in range(0, 5):
            if x == 3 and raises:
                raise raises("AN ERROR OCCURRED")
            yield x

    with patched as (m_enter, m_exit, m_run):
        m_run.return_value = _run()
        m_enter.return_value = None
        m_exit.return_value = None
        if raises == BaseException:
            with pytest.raises(BaseException) as e:
                async for result in release_assets:
                    _results.append(result)
        elif raises:
            with pytest.raises(exceptions.GithubReleaseError) as e:
                async for result in release_assets:
                    _results.append(result)
        else:
            async for result in release_assets:
                _results.append(result)

    assert (
        list(m_run.call_args)
        == [(), {}])
    assert (
        list(m_enter.call_args)
        == [(), {}])

    if raises:
        assert (
            m_exit.call_args[0][0]
            == (raises
                if raises == BaseException
                else exceptions.GithubReleaseError))
        assert m_exit.call_args[0][1] == e.value
        assert _results == [0, 1, 2]
        assert e.value.args[0] == "AN ERROR OCCURRED"
        return

    assert (
        list(m_exit.call_args)
        == [(None, None, None), {}])
    assert _results == list(range(0, 5))


async def test_assets_assets(patches):

    async def mock_assets():
        return "ASSETS"

    release = MagicMock()
    release.assets = mock_assets()
    release_assets = DummyGithubReleaseAssets(release, "PATH")
    assert await release_assets.assets == "ASSETS"


def test_assets_tasks(patches):
    release_assets = DummyGithubReleaseAssets("RELEASE", "PATH")
    patched = patches(
        "concurrent",
        ("AGithubReleaseAssets.awaitables", dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.assets")
    release_assets._concurrency = 23

    with patched as (m_concurrent, m_await):
        assert release_assets.tasks == m_concurrent.return_value

    assert (
        list(m_concurrent.call_args)
        == [(m_await.return_value,), dict(limit=23)])
    assert "tasks" not in release_assets.__dict__


def test_assets_tempdir(patches):
    release_assets = DummyGithubReleaseAssets("RELEASE", "PATH")
    patched = patches(
        "tempfile",
        prefix="envoy.github.abstract.assets")

    with patched as (m_temp, ):
        assert release_assets.tempdir == m_temp.TemporaryDirectory.return_value

    assert (
        list(m_temp.TemporaryDirectory.call_args)
        == [(), {}])


@pytest.mark.parametrize("tempdir", [True, False])
def test_assets_cleanup(patches, tempdir):
    release_assets = DummyGithubReleaseAssets("RELEASE", "PATH")
    patched = patches(
        ("AGithubReleaseAssets.tempdir", dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.assets")
    if tempdir:
        release_assets.__dict__["tempdir"] = "TEMPDIR"

    with patched as (m_temp, ):
        assert not release_assets.cleanup()

    assert "tempdir" not in release_assets.__dict__
    if tempdir:
        assert (
            list(m_temp.return_value.cleanup.call_args)
            == [(), {}])
    else:
        assert not m_temp.called


def test_assets_fail():
    release = MagicMock()
    release_assets = DummyGithubReleaseAssets(release, "PATH")
    assert release_assets.fail("FAILURE") == release.fail.return_value
    assert (
        list(release.fail.call_args)
        == [("FAILURE", ), {}])


async def test_assets_handle_result():
    release_assets = DummyGithubReleaseAssets("RELEASE", "PATH")
    assert await release_assets.handle_result("RESULT") == "RESULT"


@pytest.mark.parametrize(
    "raises",
    [None,
     BaseException,
     tasks.ConcurrentIteratorError,
     tasks.ConcurrentError])
async def test_assets_run(patches, raises):
    release_assets = DummyGithubReleaseAssets("RELEASE", "PATH")
    patched = patches(
        "AGithubReleaseAssets.fail",
        ("AGithubReleaseAssets.tasks", dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.assets")
    results = []

    class SomeError(Exception):
        pass

    async def mock_tasks():
        if raises:
            raise raises(
                SomeError("AN ERROR OCCURRED")
                if raises == tasks.ConcurrentIteratorError
                else "AN ERROR OCCURRED")
        for x in range(0, 5):
            yield x

    with patched as (m_fail, m_task):
        m_task.side_effect = mock_tasks

        if not raises or raises == tasks.ConcurrentError:
            async for x in release_assets.run():
                results.append(x)
        else:
            exception = (
                BaseException
                if raises == BaseException
                else SomeError)
            with pytest.raises(exception) as e:
                async for x in release_assets.run():
                    pass
            assert not m_fail.called
            assert e.value.args[0] == "AN ERROR OCCURRED"
            return
    if raises:
        assert (
            list(m_fail.call_args)
            == [("AN ERROR OCCURRED", ), {}])
        assert results == [dict(error=m_fail.return_value)]
        return
    assert not m_fail.called
    assert results == list(range(0, 5))


@pytest.mark.parametrize(
    "asset_types",
    [None, "ASSET TYPES"])
@pytest.mark.parametrize(
    "append",
    [None, True, False])
def test_assets_fetcher_constructor(patches, asset_types, append):
    patched = patches(
        "AGithubReleaseAssets.__init__",
        prefix="envoy.github.abstract.assets")
    args = ("RELEASE", "PATH", asset_types)
    if append is not None:
        args += (append, )

    with patched as (m_super, ):
        fetcher = DummyGithubReleaseAssetsFetcher(*args)

    assert (
        list(m_super.call_args)
        == [("RELEASE", "PATH"), {}])
    assert fetcher._asset_types == asset_types
    assert fetcher._append == (append or False)

    assert fetcher.append == (append or False)
    assert "append" not in fetcher.__dict__


@pytest.mark.parametrize(
    "asset_types",
    [None, "ASSET TYPES"])
def test_assets_fetcher_asset_types(patches, asset_types):
    fetcher = DummyGithubReleaseAssetsFetcher("RELEASE", "PATH")
    patched = patches(
        "re",
        prefix="envoy.github.abstract.assets")
    fetcher._asset_types = asset_types

    with patched as (m_re, ):
        assert (
            fetcher.asset_types
            == (asset_types
                if asset_types
                else dict(assets=m_re.compile.return_value)))

    if not asset_types:
        assert (
            list(m_re.compile.call_args)
            == [(".*", ), {}])
    else:
        assert not m_re.compile.called


@pytest.mark.parametrize(
    "asset_types",
    [(), range(0, 5), range(0, 3), range(3, 7)])
async def test_assets_fetcher_awaitables(patches, asset_types):
    fetcher = DummyGithubReleaseAssetsFetcher("RELEASE", "PATH")
    patched = patches(
        "AGithubReleaseAssetsFetcher.asset_type",
        "AGithubReleaseAssetsFetcher.download",
        ("AGithubReleaseAssetsFetcher.assets",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.assets")
    results = []
    asset_types = [f"ASSET{i}" for i in asset_types]

    def asset_type(asset):
        return (
            asset["name"]
            if asset["name"] in asset_types
            else None)

    returned_assets = [
        dict(name=f"ASSET{i}") for i in range(0, 5)]

    with patched as (m_type, m_download, m_assets):
        m_assets.side_effect = AsyncMock(
            return_value=returned_assets)
        m_type.side_effect = asset_type
        async for result in fetcher.awaitables:
            results.append(await result)

    assert (
        results
        == [m_download.return_value
            for x in returned_assets
            if x["name"] in asset_types])
    assert (
        list(list(c) for c in m_type.call_args_list)
        == [[(asset,), {}] for asset in returned_assets])
    assert (
        list(list(c) for c in m_download.call_args_list)
        == [[({'name': asset["name"], 'asset_type': asset["name"]},), {}]
            for asset in returned_assets
            if asset["name"] in asset_types])


@pytest.mark.parametrize("append", [True, False])
def test_assets_fetcher_write_mode(patches, append):
    fetcher = DummyGithubReleaseAssetsFetcher("RELEASE", "PATH")
    patched = patches(
        ("AGithubReleaseAssetsFetcher.append",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.assets")

    with patched as (m_append, ):
        m_append.return_value = append
        assert fetcher.write_mode == {True: "a", False: "w"}[append]


@pytest.mark.parametrize("name", [None, "foo0", "bar2", "baz23"])
def test_assets_fetcher_asset_type(patches, name):
    fetcher = DummyGithubReleaseAssetsFetcher("RELEASE", "PATH")
    patched = patches(
        ("AGithubReleaseAssetsFetcher.asset_types",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.assets")

    types = {}
    for t in ["foo", "bar", "baz"]:
        for i in range(0, 3):
            mock_type = MagicMock()

            def _search(x, y, name):
                return name == f"{x}{y}"

            mock_type.search = partial(_search, t, i)
            types[f"{t}{i}"] = mock_type

    with patched as (m_types, ):
        m_types.return_value = types
        assert (
            fetcher.asset_type(dict(name=name))
            == (name if name in types else None))


async def test_assets_pusher_asset_names(patches):
    pusher = DummyGithubReleaseAssetsPusher("RELEASE", "PATH")
    patched = patches(
        ("AGithubReleaseAssetsPusher.release",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.assets")

    with patched as (m_release, ):
        m_release.return_value.asset_names = AsyncMock(
            return_value="ASSET NAMES")()
        assert await pusher.asset_names == "ASSET NAMES"

    assert not hasattr(pusher, async_property.cache_name)


async def test_assets_pusher_awaitables(patches):
    pusher = DummyGithubReleaseAssetsPusher("RELEASE", "PATH")
    patched = patches(
        "AGithubReleaseAssetsPusher.artefact_url",
        "AGithubReleaseAssetsPusher.upload",
        ("AGithubReleaseAssetsPusher.artefacts",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.assets")
    results = []
    artefacts = [
        MagicMock() for i in range(0, 5)]

    with patched as (m_url, m_upload, m_artefacts):
        m_artefacts.return_value = artefacts
        async for result in pusher.awaitables:
            results.append(await result)

    assert results == [m_upload.return_value for i in range(0, 5)]
    assert (
        list(list(c) for c in m_upload.call_args_list)
        == [[(artefact, m_url.return_value), {}]
            for artefact in artefacts])
    assert (
        list(list(c) for c in m_url.call_args_list)
        == [[(artefact.name,), {}]
            for artefact in artefacts])


async def test_assets_pusher_upload_url(patches):
    pusher = DummyGithubReleaseAssetsPusher("RELEASE", "PATH")
    patched = patches(
        ("AGithubReleaseAssetsPusher.release",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.assets")

    with patched as (m_release, ):
        m_release.return_value.upload_url = AsyncMock(
            return_value="UPLOAD URL")()
        assert await pusher.upload_url == "UPLOAD URL"
    assert not hasattr(pusher, async_property.cache_name)


async def test_assets_pusher_artefact_url(patches):
    pusher = DummyGithubReleaseAssetsPusher("RELEASE", "PATH")
    patched = patches(
        ("AGithubReleaseAssetsPusher.upload_url",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.assets")

    with patched as (m_url, ):
        m_url.side_effect = AsyncMock(return_value="UPLOAD URL")
        assert (
            await pusher.artefact_url("ARTEFACT")
            == "UPLOAD URL?name=ARTEFACT")
