
from functools import partial
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from envoy.code import check


def test_yapf_yapf_files(patches):
    patched = patches(
        "yapf",
        "set",
        prefix="envoy.code.check.abstract.yapf")
    dir_path = MagicMock()
    py_files = MagicMock()

    with patched as (m_yapf, m_set):
        assert (
            check.AYapfCheck.yapf_files(dir_path, py_files)
            == m_set.return_value)

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


@pytest.mark.parametrize("fix", [None, True, False])
async def test_yapf_yapf_format(patches, fix):
    kwargs = (
        dict(fix=fix)
        if fix is not None
        else {})
    patched = patches(
        "yapf",
        "AYapfCheck._yapf_result",
        prefix="envoy.code.check.abstract.yapf")
    rel_path = MagicMock()
    abs_path = MagicMock()
    config_path = MagicMock()

    with patched as (m_yapf, m_result):
        assert (
            check.AYapfCheck.yapf_format(
                rel_path,
                abs_path,
                config_path,
                **kwargs)
            == m_result.return_value)

    assert (
        m_result.call_args
        == [(rel_path,
             m_yapf.yapf_api.FormatFile.return_value),
            {}])
    assert (
        m_yapf.yapf_api.FormatFile.call_args
        == [(abs_path, ),
            dict(style_config=config_path,
                 in_place=fix or False,
                 print_diff=not fix)])


@pytest.mark.parametrize(
    "changed",
    [None, True, False, "", [], "CHANGED"])
@pytest.mark.parametrize(
    "reformatted",
    [None, True, False, "", [], "REFORMATTED"])
def test_yapf__yapf_result(changed, reformatted):
    path = MagicMock()
    encoding = MagicMock()
    assert (
        check.AYapfCheck._yapf_result(path, (reformatted, encoding, changed))
        == ((path, [])
            if not (changed or reformatted)
            else ((path, [f"Issues found: {path}\n{reformatted}"])
                  if reformatted
                  else (path, [f"Issues found (fixed): {path}"]))))


def test_yapf_constructor():
    yapf = check.AYapfCheck("DIRECTORY")
    assert yapf.directory == "DIRECTORY"


