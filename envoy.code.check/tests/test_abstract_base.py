
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from envoy.code import check


@abstracts.implementer(check.AFileCodeCheck)
class DummyCodeCheck:

    @property
    def checker_files(self):
        return super().checker_files

    @property
    def problem_files(self):
        return super().problem_files


@pytest.mark.parametrize("fix", [None, True, False])
@pytest.mark.parametrize("binaries", [None, "BINARIES"])
@pytest.mark.parametrize("config", [None, "CONFIG"])
@pytest.mark.parametrize("pool", [None, "POOL"])
@pytest.mark.parametrize("loop", [None, "LOOP"])
async def test_code_check_constructor(fix, binaries, pool, loop, config):
    kwargs = {}
    if fix is not None:
        kwargs["fix"] = fix
    if binaries is not None:
        kwargs["binaries"] = binaries
    if config is not None:
        kwargs["config"] = config
    if loop is not None:
        kwargs["loop"] = loop
    if pool is not None:
        kwargs["pool"] = pool

    with pytest.raises(TypeError):
        check.AFileCodeCheck("DIRECTORY", **kwargs)

    code_check = DummyCodeCheck("DIRECTORY", **kwargs)
    assert code_check.directory == "DIRECTORY"
    assert code_check._fix == (fix if fix is not None else False)
    assert code_check.fix == code_check._fix
    assert "fix" not in code_check.__dict__
    assert code_check._binaries == binaries
    assert code_check.binaries == binaries
    assert "binaries" not in code_check.__dict__
    assert code_check._config == config
    assert code_check._loop == loop
    assert code_check._pool == pool

    for iface_prop in ["checker_files", "problem_files"]:
        with pytest.raises(NotImplementedError):
            await getattr(code_check, iface_prop)


@pytest.mark.parametrize("config", [None, "CONFIG"])
def test_code_check_config(patches, config):
    kwargs = {}
    if config is not None:
        kwargs["config"] = MagicMock()
    code_check = DummyCodeCheck("DIRECTORY", **kwargs)
    patched = patches(
        "yaml",
        prefix="envoy.code.check.abstract.base")

    with patched as (m_yaml, ):
        assert (
            code_check.config
            == ({}
                if not config
                else m_yaml.safe_load.return_value))

    assert "config" in code_check.__dict__
    if not config:
        assert not m_yaml.safe_load.called
        return
    assert (
        m_yaml.safe_load.call_args
        == [(kwargs["config"].read_text.return_value, ), {}])
    assert (
        kwargs["config"].read_text.call_args
        == [(), {}])


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
        ("AFileCodeCheck.checker_files",
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
            check.AFileCodeCheck.files.cache_name)[
                "files"]
        == result)


@abstracts.implementer(check.AProjectCodeCheck)
class DummyProjectCodeCheck:
    pass


async def test_project_code_check_constructor(iters, patches):
    args = iters()
    kwargs = iters(dict)
    project = MagicMock()
    patched = patches(
        "ACodeCheck.__init__",
        prefix="envoy.code.check.abstract.base")

    with patched as (m_super, ):
        m_super.return_value = None
        checker = DummyProjectCodeCheck(project, *args, **kwargs)

    assert isinstance(checker, check.ACodeCheck)
    assert (
        m_super.call_args
        == [(project.directory, *args), kwargs])
