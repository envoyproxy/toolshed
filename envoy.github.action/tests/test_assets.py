
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from envoy.github.abstract import GithubActionError
from envoy.github.action import (
    GithubActionAssetsFetcher, GithubActionAssetsPusher)


def test_fetcher_constructor(patches):
    patched = patches(
        "AGithubActionAssetsFetcher.__init__",
        ("AGithubActionAssetsFetcher.concurrency",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.assets")

    with patched as (m_super, m_concurrency):
        m_super.return_value = None
        fetcher = GithubActionAssetsFetcher(
            "RELEASE", "PATH", "ASSET_TYPES")
        concurrency = fetcher.concurrency

    assert (
        m_super.call_args
        == [("RELEASE", "PATH", "ASSET_TYPES"), {}])

    assert concurrency == m_concurrency.return_value
    assert "concurrency" not in fetcher.__dict__


def test_fetcher_dunder_exit(patches):
    fetcher = GithubActionAssetsFetcher(
        "RELEASE", "PATH", "ASSET_TYPES")
    patched = patches(
        "tarfile",
        "AGithubActionAssetsFetcher.__exit__",
        ("AGithubActionAssetsFetcher.path",
         dict(new_callable=PropertyMock)),
        ("GithubActionAssetsFetcher.write_mode",
         dict(new_callable=PropertyMock)),
        ("GithubActionAssetsFetcher.path",
         dict(new_callable=PropertyMock)),
        ("GithubActionAssetsFetcher.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.assets")
    args = [f"ARG{i}" for i in range(0, 3)]

    with patched as (m_tar, m_super, m_superpath, m_mode, m_path, m_version):
        assert not fetcher.__exit__(*args)

    assert (
        m_tar.open.call_args
        == [(m_superpath.return_value,
             m_mode.return_value), {}])
    assert (
        m_tar.open.return_value.__enter__.return_value.add.call_args
        == [(m_path.return_value, ),
            dict(arcname=m_version.return_value)])
    assert (
        m_super.call_args
        == [tuple(args), {}])


def test_fetcher_is_tarlike(patches):
    fetcher = GithubActionAssetsFetcher(
        "RELEASE", "PATH", "ASSET_TYPES")
    patched = patches(
        "utils",
        ("AGithubActionAssetsFetcher.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.assets")

    with patched as (m_utils, m_path):
        assert fetcher.is_tarlike == m_utils.is_tarlike.return_value

    assert (
        m_utils.is_tarlike.call_args
        == [(m_path.return_value, ), {}])
    assert "is_tarlike" in fetcher.__dict__


@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("append", [True, False])
def test_fetcher_out_exists(patches, exists, append):
    fetcher = GithubActionAssetsFetcher(
        "RELEASE", "PATH", "ASSET_TYPES")
    patched = patches(
        ("GithubActionAssetsFetcher.append",
         dict(new_callable=PropertyMock)),
        ("AGithubActionAssetsFetcher.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.assets")
    with patched as (m_append, m_path):
        m_append.return_value = append
        m_path.return_value.exists.return_value = exists
        assert fetcher.out_exists == (exists and not append)

    assert "out_exists" not in fetcher.__dict__


@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("is_tarlike", [True, False])
def test_fetcher_path(patches, exists, is_tarlike):
    fetcher = GithubActionAssetsFetcher(
        "RELEASE", "PATH", "ASSET_TYPES")
    patched = patches(
        "pathlib",
        "GithubActionAssetsFetcher.fail",
        ("AGithubActionAssetsFetcher.path",
         dict(new_callable=PropertyMock)),
        ("GithubActionAssetsFetcher.out_exists",
         dict(new_callable=PropertyMock)),
        ("GithubActionAssetsFetcher.is_tarlike",
         dict(new_callable=PropertyMock)),
        ("GithubActionAssetsFetcher.tempdir",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.assets")
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
            m_fail.call_args
            == [(msg,), {}])
    else:
        assert not m_fail.called
    if not is_tarlike:
        path_calls += 1
        assert not m_plib.called
        assert not m_temp.called
    else:
        assert (
            m_plib.Path.call_args
            == [(m_temp.return_value.name,), {}])
    assert (
        m_path.call_args_list
        == [[(), {}]] * path_calls)


async def test_fetcher_download(patches):
    fetcher = GithubActionAssetsFetcher(
        "RELEASE", "PATH", "ASSET_TYPES")
    patched = patches(
        ("GithubActionAssetsFetcher.save",
         dict(new_callable=AsyncMock)),
        ("GithubActionAssetsFetcher.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.assets")
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
        m_save.call_args
        == [("ASSET TYPE",
             "ASSET NAME",
             m_session.return_value.get.return_value), {}])
    assert (
        m_session.return_value.get.call_args
        == [('ASSET DOWNLOAD URL',), {}])


@pytest.mark.parametrize("status", [None, 200, 201])
async def test_fetcher_save(patches, status):
    fetcher = GithubActionAssetsFetcher(
        "RELEASE", "PATH", "ASSET_TYPES")
    patched = patches(
        "stream",
        "GithubActionAssetsFetcher.fail",
        ("GithubActionAssetsFetcher.path", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.assets")
    download = MagicMock()
    download.status = status

    with patched as (m_stream, m_fail, m_path):
        m_stream.__aenter__ = AsyncMock()
        outfile = m_path.return_value.joinpath.return_value
        result = await fetcher.save("ASSET TYPE", "NAME", download)

    expected = dict(name="NAME", outfile=outfile)
    if status != 200:
        assert (
            m_fail.call_args
            == [(f"Failed downloading, got response:\n{download}", ), {}])
        expected["error"] = m_fail.return_value
    else:
        assert not m_fail.called

    assert result == expected
    assert (
        m_path.return_value.joinpath.call_args
        == [('ASSET TYPE', 'NAME'), {}])
    assert (
        outfile.parent.mkdir.call_args
        == [(), dict(exist_ok=True)])
    writer = m_stream.writer
    assert (
        writer.call_args
        == [(outfile, ), {}])
    stream_bytes = writer.return_value.__aenter__.return_value.stream_bytes
    assert (
        stream_bytes.call_args
        == [(download, ), {}])


def test_pusher_constructor(patches):
    patched = patches(
        "AGithubActionAssetsPusher.__init__",
        ("AGithubActionAssetsPusher.concurrency",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.assets")

    with patched as (m_super, m_concurrency):
        m_super.return_value = None
        pusher = GithubActionAssetsPusher("RELEASE", "PATH")
        concurrency = pusher.concurrency

    assert (
        m_super.call_args
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
    pusher = GithubActionAssetsPusher(
        "RELEASE", "PATH")
    patched = patches(
        ("GithubActionAssetsPusher.path",
         dict(new_callable=PropertyMock)),
        ("AGithubActionAssetsPusher.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.assets")
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
        pusher._artefacts_glob.format.call_args
        == [(), dict(version=m_version.return_value)])
    assert (
        m_path.return_value.glob.call_args
        == [(pusher._artefacts_glob.format.return_value, ), {}])


def test_pusher_is_dir(patches):
    pusher = GithubActionAssetsPusher(
        "RELEASE", "PATH")
    patched = patches(
        ("AGithubActionAssetsPusher.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.assets")
    with patched as (m_path, ):
        assert pusher.is_dir == m_path.return_value.is_dir.return_value

    assert (
        m_path.return_value.is_dir.call_args
        == [(), {}])
    assert "is_dir" in pusher.__dict__


def test_pusher_is_tarball(patches):
    pusher = GithubActionAssetsPusher(
        "RELEASE", "PATH")
    patched = patches(
        "tarfile",
        ("AGithubActionAssetsPusher.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.assets")
    with patched as (m_tar, m_path):
        assert pusher.is_tarball == m_tar.is_tarfile.return_value

    assert (
        m_tar.is_tarfile.call_args
        == [(m_path.return_value, ), {}])
    assert "is_tarball" in pusher.__dict__


@pytest.mark.parametrize("is_dir", [True, False])
@pytest.mark.parametrize("is_tarball", [True, False])
def test_pusher_path(patches, is_dir, is_tarball):
    pusher = GithubActionAssetsPusher(
        "RELEASE", "PATH")
    patched = patches(
        "utils",
        ("AGithubActionAssetsPusher.path",
         dict(new_callable=PropertyMock)),
        ("GithubActionAssetsPusher.is_tarball",
         dict(new_callable=PropertyMock)),
        ("GithubActionAssetsPusher.is_dir",
         dict(new_callable=PropertyMock)),
        ("GithubActionAssetsPusher.tempdir",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.assets")
    with patched as (m_utils, m_path, m_tar, m_isdir, m_temp):
        m_tar.return_value = is_tarball
        m_isdir.return_value = is_dir
        if not is_tarball and not is_dir:
            with pytest.raises(GithubActionError) as e:
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
            m_utils.extract.call_args
            == [(m_temp.return_value.name,
                 m_path.return_value), {}])
    else:
        assert not m_utils.extract.called


@pytest.mark.parametrize("name", [f"ARTEFACT{i}" for i in range(0, 5)])
@pytest.mark.parametrize(
    "asset_names",
    [[],
     [f"ARTEFACT{i}" for i in range(0, 5)],
     [f"ARTEFACT{i}" for i in range(3, 7)]])
@pytest.mark.parametrize("error", [True, False])
@pytest.mark.parametrize("state", ["uploaded", "NOTUPLOADED"])
async def test_pusher_upload(patches, name, asset_names, error, state):
    pusher = GithubActionAssetsPusher(
        "RELEASE", "PATH")
    patched = patches(
        "stream",
        "GithubActionAssetsPusher.fail",
        ("GithubActionAssetsPusher.asset_names",
         dict(new_callable=PropertyMock)),
        ("GithubActionAssetsPusher.github",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.assets")
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
            m_fail.call_args
            == [(f"Asset exists already {name}", ), {}])
        return

    assert (
        m_stream.reader.call_args
        == [(artefact, ), {}])
    assert (
        m_github.return_value.post.call_args
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
            m_fail.call_args
            == [(("Something went wrong uploading "
                  f"{name} -> URL, got:\n{response}"), ),
                {}])
        return
    assert (
        result
        == {'name': name,
            'url': response.__getitem__.return_value})
    assert (
        response.__getitem__.call_args
        == [("url", ), {}])
    assert not m_fail.called
