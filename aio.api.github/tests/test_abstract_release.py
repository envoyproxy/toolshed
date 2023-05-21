
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from packaging import version

import abstracts

from aio.api import github


@abstracts.implementer(github.AGithubRelease)
class DummyGithubRelease:

    @property
    def assets_class(self):
        return super().assets_class


@pytest.mark.parametrize("dry_run", [True, False])
async def test_abstract_release_create(patches, dry_run):
    repo = MagicMock()
    repo.post = AsyncMock()
    data = MagicMock()
    patched = patches(
        "datetime",
        "dict",
        "AGithubRelease.__init__",
        prefix="aio.api.github.abstract.release")

    with patched as (m_dt, m_dict, m_init):
        m_init.return_value = None
        release = await DummyGithubRelease.create(repo, data, dry_run=dry_run)

    assert isinstance(release, github.IGithubRelease)
    if dry_run:
        assert (
            m_init.call_args
            == [(repo, data), {}])
        assert not repo.post.called
        assert data.update.call_args == [(m_dict.return_value, ), {}]
        assert m_dt.now.call_args == [(), {}]
        assert m_dt.now.return_value.isoformat.call_args == [(), {}]
        assert (
            data.__getitem__.call_args
            == [("tag_name",), {}])
        release_url = f"test://releases/{data.__getitem__.return_value}"
        assert (
            m_dict.call_args
            == [(),
                dict(published_at=m_dt.now.return_value.isoformat.return_value,
                     upload_url=f"{release_url}/upload",
                     html_url=release_url)])
        return
    assert not m_dt.now.called
    assert not m_dict.called
    assert not data.__getitem__.called
    assert (
        m_init.call_args
        == [(repo, repo.post.return_value), {}])
    assert (
        repo.post.call_args
        == [("releases", data), {}])


def test_abstract_release_constructor(iters, patches):
    args = iters(tuple, count=3)
    kwargs = iters(dict, count=3)
    patched = patches(
        "GithubRepoEntity.__init__",
        prefix="aio.api.github.abstract.release")

    with patched as (m_super, ):
        m_super.return_value = None
        release = DummyGithubRelease(*args, **kwargs)

    assert isinstance(release, github.abstract.base.GithubRepoEntity)
    assert (
        m_super.call_args
        == [args, kwargs])


