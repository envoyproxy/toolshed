
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


def test_fetchrunner_gpg(patches):
    runner = utils.FetchRunner()
    patched = patches(
        "gnupg",
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_gpg, ):
        assert (
            runner.gpg
            == m_gpg.GPG.return_value)

    assert (
        m_gpg.GPG.call_args
        == [(), {}])
    assert "gpg" in runner.__dict__


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
@pytest.mark.parametrize("create", [True, False])
def test_fetchrunner_download_path(patches, path, create):
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
            runner.download_path(url, create=create)
            == (None
                if not path
                else m_path.return_value.joinpath.return_value))

    if not path:
        assert not m_path.called
        assert not m_filename.called
        assert not (
            m_downloads.return_value.__getitem__.return_value
                                    .__getitem__.called)
        assert (
            not m_path.return_value.joinpath.return_value.parent.mkdir.called)
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
    if create:
        assert (
            m_path.return_value.joinpath.return_value.parent.mkdir.call_args
            == [(), dict(parents=True, exist_ok=True)])
    else:
        assert not (
            m_path.return_value.joinpath.return_value.parent.mkdir.called)


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
@pytest.mark.parametrize("extract", [True, False])
async def test_fetchrunner_fetch(patches, path, extract):
    runner = utils.FetchRunner()
    url = MagicMock()
    patched = patches(
        "asyncio",
        "io",
        "utils",
        "FetchRunner.download_path",
        "FetchRunner.fetch_bytes",
        "FetchRunner.validate",
        ("FetchRunner.args",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.log",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.time_elapsed",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    with patched as patchy:
        (m_asyncio, m_io, m_utils, m_path, m_fetch,
         m_valid, m_args, m_log, m_elapsed) = patchy
        if not path:
            m_path.return_value = None
        m_args.return_value.extract_downloads = extract
        _to_thread = AsyncMock()
        m_asyncio.to_thread = _to_thread
        fd = (m_io.BytesIO.return_value.__enter__
                          .return_value)
        assert (
            await runner.fetch(url)
            == (url,
                (fd.read.return_value
                 if not path
                 else b"")))

    assert (
        m_log.return_value.debug.call_args
        == [((f"{m_elapsed.return_value} Fetching:\n"
              f" {url}\n"), ), {}])
    assert (
        m_path.call_args
        == [(url, ), {}])
    if path:
        assert (
            m_path.return_value.open.call_args
            == [("wb+", ), {}])
        assert not m_io.BytesIO.called
        fd = m_path.return_value.open.return_value
        assert not fd.__enter__.return_value.read.called
    else:
        assert (
            m_io.BytesIO.call_args
            == [(), {}])
        fd = m_io.BytesIO.return_value
        assert (
            fd.__enter__.return_value.read.call_args
            == [(), {}])

    assert (
        m_fetch.call_args
        == [(url, fd.__enter__.return_value), {}])
    assert (
        m_valid.call_args
        == [(url, fd.__enter__.return_value), {}])
    if path and extract:
        assert (
            m_asyncio.to_thread.call_args
            == [(m_utils.extract,
                 m_path.return_value.parent,
                 m_path.return_value), {}])
        assert (
            m_path.return_value.unlink.call_args
            == [(), {}])
    else:
        assert not m_asyncio.to_thread.called


@pytest.mark.parametrize("named", [True, False])
@pytest.mark.parametrize("checksum", [True, False])
@pytest.mark.parametrize("extract", [True, False])
async def test_fetchrunner_fetch_bytes(patches, named, checksum, extract):
    runner = utils.FetchRunner()
    url = MagicMock()
    fd = MagicMock()
    patched = patches(
        "hasattr",
        ("FetchRunner.args",
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
        (m_attr,
         m_args, m_log, m_headers,
         m_session, m_elapsed) = patchy

        async def _chunked(size):
            assert size == m_args.return_value.chunk_size
            for x in range(0, 3):
                yield f"CHUNK{x}"

        m_attr.return_value = named
        _get = AsyncMock()
        m_session.return_value.get.return_value = _get
        response = _get.__aenter__.return_value
        response.content.iter_chunked = _chunked
        response.raise_for_status = MagicMock()
        assert not await runner.fetch_bytes(url, fd)

    assert (
        m_session.return_value.get.call_args
        == [(url, ), dict(headers=m_headers.return_value)])
    assert (
        response.raise_for_status.call_args
        == [(), {}])
    dest = (
        f" -> {fd.name}"
        if named
        else "")
    assert (
        m_log.return_value.debug.call_args
        == [((f"{m_elapsed.return_value} "
              f"Writing chunks({m_args.return_value.chunk_size}):\n"
              f" {url}\n"
              f"{dest}"), ), {}])
    assert (
        fd.write.call_args_list
        == [[(f"CHUNK{x}", ), {}]
            for x in range(0, 3)])


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
    fd = MagicMock()
    patched = patches(
        "hashlib",
        prefix="envoy.base.utils.fetch_runner")
    with patched as (m_hash, ):
        assert (
            runner.hashed(fd)
            == m_hash.sha256.return_value.hexdigest.return_value)

    assert (
        m_hash.sha256.call_args
        == [(), {}])
    assert (
        m_hash.sha256.return_value.update.call_args
        == [(fd.read.return_value, ), {}])
    assert (
        fd.read.call_args
        == [(), {}])
    assert (
        m_hash.sha256.return_value.hexdigest.call_args
        == [(), {}])


@pytest.mark.parametrize("output", ["json", "NOTJSON"])
@pytest.mark.parametrize("path", ["", "PATH"])
@pytest.mark.parametrize("empty", [True, False])
async def test_fetchrunner_run(patches, iters, output, path, empty):
    runner = utils.FetchRunner()
    patched = patches(
        "any",
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
        (m_any, m_asyncio, m_concurrent, m_json, m_print,
         m_utils, m_excluded, m_fetch, m_args,
         m_downloads, m_path, m_log, m_elapsed) = patchy
        m_any.return_value = not empty
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
        assert not m_any.called
        return
    if empty:
        assert result == 0
        assert len(m_log.return_value.debug.call_args_list) == 5
        assert not m_asyncio.to_thread.called
        assert (
            m_any.call_args
            == [(m_path.return_value.iterdir.return_value, ), {}])
        assert (
            m_path.return_value.iterdir.call_args
            == [(), {}])
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


@pytest.mark.parametrize("signature", [True, False])
@pytest.mark.parametrize("checksum", [True, False])
async def test_fetchrunner_validate(patches, signature, checksum):
    runner = utils.FetchRunner()
    url = MagicMock()
    fd = MagicMock()
    patched = patches(
        "FetchRunner.validate_checksum",
        "FetchRunner.validate_signature",
        ("FetchRunner.downloads",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    def _contains(x):
        if x == "checksum":
            return checksum
        if x == "signature":
            return signature

    with patched as (m_checksum, m_signature, m_downloads):
        (m_downloads.return_value.__getitem__
                    .return_value.__contains__.side_effect) = _contains
        assert not await runner.validate(url, fd)

    assert (
        (m_downloads.return_value.__getitem__
                    .return_value.__contains__.call_args_list)
        == [[("signature", ), {}],
            [("checksum", ), {}]])
    seeks = [[(0, ), {}]]
    if checksum:
        seeks.append([(0, ), {}])
        assert (
            m_checksum.call_args
            == [(url, fd), {}])
    else:
        assert not m_checksum.called
    if signature:
        seeks.append([(0, ), {}])
        assert (
            m_signature.call_args
            == [(url, fd), {}])
    else:
        assert not m_signature.called
    assert (
        fd.seek.call_args_list
        == seeks)


@pytest.mark.parametrize("matches", [True, False])
async def test_fetchrunner_validate_checksum(patches, matches):
    runner = utils.FetchRunner()
    url = MagicMock()
    fd = MagicMock()
    patched = patches(
        "asyncio",
        ("FetchRunner.downloads",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.log",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.time_elapsed",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_asyncio, m_downloads, m_log, m_elapsed):
        _to_thread = AsyncMock()
        m_asyncio.to_thread = _to_thread
        _to_thread.return_value.__ne__.return_value = not matches
        if not matches:
            with pytest.raises(utils.exceptions.ChecksumError) as e:
                await runner.validate_checksum(url, fd)
        else:
            assert not await runner.validate_checksum(url, fd)

    assert (
        _to_thread.call_args
        == [(runner.hashed, fd), {}])
    configured_checksum = (
        m_downloads.return_value.__getitem__.return_value
                                .__getitem__.return_value)
    assert (
        m_log.return_value.debug.call_args
        == [((f"{m_elapsed.return_value} "
              f"Validating checksum:\n"
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


@pytest.mark.parametrize("valid", [True, False])
@pytest.mark.parametrize("matches", [True, False])
async def test_fetchrunner_validate_signature(patches, iters, valid, matches):
    runner = utils.FetchRunner()
    url = MagicMock()
    fd = MagicMock()
    patched = patches(
        "str",
        ("FetchRunner.downloads",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.gpg",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.log",
         dict(new_callable=PropertyMock)),
        ("FetchRunner.time_elapsed",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.fetch_runner")

    with patched as (m_str, m_downloads, m_gpg, m_log, m_elapsed):
        m_gpg.return_value.verify_file.return_value.valid = valid
        (m_gpg.return_value.verify_file
              .return_value.username.__eq__.return_value) = matches
        m_gpg.return_value.verify_file.return_value.problems = iters()
        m_str.side_effect = lambda x: f"X{x}"
        if not valid or not matches:
            with pytest.raises(utils.exceptions.SignatureError) as e:
                await runner.validate_signature(url, fd)
        else:
            assert not await runner.validate_signature(url, fd)

    signature = (
        m_downloads.return_value.__getitem__
                   .return_value.__getitem__.return_value)
    assert (
        m_log.return_value.debug.call_args
        == [((f"{m_elapsed.return_value} "
              f"Validating signature:\n"
              f" {url}\n"
              f" {signature}\n"), ), {}])
    assert (
        m_gpg.return_value.verify_file.call_args
        == [(fd, ), {}])
    assert (
        m_downloads.return_value.__getitem__.call_args
        == [(url, ), {}])
    assert (
        m_downloads.return_value.__getitem__.return_value.__getitem__.call_args
        == [("signature", ), {}])
    if not valid:
        assert (
            e.value.args[0]
            == f"Signature not valid:\n {url}\n XI0\n XI1\n XI2\n XI3\n XI4")
        assert not (
            m_gpg.return_value.verify_file
                 .return_value.username.__eq__.called)
        return
    assert (
        m_gpg.return_value.verify_file.return_value.username.__eq__.call_args
        == [((m_downloads.return_value.__getitem__
                         .return_value.__getitem__.return_value), ),
            {}])
    if not matches:
        signature = (
            m_downloads.return_value.__getitem__
                       .return_value.__getitem__.return_value)
        received = (
            m_gpg.return_value.verify_file.return_value.username)
        assert (
            e.value.args[0]
            == ("Signature not correct:\n"
                f" expected: {signature}\n"
                f" received: {received}"))
