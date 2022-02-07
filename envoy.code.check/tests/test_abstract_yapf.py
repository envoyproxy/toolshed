
from functools import partial
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from envoy.code import check


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
        ("AYapfCheck.files",
         dict(new_callable=PropertyMock)),
        ("AYapfCheck._problem_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.yapf")

    with patched as (m_dict, m_files, m_problems):
        m_files.side_effect = AsyncMock(return_value=files)
        problems = AsyncMock()
        m_problems.side_effect = problems
        result = await yapf.problem_files
        assert (
            result
            == (m_dict.return_value
                if files
                else {}))

    if files:
        assert (
            m_dict.call_args
            == [(problems.return_value, ), {}])
    else:
        assert not m_dict.called
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
        == directory.absolute_paths.return_value)
    iterator = directory.absolute_paths.call_args[0][0]
    called = list(iterator)
    assert (
        called
        == [f for i, f in enumerate(dir_files) if i != notpy])
    for f in dir_files:
        assert (
            f.endswith.call_args
            == [(".py", ), {}])
    assert not (
        hasattr(
            yapf,
            check.AYapfCheck.py_files.cache_name))


def test_yapf_yapf_config_path():
    directory = MagicMock()
    yapf = check.AYapfCheck(directory)
    assert (
        yapf.yapf_config_path
        == directory.path.joinpath.return_value)
    assert (
        directory.path.joinpath.call_args
        == [(check.abstract.yapf.YAPF_CONFIG, ), {}])
    assert "yapf_config_path" not in yapf.__dict__


@pytest.mark.parametrize(
    "py_files", [None, True, False, "", [], ["PYFILES"]])
async def test_yapf_yapf_file_resources(patches, py_files):
    directory = MagicMock()
    yapf = check.AYapfCheck(directory)
    patched = patches(
        "str",
        "yapf",
        ("AYapfCheck.py_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.yapf")

    with patched as (m_str, m_yapf, m_files):
        m_files.side_effect = AsyncMock(return_value=py_files)
        assert (
            await yapf.yapf_file_resources
            == (m_yapf.file_resources.GetCommandLineFiles.return_value
                if py_files
                else []))

    assert not (
        hasattr(
            yapf,
            check.AYapfCheck.yapf_file_resources.cache_name))
    if not py_files:
        assert not m_yapf.file_resources.GetCommandLineFiles.called
        assert not m_yapf.file_resources.GetExcludePatternsForDir.called
        assert not m_str.called
        return
    assert (
        m_yapf.file_resources.GetCommandLineFiles.call_args
        == [(py_files, ),
            dict(recursive=False,
                 exclude=(m_yapf.file_resources.GetExcludePatternsForDir
                                               .return_value))])
    assert (
        m_yapf.file_resources.GetExcludePatternsForDir.call_args
        == [(m_str.return_value, ), {}])
    assert (
        m_str.call_args
        == [(directory.path, ), {}])


async def test_yapf__problem_files(patches):
    yapf = check.AYapfCheck("DIRECTORY")
    patched = patches(
        "async_list",
        "async_map",
        ("AYapfCheck.absolute_paths",
         dict(new_callable=PropertyMock)),
        "AYapfCheck.yapf_format",
        "AYapfCheck._handle_problem",
        prefix="envoy.code.check.abstract.yapf")

    with patched as (m_list, m_map, m_paths, m_format, m_handle):
        m_paths.side_effect = AsyncMock()
        assert (
            await yapf._problem_files
            == m_list.return_value)
        predicate = m_list.call_args[1]["predicate"]

    assert (
        m_list.call_args
        == [(m_map.return_value, ),
            dict(predicate=predicate, result=m_handle)])
    result = MagicMock()
    assert (
        predicate(result)
        == result.__getitem__.return_value.__getitem__.return_value)
    assert (
        result.__getitem__.call_args
        == [(1, ), {}])
    assert (
        result.__getitem__.return_value.__getitem__.call_args
        == [(2, ), {}])
    assert not (
        hasattr(
            yapf,
            check.AYapfCheck.problem_files.cache_name))


@pytest.mark.parametrize("fix", [True, False])
async def test_yapf_yapf_format(patches, fix):
    directory = MagicMock()
    yapf = check.AYapfCheck(directory)
    patched = patches(
        "str",
        "yapf",
        ("AYapfCheck.fix",
         dict(new_callable=PropertyMock)),
        ("AYapfCheck.yapf_config_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.yapf")
    python_file = MagicMock()

    with patched as (m_str, m_yapf, m_fix, m_config):
        m_fix.return_value = fix
        assert (
            yapf.yapf_format(python_file)
            == (directory.relative_path.return_value,
                m_yapf.yapf_api.FormatFile.return_value))

    assert (
        directory.relative_path.call_args
        == [(python_file, ), {}])
    assert (
        m_yapf.yapf_api.FormatFile.call_args
        == [(python_file, ),
            dict(style_config=m_str.return_value,
                 in_place=fix,
                 print_diff=not fix)])
    assert (
        m_str.call_args
        == [(m_config.return_value, ), {}])


@pytest.mark.parametrize("changed", [True, False])
@pytest.mark.parametrize(
    "reformatted", [None, True, False, "", [], "REFORMATTED"])
def test_yapf__handle_problem(changed, reformatted):
    yapf = check.AYapfCheck("DIRECTORY")
    path = MagicMock()
    encoding = MagicMock()
    assert (
        yapf._handle_problem((path, (reformatted, encoding, changed)))
        == ((path, [f"Issues found (fixed): {path}"])
            if changed and not reformatted
            else (path, [f"Issues found: {path}\n{reformatted}"])))
