
from functools import partial
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from envoy.code import check


def test_yapf__yapf_files(patches):
    patched = patches(
        "yapf",
        "set",
        "directory_context",
        prefix="envoy.code.check.abstract.yapf")
    dir_path = MagicMock()
    py_files = MagicMock()

    with patched as (m_yapf, m_set, m_dir_ctx):
        assert (
            check.abstract.yapf._yapf_files(dir_path, py_files)
            == m_set.return_value)

    assert (
        m_dir_ctx.call_args
        == [(dir_path, ), {}])
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
        == [(dir_path, ), {}])


def test_yapf_yapf_files(patches):
    patched = patches(
        "_yapf_files",
        prefix="envoy.code.check.abstract.yapf")
    path = MagicMock()
    files = [MagicMock() for i in range(0, 5)]

    with patched as (m_yapf_files, ):
        assert (
            check.AYapfCheck.yapf_files(path, *files)
            == m_yapf_files.return_value)

    assert (
        m_yapf_files.call_args
        == [(path, tuple(files)), {}])


@pytest.mark.parametrize("fix", [None, True, False])
def test_yapf_yapf_format(patches, fix):
    patched = patches(
        "YapfFormatCheck",
        prefix="envoy.code.check.abstract.yapf")
    root_path = MagicMock()
    config_path = MagicMock()
    args = [MagicMock() for i in range(0, 5)]
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
                check.ACodeCheck.problem_files.cache_name)[
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
