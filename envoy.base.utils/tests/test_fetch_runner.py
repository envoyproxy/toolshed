
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio.run.runner import Runner

from envoy.base import utils


def test_fetchrunner_constructor(iters, patches):
    args = iters(tuple, count=3)
    kwargs = iters(dict, count=3)
    patched = patches(
        "runner.Runner.__init__",
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_super, ):
        m_super.return_value = None
        runner = utils.fetch_runner.FetchRunner(*args, **kwargs)

    assert isinstance(runner, Runner)
    assert (
        m_super.call_args
        == [args, kwargs])


def test_fetchrunner_downloads(patches):
    runner = utils.FetchRunner()
    patched = patches(
        "json",
        "pathlib",
        ("FetchRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_json, m_plib, m_args):
        assert (
            runner.downloads
            == m_json.load.return_value)

    assert (
        m_json.load.call_args
        == [(m_plib.Path.return_value.open.return_value, ), {}])
    assert (
        m_plib.Path.call_args
        == [(m_args.return_value.downloads, ), {}])
    assert (
        m_plib.Path.return_value.open.call_args
        == [(), {}])
    assert "downloads" in runner.__dict__


def test_fetchrunner_downloads_path(patches):
    runner = utils.FetchRunner()
    patched = patches(
        "pathlib",
        ("FetchRunner.tempdir",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_plib, m_temp):
        assert (
            runner.downloads_path
            == m_plib.Path.return_value.joinpath.return_value)

    assert (
        m_plib.Path.call_args
        == [(m_temp.return_value.name, ), {}])
    assert (
        m_plib.Path.return_value.joinpath.call_args
        == [("downloads", ), {}])

    assert "downloads_path" in runner.__dict__


@pytest.mark.parametrize("excludes", ["", "EXCLUDE_PATH"])
def test_fetchrunner_excludes(patches, excludes):
    runner = utils.FetchRunner()
    patched = patches(
        "pathlib",
        ("FetchRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_plib, m_args):
        m_args.return_value.excludes = excludes
        assert (
            runner.excludes
            == ((m_plib.Path.return_value
                       .read_text.return_value
                       .splitlines.return_value)
                if excludes
                else []))

    if not excludes:
        assert not m_plib.Path.called
        return

    assert (
        m_plib.Path.call_args
        == [("EXCLUDE_PATH", ), {}])
    assert (
        m_plib.Path.return_value.read_text.call_args
        == [(), {}])
    assert (
        m_plib.Path.return_value.read_text.return_value.splitlines.call_args
        == [(), {}])
    assert "excludes" in runner.__dict__


@pytest.mark.parametrize("token", ["", "TOKEN"])
def test_fetchrunner_headers(patches, token):
    runner = utils.FetchRunner()
    patched = patches(
        "dict",
        ("FetchRunner.token",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_dict, m_token):
        m_token.return_value = token
        assert (
            runner.headers
            == (m_dict.return_value
                if token
                else {}))

    if not token:
        assert not m_dict.called
        return

    assert (
        m_dict.call_args
        == [(),
            dict(Authorization="token TOKEN",
                 Accept="application/octet-stream")])
    assert "headers" not in runner.__dict__


def test_fetchrunner_time_elapsed(patches):
    runner = utils.FetchRunner()
    patched = patches(
        "round",
        "time",
        ("FetchRunner.time_start",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_round, m_time, m_start):
        assert (
            runner.time_elapsed
            == m_round.return_value)

    assert (
        m_round.call_args
        == [(m_time.time.return_value.__sub__.return_value, 3), {}])
    assert (
        m_time.time.call_args
        == [(), {}])
    assert (
        m_time.time.return_value.__sub__.call_args
        == [(m_start.return_value, ), {}])

    assert "time_elapsed" not in runner.__dict__


def test_fetchrunner_time_start(patches):
    runner = utils.FetchRunner()
    patched = patches(
        "time",
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_time, ):
        assert (
            runner.time_start
            == m_time.time.return_value)

    assert (
        m_time.time.call_args
        == [(), {}])

    assert "time_start" in runner.__dict__


@pytest.mark.parametrize("token", ["", "TOKEN"])
@pytest.mark.parametrize("token_path", ["", "TOKEN_PATH"])
def test_fetchrunner_token(patches, token, token_path):
    runner = utils.FetchRunner()
    patched = patches(
        "os",
        "pathlib",
        ("FetchRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_os, m_plib, m_args):
        m_args.return_value.token = token
        m_args.return_value.token_path = token_path
        assert (
            runner.token
            == ((m_plib.Path.return_value
                       .read_text.return_value
                       .strip.return_value)
                if token_path
                else (m_os.getenv.return_value
                      if token
                      else None)))

    if token_path:
        assert (
            m_plib.Path.call_args
            == [(token_path, ), {}])
        assert (
            m_plib.Path.return_value.read_text.call_args
            == [(), {}])
        assert (
            m_plib.Path.return_value.read_text.return_value.strip.call_args
            == [(), {}])
        assert not m_os.getenv.called
    elif token:
        assert not m_plib.Path.called
        assert (
            m_os.getenv.call_args
            == [(token, ), {}])
    else:
        assert not m_plib.Path.called
        assert not m_os.getenv.called
    assert "token" not in runner.__dict__


def test_fetchrunner_session(patches):
    runner = utils.FetchRunner()
    patched = patches(
        "aiohttp",
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_aiohttp, ):
        assert (
            runner.session
            == m_aiohttp.ClientSession.return_value)

    assert (
        m_aiohttp.ClientSession.call_args
        == [(), {}])
    assert "session" in runner.__dict__


def test_fetchrunner_add_arguments(patches):
    runner = utils.FetchRunner()
    parser = MagicMock()
    patched = patches(
        "runner.Runner.add_arguments",
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_super, ):
        runner.add_arguments(parser)

    assert (
        m_super.call_args
        == [(parser, ), {}])

    assert (
        parser.add_argument.call_args_list
        == [[("downloads",),
             {"help": "JSON k/v of downloads/info"}],
            [("--chunk-size",),
             {"default": utils.fetch_runner.DEFAULT_CHUNK_SIZE,
              "help": "Download chunk size",
              "type": int}],
            [("--concurrency",),
             {"default": utils.fetch_runner.DEFAULT_MAX_CONCURRENCY,
              "help": "Maximum concurrent downloads",
              "type": int}],
            [("--excludes",),
             {"help": (
                 "Path to file containing newline separated "
                 "paths to exclude")}],
            [("--extract-downloads",),
             {"action": "store_true",
              "default": False,
              "help": "Extract downloaded files"}],
            [("--output",),
             {"help": "Output format"}],
            [("--output-path",),
             {"help": "Output path"}],
            [("--token",),
             {"help": "Env name for auth token"}],
            [("--token-path",),
             {"help": "Path to auth token"}]])


@pytest.mark.parametrize("path", [True, False])
def test_fetchrunner_download_path(patches, path):
    runner = utils.FetchRunner()
    url = MagicMock()
    patched = patches(
        ("FetchRunner.downloads",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.downloads_path",
         dict(new_callable=PropertyMock)),
        "FetchRunner.filename",
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_downloads, m_path, m_filename):
        (m_downloads.return_value.__getitem__.return_value
                                 .__contains__.return_value) = path
        assert (
            runner.download_path(url)
            == (None
                if not path
                else m_path.return_value.joinpath.return_value))

    if not path:
        assert not m_path.called
        assert not m_filename.called
        assert not (
            m_downloads.return_value.__getitem__.return_value
                                    .__getitem__.called)
        return

    assert (
        m_path.return_value.joinpath.call_args
        == [(m_downloads.return_value.__getitem__.return_value
                                     .__getitem__.return_value,
             m_filename.return_value), {}])
    assert (
        m_filename.call_args
        == [(url, ), {}])
    assert (
        m_downloads.return_value.__getitem__.call_args
        == [(url, ), {}])
    assert (
        m_downloads.return_value.__getitem__.return_value.__getitem__.call_args
        == [("path", ), {}])


@pytest.mark.parametrize("path", [True, False])
@pytest.mark.parametrize("contains", [True, False])
def test_fetchrunner_excluded(patches, path, contains):
    runner = utils.FetchRunner()
    url = MagicMock()
    _path = (
        MagicMock()
        if path
        else None)
    patched = patches(
        "bool",
        ("FetchRunner.downloads",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.excludes",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_bool, m_downloads, m_excludes):
        (m_downloads.return_value.__getitem__.return_value
                                 .get.return_value) = _path
        m_excludes.return_value.__contains__.return_value = contains
        assert (
            runner.excluded(url)
            == m_bool.return_value)

    assert (
        m_downloads.return_value.__getitem__.call_args
        == [(url, ), {}])
    assert (
        m_downloads.return_value.__getitem__.return_value.get.call_args
        == [("path", ), {}])
    assert (
        m_bool.call_args
        == [((None if not path else contains), ), {}])
    if path:
        assert (
            m_excludes.return_value.__contains__.call_args
            == [(_path, ), {}])
    else:
        assert not m_excludes.called


@pytest.mark.parametrize("path", [True, False])
async def test_fetchrunner_fetch(patches, path):
    runner = utils.FetchRunner()
    url = MagicMock()
    _path = (
        MagicMock()
        if path
        else None)
    patched = patches(
        "FetchRunner.download_path",
        "FetchRunner.fetch_bytes",
        ("FetchRunner.log",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.time_elapsed",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_path, m_fetch, m_log, m_elapsed):
        m_path.return_value = _path
        assert (
            await runner.fetch(url)
            == m_fetch.return_value)

    assert (
        m_log.return_value.debug.call_args
        == [((f"{m_elapsed.return_value} Fetching:\n"
              f" {url}\n"), ), {}])
    assert (
        m_path.call_args
        == [(url, ), {}])
    if path:
        assert (
            _path.parent.mkdir.call_args
            == [(), dict(parents=True, exist_ok=True)])
    assert (
        m_fetch.call_args
        == [(url, ), dict(path=_path)])


@pytest.mark.parametrize("path", [True, False])
@pytest.mark.parametrize("checksum", [True, False])
@pytest.mark.parametrize("extract", [True, False])
async def test_fetchrunner_fetch_bytes(patches, path, checksum, extract):
    runner = utils.FetchRunner()
    url = MagicMock()
    _path = (
        MagicMock()
        if path
        else None)
    patched = patches(
        "asyncio",
        "utils",
        "FetchRunner.download_path",
        "FetchRunner.validate_checksum",
        ("FetchRunner.args",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.downloads",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.log",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.headers",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.session",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.time_elapsed",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    with patched as patchy:
        (m_asyncio, m_utils, m_download_path, m_validate,
         m_args, m_downloads, m_log, m_headers,
         m_session, m_elapsed) = patchy

        async def _chunked(size):
            assert size == m_args.return_value.chunk_size
            for x in range(0, 3):
                yield f"CHUNK{x}"

        _to_thread = AsyncMock()
        m_asyncio.to_thread = _to_thread
        _get = AsyncMock()
        m_session.return_value.get.return_value = _get
        response = _get.__aenter__.return_value
        response.content.iter_chunked = _chunked
        response.raise_for_status = MagicMock()
        (m_downloads.return_value.__getitem__.return_value
                                 .__contains__.return_value) = checksum
        m_args.return_value.extract_downloads = extract
        assert (
            await runner.fetch_bytes(url, _path)
            == (url,
                (response.read.return_value
                 if not path
                 else None)))

    assert (
        m_session.return_value.get.call_args
        == [(url, ), dict(headers=m_headers.return_value)])
    assert (
        response.raise_for_status.call_args
        == [(), {}])
    if not path:
        assert (
            response.read.call_args
            == [(), {}])
        assert not m_log.return_value.debug.called
        assert not response.content.iter_chunk.called
        assert not m_downloads.return_value.__getitem__.called
        assert not m_asyncio.to_thread.called
        assert not m_validate.called
        return

    assert not response.read.called
    assert (
        m_log.return_value.debug.call_args
        == [((f"{m_elapsed.return_value} "
              f"Writing chunks({m_args.return_value.chunk_size}):\n"
              f" {url}\n"
              f" -> {_path}"), ), {}])
    assert (
        _path.open.call_args
        == [("wb", ), {}])
    assert (
        _path.open.return_value.__enter__.return_value.write.call_args_list
        == [[(f"CHUNK{x}", ), {}]
            for x in range(0, 3)])
    assert (
        m_downloads.return_value.__getitem__.call_args
        == [(url, ), {}])
    if checksum:
        assert (
            m_validate.call_args
            == [(url, ), {}])
    else:
        assert not m_validate.called
    if not extract:
        assert not m_asyncio.to_thread.called
        assert not _path.unlink.called
        return
    assert (
        m_asyncio.to_thread.call_args
        == [(m_utils.extract, _path.parent, _path), {}])
    assert (
        _path.unlink.call_args
        == [(), {}])


def test_fetchrunner_filename(patches):
    runner = utils.FetchRunner()
    url = MagicMock()
    patched = patches(
        "urlsplit",
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_url, ):
        assert (
            runner.filename(url)
            == (m_url.return_value.path.split.return_value
                                  .__getitem__.return_value))

    assert (
        m_url.call_args
        == [(url, ), {}])
    assert (
        m_url.return_value.path.split.call_args
        == [("/", ), {}])
    assert (
        m_url.return_value.path.split.return_value.__getitem__.call_args
        == [(-1, ), {}])


def test_fetchrunner_hashed(patches):
    runner = utils.FetchRunner()
    content = MagicMock()
    patched = patches(
        "hashlib",
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_hash, ):
        assert (
            runner.hashed(content)
            == m_hash.sha256.return_value.hexdigest.return_value)

    assert (
        m_hash.sha256.call_args
        == [(), {}])
    assert (
        m_hash.sha256.return_value.update.call_args
        == [(content, ), {}])
    assert (
        m_hash.sha256.return_value.hexdigest.call_args
        == [(), {}])


@pytest.mark.parametrize("output", ["json", "NOTJSON"])
@pytest.mark.parametrize("path", ["", "PATH"])
async def test_fetchrunner_run(patches, iters, output, path):
    runner = utils.FetchRunner()
    patched = patches(
        "asyncio",
        "concurrent",
        "json",
        "print",
        "utils",
        "FetchRunner.excluded",
        "FetchRunner.fetch",
        ("FetchRunner.args",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.downloads",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.downloads_path",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.log",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.time_elapsed",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")
    items = {}

    async def _concurrent():
        for item in iters(cb=lambda x: f"X{x}"):
            items[item] = MagicMock()
            yield item, items[item]

    with patched as patchy:
        (m_asyncio, m_concurrent, m_json, m_print,
         m_utils, m_excluded, m_fetch, m_args,
         m_downloads, m_path, m_log, m_elapsed) = patchy
        m_args.return_value.output = output
        m_args.return_value.output_path = path
        _to_thread = AsyncMock()
        m_asyncio.to_thread = _to_thread
        m_concurrent.return_value = _concurrent()
        m_excluded.side_effect = lambda x: x == "I3"
        m_downloads.return_value = iters()
        result = await runner.run()
        assert not result
        download_iter = m_concurrent.call_args[0][0]
        downloads = list(download_iter)

    assert isinstance(download_iter, types.GeneratorType)
    assert (
        m_concurrent.call_args
        == [(download_iter, ),
            dict(limit=m_args.return_value.concurrency)])
    for download in downloads:
        assert await download == m_fetch.return_value
    assert (
        m_fetch.call_args_list
        == [[(x, ), {}]
            for x in m_downloads.return_value
            if x != "I3"])
    assert (
        m_log.return_value.debug.call_args_list[:5]
        == [[(f"{m_elapsed.return_value} Received:\n {x}\n", ), {}]
            for x in items])

    if output == "json":
        assert result == 0
        assert (
            m_print.call_args
            == [(m_json.dumps.return_value, ), {}])
        assert len(m_log.return_value.debug.call_args_list) == 5
        assert (
            m_json.dumps.call_args
            == [({k: v.decode() for k, v in items.items()},), {}])
        assert not m_asyncio.to_thread.called
        return
    if not path:
        assert result == 0
        assert len(m_log.return_value.debug.call_args_list) == 5
        assert not m_asyncio.to_thread.called
        return
    assert (
        m_log.return_value.debug.call_args_list[5]
        == [(f"{m_elapsed.return_value} "
             f"Packing:\n"
             f" {m_path.return_value}\n"
             f" {m_args.return_value.output_path}\n", ), {}])
    assert not m_print.called
    assert not m_json.dumps.called
    assert (
        m_asyncio.to_thread.call_args
        == [(m_utils.pack,
             m_path.return_value,
             m_args.return_value.output_path), {}])


@pytest.mark.parametrize("path", [True, False])
@pytest.mark.parametrize("matches", [True, False])
async def test_fetchrunner_validate_checksum(patches, path, matches):
    runner = utils.FetchRunner()
    url = MagicMock()
    _path = (
        MagicMock()
        if path
        else None)
    patched = patches(
        "asyncio",
        "FetchRunner.download_path",
        ("FetchRunner.downloads",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.log",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.time_elapsed",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_asyncio, m_path, m_downloads, m_log, m_elapsed):
        m_path.return_value = _path
        _to_thread = AsyncMock()
        m_asyncio.to_thread = _to_thread
        _to_thread.return_value.__ne__.return_value = not matches
        if path and not matches:
            with pytest.raises(utils.exceptions.ChecksumError) as e:
                await runner.validate_checksum(url)
        else:
            assert not await runner.validate_checksum(url)

    assert (
        m_path.call_args
        == [(url, ), {}])
    if not path:
        assert not _to_thread.called
        assert not m_log.return_value.debug.called
        assert not m_downloads.called
        return
    assert (
        _to_thread.call_args
        == [(runner.hashed, _path.read_bytes.return_value), {}])
    assert (
        _path.read_bytes.call_args
        == [(), {}])
    configured_checksum = (
        m_downloads.return_value.__getitem__.return_value
                                .__getitem__.return_value)
    assert (
        m_log.return_value.debug.call_args
        == [((f"{m_elapsed.return_value} "
              f"Validating:\n"
              f" {url}\n"
              f" {configured_checksum}\n"), ), {}])
    assert (
        _to_thread.return_value.__ne__.call_args
        == [(m_downloads.return_value.__getitem__.return_value
                                     .__getitem__.return_value, ), {}])
    assert (
        m_downloads.return_value.__getitem__.call_args
        == [(url,), {}])
    assert (
        m_downloads.return_value.__getitem__.return_value.__getitem__.call_args
        == [("checksum",), {}])
    if not matches:
        assert (
            e.value.args[0]
            == (f"Checksums do not match({url}):\n"
                f" expected: {configured_checksum}\n"
                f" received: {_to_thread.return_value}"))
