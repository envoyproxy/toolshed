
import types
from functools import partial
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import yapf

from aio.core import directory

from envoy.code import check


@pytest.mark.parametrize("args", [[], [f"ARG{i}" for i in range(0, 5)]])
def test_yapf_yapfformatcheck_constructor(args):
    yapf_check = check.abstract.yapf.YapfFormatCheck(
        "PATH", "CONFIG_PATH", "FIX", *args)
    assert isinstance(yapf_check, directory.IDirectoryContext)
    assert isinstance(yapf_check, directory.ADirectoryContext)
    assert yapf_check.config_path == "CONFIG_PATH"
    assert yapf_check.fix == "FIX"
    assert yapf_check.args == tuple(args)


@pytest.mark.parametrize("n", range(1, 5))
@pytest.mark.parametrize("e", [[1, 3], [2, 4], [3, 7]])
@pytest.mark.parametrize("raises", [None, Exception, yapf.errors.YapfError])
@pytest.mark.parametrize("fix", [True, False])
def test_yapf_yapfformatcheck_check_results(iters, patches, n, e, raises, fix):
    args = iters(count=7)
    yapf_check = check.abstract.yapf.YapfFormatCheck(
        "PATH", "CONFIG_PATH", fix, *args)
    patched = patches(
        "os",
        "yapf.yapf_api",
        ("YapfFormatCheck.path",
         dict(new_callable=PropertyMock)),
        "YapfFormatCheck.handle_result",
        prefix="envoy.code.check.abstract.yapf")
    _expected = []

    def handle(path, *args):
        i = int(path[-1])
        if i in e and raises:
            if raises == yapf.errors.YapfError:
                _expected.append(
                    (path,
                     [f"Yaml check failed: {path}\nAN ERROR OCCURRED"]))
            raise raises("AN ERROR OCCURRED")
        if i % n:
            _expected.append(path)
            return path

    with patched as (m_os, m_yapf, m_path, m_handle):
        m_handle.side_effect = handle
        resultgen = yapf_check.check_results
        if raises == Exception:
            with pytest.raises(Exception):
                resultlist = list(resultgen)
        else:
            resultlist = list(resultgen)

    assert isinstance(resultgen, types.GeneratorType)
    if raises == Exception:
        return
    assert (
        resultlist
        == _expected)
    assert (
        m_handle.call_args_list
        == [[(p, m_yapf.FormatFile.return_value), {}]
            for p in args])
    assert (
        m_yapf.FormatFile.call_args_list
        == [[(m_os.path.join.return_value, ),
             dict(style_config="CONFIG_PATH",
                  in_place=fix,
                  print_diff=not fix)]
            for p in args])
    assert (
        m_os.path.join.call_args_list
        == [[(m_path.return_value, p), {}]
            for p in args])


@pytest.mark.parametrize(
    "changed",
    [None, True, False, "", [], "CHANGED"])
@pytest.mark.parametrize(
    "reformatted",
    [None, True, False, "", [], "REFORMATTED"])
def test_yapf_yapfformatcheck_handle_result(changed, reformatted):
    yapf_check = check.abstract.yapf.YapfFormatCheck(
        "PATH", "CONFIG_PATH", "FIX")
    path = MagicMock()
    encoding = MagicMock()
    assert (
        yapf_check.handle_result(path, (reformatted, encoding, changed))
        == (None
            if not (changed or reformatted)
            else ((path, [f"Issues found: {path}\n{reformatted}"])
                  if reformatted
                  else (path, [f"Issues found (fixed): {path}"]))))