async def test_yapf_checker_files(patches):
    directory = MagicMock()
    yapf = check.AYapfCheck(directory)
    patched = patches(
        ("AYapfCheck.yapf_file_resources",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.yapf")

    with patched as (m_yapf, ):
        yapf_files = AsyncMock()
        m_yapf.side_effect = yapf_files
        assert (
            await yapf.checker_files
            == directory.relative_paths.return_value)

    assert (
        directory.relative_paths.call_args
        == [(yapf_files.return_value, ), {}])
    assert not (
        hasattr(
            yapf,
            check.AYapfCheck.checker_files.cache_name))


@pytest.mark.parametrize("files", [True, False])
async def test_yapf_problem_files(patches, files):
    yapf = check.AYapfCheck("DIRECTORY")
    patched = patches(
        "dict",
        ("AwaitableGenerator",
         dict(new_callable=AsyncMock)),
        ("AYapfCheck.files",
         dict(new_callable=PropertyMock)),
        ("AYapfCheck._problem_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.yapf")

    with patched as (m_dict, m_agen, m_files, m_problems):
        m_files.side_effect = AsyncMock(return_value=files)
        result = await yapf.problem_files
        assert (
            result
            == (m_dict.return_value
                if files
                else {}))

    if files:
        assert (
            m_dict.call_args
            == [(m_agen.return_value, ), {}])
    else:
        assert not m_dict.called
        assert not m_agen.called
    assert (
        getattr(
            yapf,
            check.ACodeCheck.problem_files.cache_name)[
                "problem_files"]
        == result)


@pytest.mark.parametrize("notpy", range(0, 10))
async def test_yapf_py_files(notpy):
    directory = MagicMock()
    yapf = check.AYapfCheck(directory)
    dir_files = []

    def path_endswith(x, ext):
        return x != notpy

    for x in range(0, 5):
        f = MagicMock()
        f.endswith.side_effect = partial(path_endswith, x)
        dir_files.append(f)
    files = AsyncMock(return_value=dir_files)
    directory.files = files()
    assert (
        await yapf.py_files
        == directory.absolute_paths.return_value
        == getattr(
            yapf,
            check.AYapfCheck.py_files.cache_name)["py_files"])

    iterator = directory.absolute_paths.call_args[0][0]
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


@pytest.mark.parametrize(
    "py_files", [None, True, False, "", [], ["PYFILES"]])
async def test_yapf_yapf_file_resources(patches, py_files):
    directory = MagicMock()
    yapf = check.AYapfCheck(directory)
    patched = patches(
        "str",
        ("AYapfCheck.py_files",
         dict(new_callable=PropertyMock)),
        "AYapfCheck.execute",
        "AYapfCheck.yapf_files",
        prefix="envoy.code.check.abstract.yapf")

    with patched as (m_str, m_files, m_execute, m_yapf):
        m_files.side_effect = AsyncMock(return_value=py_files)
        assert (
            await yapf.yapf_file_resources
            == (m_execute.return_value
                if py_files
                else set()))

    assert not (
        hasattr(
            yapf,
            check.AYapfCheck.yapf_file_resources.cache_name))
    if not py_files:
        assert not m_str.called
        assert not m_execute.called
        return
    assert (
        m_str.call_args
        == [(directory.path, ), {}])
    assert (
        m_execute.call_args
        == [(m_yapf,
             m_str.return_value,
             py_files),
            {}])


@pytest.mark.parametrize("n", range(1, 5))
@pytest.mark.parametrize("files", [True, False])
async def test_yapf__problem_files(patches, n, files):
    yapf = check.AYapfCheck("DIRECTORY")
    patched = patches(
        "tasks",
        ("AYapfCheck._yapf_checks",
         dict(new_callable=PropertyMock)),
        ("AYapfCheck.files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.yapf")
    results = []
    expected = []

    async def iter_tasks(tasks):
        for i in range(0, 7):
            result = f"PATH{i}", i % n
            if i % n:
                expected.append(result)
            yield result

    with patched as (m_tasks, m_checks, m_files):
        m_tasks.concurrent.side_effect = iter_tasks
        m_files.side_effect = AsyncMock(return_value=files)
        async for result in yapf._problem_files:
            results.append(result)

    assert results == expected
    assert not (
        hasattr(
            yapf,
            check.AYapfCheck._problem_files.cache_name))
    if not files:
        assert not m_tasks.concurrent.called
        assert not m_checks.called
        return
    assert (
        m_tasks.concurrent.call_args
        == [(m_checks.return_value, ), {}])


async def test_yapf__yapf_checks(patches):
    directory = MagicMock()
    yapf = check.AYapfCheck(directory)
    patched = patches(
        "str",
        ("AYapfCheck.absolute_paths",
         dict(new_callable=PropertyMock)),
        ("AYapfCheck.config_path",
         dict(new_callable=PropertyMock)),
        ("AYapfCheck.fix",
         dict(new_callable=PropertyMock)),
        ("AYapfCheck.execute",
         dict(new_callable=MagicMock)),
        "AYapfCheck.yapf_format",
        prefix="envoy.code.check.abstract.yapf")
    results = []
    paths = [f"PATH{i}" for i in range(0, 5)]

    with patched as (m_str, m_paths, m_config, m_fix, m_execute, m_yapf):
        m_paths.side_effect = AsyncMock(return_value=paths)
        async for yapf_check in yapf._yapf_checks:
            results.append(yapf_check)

    assert (
        results
        == [m_execute.return_value] * 5)
    assert (
        m_execute.call_args_list
        == [[(m_yapf,
              m_str.return_value,
              path,
              m_str.return_value,
              m_fix.return_value),
             {}]
            for path in paths])
    expected_str_calls = []
    for path in paths:
        expected_str_calls.extend(
            [[(directory.relative_path.return_value, ), {}],
             [(m_config.return_value, ), {}]])
    assert (
        m_str.call_args_list
        == expected_str_calls)
    assert (
        directory.relative_path.call_args_list
        == [[(path, ), {}] for path in paths])