def test_abstract_release_dunder_str(patches):
    repo = MagicMock()
    release = DummyGithubRelease(repo, "DATA")
    patched = patches(
        ("AGithubRelease.tag_name",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.release")

    with patched as (m_tag, ):
        assert (
            str(release)
            == (f"<{release.__class__.__name__} "
                f"{repo.name}@{m_tag.return_value}>"))


def test_abstract_release_dunder_data(patches):
    release = DummyGithubRelease("REPO", "DATA")
    patched = patches(
        "dict",
        "utils",
        prefix="aio.api.github.abstract.release")

    with patched as (m_dict, m_utils):
        assert release.__data__ == m_dict.return_value

    assert (
        m_dict.call_args
        == [(),
            dict(created_at=m_utils.dt_from_js_isoformat,
                 published_at=m_utils.dt_from_js_isoformat)])

    assert "__data__" in release.__dict__


def test_abstract_release_assets(patches):
    release = DummyGithubRelease("REPO", "DATA")
    patched = patches(
        ("AGithubRelease.assets_class",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.release")

    with patched as (m_cls, ):
        assert release.assets == m_cls.return_value.return_value

    assert (
        m_cls.return_value.call_args
        == [(release, ), {}])
    assert "assets" in release.__dict__


def test_abstract_release_tag_name():
    release = DummyGithubRelease("REPO", "DATA")
    release.data = MagicMock()
    assert (
        release.tag_name
        == release.data.__getitem__.return_value)

    assert "tag_name" not in release.__dict__


def test_abstract_release_upload_url():
    release = DummyGithubRelease("REPO", "DATA")
    release.data = MagicMock()
    assert (
        release.upload_url
        == release.data.__getitem__.return_value)

    assert "upload_url" not in release.__dict__


@pytest.mark.parametrize("raises", [None, Exception, version.InvalidVersion])
def test_abstract_release_version(patches, raises):
    release = DummyGithubRelease("REPO", "DATA")
    patched = patches(
        "version.parse",
        ("AGithubRelease.tag_name",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.release")

    with patched as (m_version, m_tag):
        if raises:
            m_version.side_effect = raises("AN ERROR OCCURRED")
        if raises == Exception:
            with pytest.raises(Exception):
                release.version
        elif not raises:
            assert release.version == m_version.return_value
        else:
            assert not release.version

    assert (
        m_version.call_args
        == [(m_tag.return_value, ), {}])

    if raises != Exception:
        assert "version" in release.__dict__
    else:
        assert "version" not in release.__dict__


def test_abstract_release_assets_constructor():
    assets = github.AGithubReleaseAssets("RELEASE")
    assert assets.release == "RELEASE"
    assert "release" not in assets.__dict__


def test_abstract_release_assets_upload_url(patches):
    assets = github.AGithubReleaseAssets("RELEASE")
    patched = patches(
        ("AGithubReleaseAssets.release",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.release")

    with patched as (m_release, ):
        m_split = m_release.return_value.upload_url.split
        assert (
            assets.upload_url
            == m_split.return_value.__getitem__.return_value)

    assert (
        m_split.call_args
        == [("{", ), {}])
    assert (
        m_split.return_value.__getitem__.call_args
        == [(0, ), {}])
    assert "upload_url" not in assets.__dict__


def test_abstract_release_assets_artefact_url(patches):
    assets = github.AGithubReleaseAssets("RELEASE")
    patched = patches(
        ("AGithubReleaseAssets.upload_url",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.release")
    name = MagicMock()

    with patched as (m_upload, ):
        assert (
            assets.artefact_url(name)
            == f"{m_upload.return_value}?name={name}")


@pytest.mark.parametrize("dry_run", [True, False])
async def test_abstract_release_assets_push(patches, iters, dry_run):
    assets = github.AGithubReleaseAssets("RELEASE")
    patched = patches(
        "concurrent",
        "AGithubReleaseAssets.artefact_url",
        ("AGithubReleaseAssets.upload",
         dict(new_callable=MagicMock)),
        prefix="aio.api.github.abstract.release")
    path = MagicMock()
    path.glob.return_value = iters(cb=lambda x: MagicMock())
    _results = iters()
    results = []

    async def concurrent(awaitables, limit):
        for item in _results:
            yield item

    with patched as (m_conc, m_url, m_upload):
        m_conc.side_effect = concurrent
        async for result in assets.push(path, dry_run):
            results.append(result)
        resultiters = m_conc.call_args[0][0]
        resultlist = list(resultiters)

    assert results == _results
    assert isinstance(resultiters, types.GeneratorType)
    assert (
        resultlist
        == [m_upload.return_value] * len(path.glob.return_value))
    assert (
        path.glob.call_args
        == [("*", ), {}])
    assert (
        m_upload.call_args_list
        == [[(p, m_url.return_value), dict(dry_run=dry_run)]
            for p
            in path.glob.return_value])
    assert (
        m_conc.call_args
        == [(resultiters, ),
            dict(limit=github.AGithubReleaseAssets._concurrency)])


@pytest.mark.parametrize("errored", [True, False])
@pytest.mark.parametrize("uploaded", [True, False])
@pytest.mark.parametrize("dry_run", [True, False])
async def test_abstract_release_assets_upload(
        patches, errored, uploaded, dry_run):
    assets = github.AGithubReleaseAssets("RELEASE")
    patched = patches(
        "dict",
        "logger",
        "AGithubReleaseAssets.artefact_url",
        ("AGithubReleaseAssets.release",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.release")
    artefact = MagicMock()
    url = MagicMock()

    def get_response_key(k):
        if k == "error":
            return "ERROR" if errored else ""
        if k == "state":
            return "uploaded" if uploaded else ""

    with patched as (m_dict, m_log, m_url, m_release):
        m_response = MagicMock()
        m_release.return_value.repo.post = AsyncMock(return_value=m_response)
        if dry_run:
            response = m_dict.return_value
        else:
            response = m_release.return_value.repo.post.return_value
        response.get.side_effect = get_response_key
        assert (
            await assets.upload(artefact, url, dry_run=dry_run)
            == m_dict.return_value)

    succeeded = uploaded and not errored
    assert (
        response.get.call_args_list[0]
        == [("error", ), {}])
    if errored:
        assert len(response.get.call_args_list) == 1
    else:
        assert len(response.get.call_args_list) == 2
        assert (
            response.get.call_args_list[1]
            == [("state", ), {}])
    if dry_run:
        assert (
            m_dict.call_args_list[0]
            == [(),
                dict(state="uploaded",
                     url=(f"test://releases/{m_release.return_value.tag_name}"
                          f"/assets/{artefact.name}"))])
        assert not m_release.return_value.repo.post.called
        assert not artefact.read_bytes.called
        dict_key = 1
    else:
        assert (
            m_release.return_value.repo.post.call_args
            == [(url, ),
                dict(data=artefact.read_bytes.return_value,
                     content_type="application/octet-stream")])
        assert (
            artefact.read_bytes.call_args
            == [(), {}])
        dict_key = 0
    assert (
        m_dict.call_args_list[dict_key]
        == [(),
            dict(name=artefact.name,
                 url=(response.__getitem__.return_value
                      if succeeded
                      else url))])
    if succeeded:
        assert (
            response.__getitem__.call_args
            == [("url", ), {}])
        assert (
            m_log.debug.call_args
            == [(f"Upload {'(dry run) ' if dry_run else ''}release "
                 f"({m_release.return_value.tag_name}): {artefact.name}", ),
                {}])
    else:
        assert not response.__getitem__.called
        assert not m_log.debug.called