def test_yapf_yapfformatcheck_run_checks(patches):
    yapf_check = check.abstract.yapf.YapfFormatCheck(
        "PATH", "CONFIG_PATH", "FIX")
    patched = patches(
        "tuple",
        ("YapfFormatCheck.check_results",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.yapf")

    with patched as (m_tuple, m_results):
        assert (
            yapf_check.run_checks()
            == m_tuple.return_value)

    assert (
        m_tuple.call_args
        == [(m_results.return_value, ), {}])


def test_yapf_yapffiles_constructor():
    yapf_files = check.abstract.yapf.YapfFiles("PATH")
    assert isinstance(yapf_files, directory.IDirectoryContext)
    assert isinstance(yapf_files, directory.ADirectoryContext)


def test_yapf_yapffiles_filter_files(patches):
    yapf_files = check.abstract.yapf.YapfFiles("PATH")
    patched = patches(
        "yapf",
        "set",
        ("YapfFiles.in_directory",
         dict(new_callable=PropertyMock)),
        ("YapfFiles.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.yapf")
    py_files = MagicMock()

    with patched as (m_yapf, m_set, m_dir_ctx, m_path):
        assert (
            yapf_files.filter_files(py_files)
            == m_set.return_value)

    assert m_dir_ctx.return_value.__enter__.called
    assert (
        m_set.call_args
        == [(m_yapf.file_resources.GetCommandLineFiles.return_value, ),
            {}])
    assert (
        m_yapf.file_resources.GetCommandLineFiles.call_args
        == [(py_files, ),
            dict(recursive=False,
                 exclude=(m_yapf.file_resources.GetExcludePatternsForDir
                                               .return_value))])
    assert (
        m_yapf.file_resources.GetExcludePatternsForDir.call_args
        == [(m_path.return_value, ), {}])


def test_yapf_yapf_files(iters, patches):
    patched = patches(
        "YapfFiles",
        prefix="envoy.code.check.abstract.yapf")
    path = MagicMock()
    files = iters(cb=lambda i: MagicMock())

    with patched as (m_yapf_files, ):
        assert (
            check.AYapfCheck.yapf_files(path, *files)
            == m_yapf_files.return_value.filter_files.return_value)

    assert (
        m_yapf_files.call_args
        == [(path, ), {}])
    assert (
        m_yapf_files.return_value.filter_files.call_args
        == [(tuple(files), ), {}])


@pytest.mark.parametrize("fix", [None, True, False])
def test_yapf_yapf_format(iters, patches, fix):
    patched = patches(
        "YapfFormatCheck",
        prefix="envoy.code.check.abstract.yapf")
    root_path = MagicMock()
    config_path = MagicMock()
    args = iters(cb=lambda i: MagicMock())
    fix = MagicMock()

    with patched as (m_yapf, ):
        assert (
            check.AYapfCheck.yapf_format(
                root_path,
                config_path,
                fix,
                *args)
            == m_yapf.return_value.run_checks.return_value)

    assert (
        m_yapf.call_args
        == [(root_path,
             config_path,
             fix,
             *args), {}])
    assert (
        m_yapf.return_value.run_checks.call_args
        == [(), {}])


def test_yapf_constructor():
    yapf = check.AYapfCheck("DIRECTORY")
    assert yapf.directory == "DIRECTORY"


@pytest.mark.parametrize("files", [True, False])
async def test_yapf_checker_files(patches, files):
    directory = MagicMock()
    yapf = check.AYapfCheck(directory)
    patched = patches(
        "partial",
        "str",
        ("AYapfCheck.py_files",
         dict(new_callable=PropertyMock)),
        ("AYapfCheck.yapf_files",
         dict(new_callable=PropertyMock)),
        "AYapfCheck.execute_in_batches",
        prefix="envoy.code.check.abstract.yapf")
    batched = [
        set(x for x in range(0, 10)),
        set(x for x in range(1, 7)),
        set(x for x in range(5, 13))]
    expected = batched[0] | batched[1] | batched[2]
    files = (
        [f"FILE{i}" for i in range(0, 5)]
        if files
        else [])

    async def batch_iter(*x):
        for batch in batched:
            yield batch

    with patched as (m_partial, m_str, m_py, m_yapf, m_execute):
        m_py.side_effect = AsyncMock(return_value=files)
        m_execute.side_effect = batch_iter
        assert (
            await yapf.checker_files
            == (set()
                if not files
                else expected))

    assert not (
        hasattr(
            yapf,
            check.AYapfCheck.checker_files.cache_name))
    if not files:
        assert not m_execute.called
        assert not m_partial.called
        assert not m_str.called
        return
    assert (
        m_execute.call_args
        == [(m_partial.return_value, *files), {}])
    assert (
        m_partial.call_args
        == [(m_yapf.return_value, m_str.return_value), {}])
    assert (
        m_str.call_args
        == [(directory.path, ), {}])


def test_yapf_config_path():
    directory = MagicMock()
    yapf = check.AYapfCheck(directory)
    assert (
        yapf.config_path
        == directory.path.joinpath.return_value)
    assert (
        directory.path.joinpath.call_args
        == [(check.abstract.yapf.YAPF_CONFIG, ), {}])
    assert "config_path" not in yapf.__dict__


@pytest.mark.parametrize("files", [True, False])
async def test_yapf_problem_files(patches, files):
    yapf = check.AYapfCheck("DIRECTORY")
    patched = patches(
        "dict",
        ("AwaitableGenerator",
         dict(new_callable=AsyncMock)),
        ("AYapfCheck._problem_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.yapf")

    with patched as (m_dict, m_agen, m_problems):
        result = await yapf.problem_files
        assert (
            result
            == m_dict.return_value
            == getattr(
                yapf,
                check.AFileCodeCheck.problem_files.cache_name)[
                    "problem_files"])

    assert (
        m_dict.call_args
        == [(m_agen.return_value, ), {}])
    assert (
        m_agen.call_args
        == [(m_problems.return_value, ), {}])


@pytest.mark.parametrize("notpy", range(0, 10))
async def test_yapf_py_files(patches, notpy):
    directory = MagicMock()
    yapf = check.AYapfCheck(directory)
    dir_files = []
    patched = patches(
        "set",
        prefix="envoy.code.check.abstract.yapf")

    def path_endswith(x, ext):
        return x != notpy

    for x in range(0, 5):
        f = MagicMock()
        f.endswith.side_effect = partial(path_endswith, x)
        dir_files.append(f)
    files = AsyncMock(return_value=dir_files)
    directory.files = files()

    with patched as (m_set, ):
        assert (
            await yapf.py_files
            == m_set.return_value
            == getattr(
                yapf,
                check.AYapfCheck.py_files.cache_name)["py_files"])
        iterator = m_set.call_args[0][0]
        called = list(iterator)

    assert (
        called
        == [f for i, f in enumerate(dir_files) if i != notpy])
    for f in dir_files:
        assert (
            f.endswith.call_args
            == [(".py", ), {}])


@pytest.mark.parametrize("files", [True, False])
async def test_yapf__problem_files(patches, files):
    directory = MagicMock()
    fix = MagicMock()
    yapf = check.AYapfCheck(directory, fix=fix)
    patched = patches(
        "partial",
        "str",
        "AYapfCheck.yapf_format",
        ("AYapfCheck.config_path",
         dict(new_callable=PropertyMock)),
        ("AYapfCheck.files",
         dict(new_callable=PropertyMock)),
        "AYapfCheck.execute_in_batches",
        prefix="envoy.code.check.abstract.yapf")
    batched = [
        [(f"PATH{x}", f"PROB{x}") for x in range(0, 10)],
        [(f"PATH{x}", f"PROB{x}") for x in range(10, 20)],
        [(f"PATH{x}", f"PROB{x}") for x in range(20, 30)]]
    files = (
        [f"FILE{i}" for i in range(0, 5)]
        if files
        else [])
    expected = batched[0] + batched[1] + batched[2]
    results = []

    async def batch_iter(*x):
        for batch in batched:
            yield batch

    with patched as (m_partial, m_str, m_format, m_conf, m_files, m_execute):
        m_files.side_effect = AsyncMock(return_value=files)
        m_execute.side_effect = batch_iter

        async for f, p in yapf._problem_files:
            results.append((f, p))

        assert (
            results
            == ([]
                if not files
                else expected))

    assert not (
        hasattr(
            yapf,
            check.AYapfCheck._problem_files.cache_name))
    if not files:
        assert not m_execute.called
        assert not m_partial.called
        assert not m_str.called
        return
    assert (
        m_execute.call_args
        == [(m_partial.return_value, *files), {}])
    assert (
        m_partial.call_args
        == [(m_format,
             m_str.return_value,
             m_str.return_value,
             fix), {}])
    assert (
        m_str.call_args_list
        == [[(directory.path, ), {}],
            [(m_conf.return_value, ), {}]])
