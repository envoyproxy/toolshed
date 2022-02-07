
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from envoy.code import check


@abstracts.implementer(check.ACodeCheck)
class DummyCodeCheck:

    @property
    def checker_files(self):
        return super().checker_files

    @property
    def problem_files(self):
        return super().problem_files


@pytest.mark.parametrize("fix", [None, True, False])
async def test_code_check_constructor(fix):
    kwargs = (
        dict(fix=fix)
        if fix is not None
        else {})

    with pytest.raises(TypeError):
        check.ACodeCheck("DIRECTORY", **kwargs)

    code_check = DummyCodeCheck("DIRECTORY", **kwargs)
    assert code_check.directory == "DIRECTORY"
    assert code_check._fix == (fix if fix is not None else False)
    assert code_check.fix == code_check._fix
    assert "fix" not in code_check.__dict__

    for iface_prop in ["checker_files", "problem_files"]:
        with pytest.raises(NotImplementedError):
            await getattr(code_check, iface_prop)


async def test_code_check_absolute_paths(patches):
    directory = MagicMock()
    code_check = DummyCodeCheck(directory)
    patched = patches(
        ("ACodeCheck.files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.base")

    with patched as (m_files, ):
        files = AsyncMock()
        m_files.side_effect = files
        result = await code_check.absolute_paths

    assert (
        result
        == directory.absolute_paths.return_value)
    assert (
        directory.absolute_paths.call_args
        == [(files.return_value, ), {}])
    assert (
        getattr(
            code_check,
            check.ACodeCheck.absolute_paths.cache_name)[
                "absolute_paths"]
        == result)


@pytest.mark.parametrize(
    "files",
    [set(),
     set(f"F{i}" for i in range(0, 5)),
     set(f"F{i}" for i in range(0, 10))])
@pytest.mark.parametrize(
    "dir_files",
    [set(),
     set(f"F{i}" for i in range(0, 5)),
     set(f"F{i}" for i in range(0, 10))])
async def test_code_check_files(patches, files, dir_files):
    directory = MagicMock()
    code_check = DummyCodeCheck(directory)
    patched = patches(
        ("ACodeCheck.checker_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.base")
    directory_files = AsyncMock(return_value=dir_files)
    directory.files = directory_files()

    with patched as (m_files, ):
        checker_files = AsyncMock(return_value=files)
        m_files.side_effect = checker_files
        result = await code_check.files

    assert (
        result
        == dir_files & files)
    if not dir_files:
        assert not checker_files.called
    assert (
        getattr(
            code_check,
            check.ACodeCheck.files.cache_name)[
                "files"]
        == result)
