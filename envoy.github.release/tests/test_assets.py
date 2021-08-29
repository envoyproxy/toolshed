
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from envoy.github.abstract import GithubReleaseError
from envoy.github.release import (
    GithubReleaseAssetsFetcher, GithubReleaseAssetsPusher)


def test_fetcher_constructor(patches):
    patched = patches(
        "AGithubReleaseAssetsFetcher.__init__",
        ("AGithubReleaseAssetsFetcher.concurrency",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.assets")

    with patched as (m_super, m_concurrency):
        m_super.return_value = None
        fetcher = GithubReleaseAssetsFetcher(
            "RELEASE", "PATH", "ASSET_TYPES")
        concurrency = fetcher.concurrency

    assert (
        list(m_super.call_args)
        == [("RELEASE", "PATH", "ASSET_TYPES"), {}])

    assert concurrency == m_concurrency.return_value
    assert "concurrency" not in fetcher.__dict__


def test_fetcher_dunder_exit(patches):
    fetcher = GithubReleaseAssetsFetcher(
        "RELEASE", "PATH", "ASSET_TYPES")
    patched = patches(
        "tarfile",
        "AGithubReleaseAssetsFetcher.__exit__",
        ("AGithubReleaseAssetsFetcher.path",
         dict(new_callable=PropertyMock)),
        ("GithubReleaseAssetsFetcher.write_mode",
         dict(new_callable=PropertyMock)),
        ("GithubReleaseAssetsFetcher.path",
         dict(new_callable=PropertyMock)),
        ("GithubReleaseAssetsFetcher.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.assets")
    args = [f"ARG{i}" for i in range(0, 3)]

    with patched as (m_tar, m_super, m_superpath, m_mode, m_path, m_version):
        assert not fetcher.__exit__(*args)

    assert (
        list(m_tar.open.call_args)
        == [(m_superpath.return_value,
             m_mode.return_value), {}])
    assert (
        list(m_tar.open.return_value.__enter__.return_value.add.call_args)
        == [(m_path.return_value, ),
            dict(arcname=m_version.return_value)])
    assert (
        list(m_super.call_args)
        == [tuple(args), {}])


def test_fetcher_is_tarlike(patches):
    fetcher = GithubReleaseAssetsFetcher(
        "RELEASE", "PATH", "ASSET_TYPES")
    patched = patches(
        "utils",
        ("AGithubReleaseAssetsFetcher.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.assets")

    with patched as (m_utils, m_path):
        assert fetcher.is_tarlike == m_utils.is_tarlike.return_value

    assert (
        list(m_utils.is_tarlike.call_args)
        == [(m_path.return_value, ), {}])
    assert "is_tarlike" in fetcher.__dict__


@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("append", [True, False])
def test_fetcher_out_exists(patches, exists, append):
    fetcher = GithubReleaseAssetsFetcher(
        "RELEASE", "PATH", "ASSET_TYPES")
    patched = patches(
        ("GithubReleaseAssetsFetcher.append",
         dict(new_callable=PropertyMock)),
        ("AGithubReleaseAssetsFetcher.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.assets")
    with patched as (m_append, m_path):
        m_append.return_value = append
        m_path.return_value.exists.return_value = exists
        assert fetcher.out_exists == (exists and not append)

    assert "out_exists" not in fetcher.__dict__


@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("is_tarlike", [True, False])
def test_fetcher_path(patches, exists, is_tarlike):
    fetcher = GithubReleaseAssetsFetcher(
        "RELEASE", "PATH", "ASSET_TYPES")
    patched = patches(
        "pathlib",
        "GithubReleaseAssetsFetcher.fail",
        ("AGithubReleaseAssetsFetcher.path",
         dict(new_callable=PropertyMock)),
        ("GithubReleaseAssetsFetcher.out_exists",
         dict(new_callable=PropertyMock)),
        ("GithubReleaseAssetsFetcher.is_tarlike",
         dict(new_callable=PropertyMock)),
        ("GithubReleaseAssetsFetcher.tempdir",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.assets")
    with patched as (m_plib, m_fail, m_path, m_exists, m_tar, m_temp):
        m_tar.return_value = is_tarlike
        m_exists.return_value = exists
        assert (
            fetcher.path
            == (m_plib.Path.return_value
                if is_tarlike
                else m_path.return_value))

    assert "path" in fetcher.__dict__
    path_calls = 0
    if exists:
        path_calls += 1
        msg = (
            f"Output directory exists: {m_path.return_value}"
            if not is_tarlike
            else f"Output tarball exists: {m_path.return_value}")
        assert (
            list(m_fail.call_args)
            == [(msg,), {}])
    else:
        assert not m_fail.called
    if not is_tarlike:
        path_calls += 1
        assert not m_plib.called
        assert not m_temp.called
    else:
        assert (
            list(m_plib.Path.call_args)
            == [(m_temp.return_value.name,), {}])
    assert (
        list(list(c) for c in m_path.call_args_list)
        == [[(), {}]] * path_calls)


@pytest.mark.asyncio
async def test_fetcher_download(patches):
    fetcher = GithubReleaseAssetsFetcher(
        "RELEASE", "PATH", "ASSET_TYPES")
    patched = patches(
        ("GithubReleaseAssetsFetcher.save",
         dict(new_callable=AsyncMock)),
        ("GithubReleaseAssetsFetcher.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.assets")
    asset = dict(
        asset_type="ASSET TYPE",
        browser_download_url="ASSET DOWNLOAD URL",
        name="ASSET NAME")

    with patched as (m_save, m_session):
        m_session.return_value.get = AsyncMock()
        assert (
            await fetcher.download(asset)
            == m_save.return_value)

    assert (
        list(m_save.call_args)
        == [("ASSET TYPE",
             "ASSET NAME",
             m_session.return_value.get.return_value), {}])
    assert (
        list(m_session.return_value.get.call_args)
        == [('ASSET DOWNLOAD URL',), {}])


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [None, 200, 201])
async def test_fetcher_save(patches, status):
    fetcher = GithubReleaseAssetsFetcher(
        "RELEASE", "PATH", "ASSET_TYPES")
    patched = patches(
        "stream",
        "GithubReleaseAssetsFetcher.fail",
        ("GithubReleaseAssetsFetcher.path", dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.assets")
    download = MagicMock()
    download.status = status

    with patched as (m_stream, m_fail, m_path):
        m_stream.__aenter__ = AsyncMock()
        outfile = m_path.return_value.joinpath.return_value
        result = await fetcher.save("ASSET TYPE", "NAME", download)

    expected = dict(name="NAME", outfile=outfile)
    if status != 200:
        assert (
            list(m_fail.call_args)
            == [(f"Failed downloading, got response:\n{download}", ), {}])
        expected["error"] = m_fail.return_value
    else:
        assert not m_fail.called

    assert result == expected
    assert (
        list(m_path.return_value.joinpath.call_args)
        == [('ASSET TYPE', 'NAME'), {}])
    assert (
        list(outfile.parent.mkdir.call_args)
        == [(), dict(exist_ok=True)])
    writer = m_stream.writer
    assert (
        list(writer.call_args)
        == [(outfile, ), {}])
    stream_bytes = writer.return_value.__aenter__.return_value.stream_bytes
    assert (
        list(stream_bytes.call_args)
        == [(download, ), {}])


def test_pusher_constructor(patches):
    patched = patches(
        "AGithubReleaseAssetsPusher.__init__",
        ("AGithubReleaseAssetsPusher.concurrency",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.assets")

    with patched as (m_super, m_concurrency):
        m_super.return_value = None
        pusher = GithubReleaseAssetsPusher("RELEASE", "PATH")
        concurrency = pusher.concurrency

    assert (
        list(m_super.call_args)
        == [("RELEASE", "PATH"), {}])

    assert concurrency == m_concurrency.return_value
    assert "concurrency" not in pusher.__dict__


@pytest.mark.parametrize(
    "file_exts",
    [[],
     [f"EXT{i}" for i in range(0, 3)],
     [f"EXT{i}" for i in range(3, 7)]])
@pytest.mark.parametrize(
    "globs",
    [[],
     [f".EXT{i}" for i in range(0, 3)],
     [f".EXT{i}" for i in range(3, 7)],
     ([f".EXT{i}" for i in range(0, 3)]
      + [f".NOTEXT{i}" for i in range(0, 3)])])
def test_pusher_artefacts(patches, file_exts, globs):
    pusher = GithubReleaseAssetsPusher(
        "RELEASE", "PATH")
    patched = patches(
        ("GithubReleaseAssetsPusher.path",
         dict(new_callable=PropertyMock)),
        ("AGithubReleaseAssetsPusher.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.assets")
    pusher._artefacts_glob = MagicMock()
    pusher.file_exts = file_exts

    mock_globs = {}
    for glob in globs:
        mock_match = MagicMock()
        mock_match.suffix = glob
        mock_globs[glob] = mock_match

    with patched as (m_path, m_version):
        m_path.return_value.glob.return_value = mock_globs.values()
        artefacts = pusher.artefacts
        assert isinstance(artefacts, types.GeneratorType)
        artefacts = list(artefacts)

    assert (
        artefacts
        == [mock_globs[x] for x in globs if x[1:] in file_exts])
    assert (
        list(pusher._artefacts_glob.format.call_args)
        == [(), dict(version=m_version.return_value)])
    assert (
        list(m_path.return_value.glob.call_args)
        == [(pusher._artefacts_glob.format.return_value, ), {}])


def test_pusher_is_dir(patches):
    pusher = GithubReleaseAssetsPusher(
        "RELEASE", "PATH")
    patched = patches(
        ("AGithubReleaseAssetsPusher.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.assets")
    with patched as (m_path, ):
        assert pusher.is_dir == m_path.return_value.is_dir.return_value

    assert (
        list(m_path.return_value.is_dir.call_args)
        == [(), {}])
    assert "is_dir" in pusher.__dict__


def test_pusher_is_tarball(patches):
    pusher = GithubReleaseAssetsPusher(
        "RELEASE", "PATH")
    patched = patches(
        "tarfile",
        ("AGithubReleaseAssetsPusher.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.assets")
    with patched as (m_tar, m_path):
        assert pusher.is_tarball == m_tar.is_tarfile.return_value

    assert (
        list(m_tar.is_tarfile.call_args)
        == [(m_path.return_value, ), {}])
    assert "is_tarball" in pusher.__dict__


@pytest.mark.parametrize("is_dir", [True, False])
@pytest.mark.parametrize("is_tarball", [True, False])
def test_pusher_path(patches, is_dir, is_tarball):
    pusher = GithubReleaseAssetsPusher(
        "RELEASE", "PATH")
    patched = patches(
        "utils",
        ("AGithubReleaseAssetsPusher.path",
         dict(new_callable=PropertyMock)),
        ("GithubReleaseAssetsPusher.is_tarball",
         dict(new_callable=PropertyMock)),
        ("GithubReleaseAssetsPusher.is_dir",
         dict(new_callable=PropertyMock)),
        ("GithubReleaseAssetsPusher.tempdir",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.assets")
    with patched as (m_utils, m_path, m_tar, m_isdir, m_temp):
        m_tar.return_value = is_tarball
        m_isdir.return_value = is_dir
        if not is_tarball and not is_dir:
            with pytest.raises(GithubReleaseError) as e:
                pusher.path
            assert not m_utils.extract.called
            assert (
                e.value.args[0]
                == (f"Unrecognized target '{m_path.return_value}', "
                    "should either be a directory or a tarball "
                    "containing packages"))
            return
        assert (
            pusher.path
            == (m_utils.extract.return_value
                if is_tarball
                else m_path.return_value))

    assert "path" in pusher.__dict__
    if is_tarball:
        assert (
            list(m_utils.extract.call_args)
            == [(m_temp.return_value.name,
                 m_path.return_value), {}])
    else:
        assert not m_utils.extract.called


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [f"ARTEFACT{i}" for i in range(0, 5)])
@pytest.mark.parametrize(
    "asset_names",
    [[],
     [f"ARTEFACT{i}" for i in range(0, 5)],
     [f"ARTEFACT{i}" for i in range(3, 7)]])
@pytest.mark.parametrize("error", [True, False])
@pytest.mark.parametrize("state", ["uploaded", "NOTUPLOADED"])
async def test_pusher_upload(patches, name, asset_names, error, state):
    pusher = GithubReleaseAssetsPusher(
        "RELEASE", "PATH")
    patched = patches(
        "stream",
        "GithubReleaseAssetsPusher.fail",
        ("GithubReleaseAssetsPusher.asset_names",
         dict(new_callable=PropertyMock)),
        ("GithubReleaseAssetsPusher.github",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.release.assets")
    artefact = MagicMock()
    artefact.name = name
    response = MagicMock()
    response.get.side_effect = lambda k: dict(error=error, state=state)[k]

    with patched as (m_stream, m_fail, m_assets, m_github):
        m_stream.reader.__aenter__ = AsyncMock()
        m_assets.return_value = AsyncMock(return_value=asset_names)()
        m_github.return_value.post = AsyncMock(return_value=response)
        result = await pusher.upload(artefact, "URL")

    if name in asset_names:
        assert (
            result
            == {'name': name,
                'url': 'URL',
                'error': m_fail.return_value})
        assert not m_stream.reader.called
        assert not m_github.return_value.post.called
        assert (
            list(m_fail.call_args)
            == [(f"Asset exists already {name}", ), {}])
        return

    assert (
        list(m_stream.reader.call_args)
        == [(artefact, ), {}])
    assert (
        list(m_github.return_value.post.call_args)
        == [("URL", ),
            dict(data=m_stream.reader.return_value.__aenter__.return_value,
                 content_type="application/octet-stream")])
    if error or state != "uploaded":
        assert (
            result
            == {'name': name,
                'url': 'URL',
                'error': m_fail.return_value})
        assert (
            list(m_fail.call_args)
            == [(("Something went wrong uploading "
                  f"{name} -> URL, got:\n{response}"), ),
                {}])
        return
    assert (
        result
        == {'name': name,
            'url': response.__getitem__.return_value})
    assert (
        list(response.__getitem__.call_args)
        == [("url", ), {}])
    assert not m_fail.called
