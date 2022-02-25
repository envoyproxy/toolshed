
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from envoy.code import check


def test_shellcheck_run_shellcheck(patches):
    patched = patches(
        "Shellcheck",
        prefix="envoy.code.check.abstract.shellcheck")
    path = MagicMock()
    args = [MagicMock() for x in range(0, 5)]

    with patched as (m_shellcheck, ):
        assert (
            check.AShellcheckCheck.run_shellcheck(path, *args)
            == m_shellcheck.return_value.run_checks.return_value)

    assert (
        m_shellcheck.call_args
        == [(path, *args), {}])
    assert (
        m_shellcheck.return_value.run_checks.call_args
        == [(), {}])


def test_shellcheck_constructor():
    shellcheck = check.AShellcheckCheck("DIRECTORY")
    assert shellcheck.directory == "DIRECTORY"
    assert (
        shellcheck.shebang_re_expr
        == "|".join(check.abstract.shellcheck.SHEBANG_RE))
    assert "shebang_re_expr" not in shellcheck.__dict__


@pytest.mark.parametrize(
    "sh_files",
    [set(),
     set(f"F{i}" for i in range(0, 5)),
     set(f"F{i}" for i in range(0, 10))])
@pytest.mark.parametrize(
    "shebang_files",
    [set(),
     set(f"F{i}" for i in range(0, 5)),
     set(f"F{i}" for i in range(0, 10))])
async def test_shellcheck_checker_files(patches, sh_files, shebang_files):
    shellcheck = check.AShellcheckCheck("DIRECTORY")
    patched = patches(
        ("AShellcheckCheck.sh_files",
         dict(new_callable=PropertyMock)),
        ("AShellcheckCheck.shebang_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.shellcheck")

    with patched as (m_sh, m_shebang):
        m_sh.side_effect = AsyncMock(return_value=sh_files)
        m_shebang.side_effect = AsyncMock(return_value=shebang_files)
        assert (
            await shellcheck.checker_files
            == (sh_files | shebang_files))

    assert not (
        hasattr(
            shellcheck,
            check.AShellcheckCheck.checker_files.cache_name))


def test_shellcheck_checker_path_match_exclude_re(patches):
    shellcheck = check.AShellcheckCheck("DIRECTORY")
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.shellcheck")

    with patched as (m_re, ):
        assert (
            shellcheck.path_match_exclude_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [("|".join(check.abstract.shellcheck.SHELLCHECK_NOMATCH_RE), ),
            {}])
    assert "path_match_exclude_re" in shellcheck.__dict__


def test_shellcheck_checker_path_match_re(patches):
    shellcheck = check.AShellcheckCheck("DIRECTORY")
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.shellcheck")

    with patched as (m_re, ):
        assert (
            shellcheck.path_match_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [("|".join(check.abstract.shellcheck.SHELLCHECK_MATCH_RE), ),
            {}])
    assert "path_match_re" in shellcheck.__dict__


@pytest.mark.parametrize("files", [True, False])
async def test_shellcheck_problem_files(patches, files):
    shellcheck = check.AShellcheckCheck("DIRECTORY")
    patched = patches(
        ("AShellcheckCheck.files",
         dict(new_callable=PropertyMock)),
        ("AShellcheckCheck.shellcheck_executable",
         dict(new_callable=PropertyMock)),
        "AShellcheckCheck.execute_in_batches",
        prefix="envoy.code.check.abstract.shellcheck")
    batched = [
        {f"K{x}": "V1{x}" for x in range(0, 10)},
        {f"K{x}": "V2{x}" for x in range(1, 7)},
        {f"K{x}": "V3{x}" for x in range(5, 13)}]
    if files:
        files = [f"F{i}" for i in range(0, 5)]
    expected = {}
    for d in batched:
        expected.update(d)

    async def iter_batched(*args):
        for batch in batched:
            yield batch

    with patched as (m_files, m_exec, m_batches):
        m_files.side_effect = AsyncMock(return_value=files)
        m_batches.side_effect = iter_batched
        assert (
            await shellcheck.problem_files
            == (expected
                if files
                else {})
            == getattr(
                shellcheck,
                check.ACodeCheck.problem_files.cache_name)[
                    "problem_files"])

    if not files:
        assert not m_exec.called
        return
    assert (
        m_batches.call_args
        == [(m_exec.return_value, *files), {}])


@pytest.mark.parametrize("files", [True, False])
async def test_shellcheck_sh_files(patches, files):
    directory = MagicMock()
    shellcheck = check.AShellcheckCheck(directory)
    patched = patches(
        "set",
        ("AShellcheckCheck.path_match_exclude_re",
         dict(new_callable=PropertyMock)),
        ("AShellcheckCheck.path_match_re",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.shellcheck")
    files = AsyncMock(return_value=range(0, 20))
    directory.files = files()

    with patched as (m_set, m_exc_re, m_re):
        m_exc_re.return_value.match.side_effect = lambda x: x % 3
        m_re.return_value.match.side_effect = lambda x: x % 2
        assert (
            await shellcheck.sh_files
            == m_set.return_value)
        iterator = m_set.call_args[0][0]
        called = list(iterator)

    assert (
        called
        == [x for x in range(0, 20)
            if not x % 3
            and x % 2])
    assert (
        m_re.return_value.match.call_args_list
        == [[(x, ), {}] for x in range(0, 20)])
    assert (
        m_exc_re.return_value.match.call_args_list
        == [[(x, ), {}]
            for x
            in range(0, 20)
            if x % 2])
    assert not (
        hasattr(
            shellcheck,
            check.AShellcheckCheck.sh_files.cache_name))


async def test_shellcheck_shebang_files(patches):
    directory = MagicMock()
    shellcheck = check.AShellcheckCheck(directory)
    patched = patches(
        ("AShellcheckCheck.shebang_re_expr",
         dict(new_callable=PropertyMock)),
        ("AShellcheckCheck._possible_shebang_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.shellcheck")
    directory.grep = AsyncMock()

    with patched as (m_re, m_files):
        files = AsyncMock()
        m_files.side_effect = files
        assert (
            await shellcheck.shebang_files
            == directory.grep.return_value)

    assert (
        directory.grep.call_args
        == [(['-lE', m_re.return_value], ),
            dict(target=files.return_value)])
    assert not (
        hasattr(
            shellcheck,
            check.AShellcheckCheck.shebang_files.cache_name))


@pytest.mark.parametrize("command", [None, False, "", "COMMAND"])
def test_shellcheck_shellcheck_command(patches, command):
    shellcheck = check.AShellcheckCheck("DIRECTORY")
    patched = patches(
        "shutil",
        prefix="envoy.code.check.abstract.shellcheck")

    with patched as (m_shutil, ):
        m_shutil.which.return_value = command
        if not command:
            with pytest.raises(check.exceptions.ShellcheckError) as e:
                shellcheck.shellcheck_command
            assert e.value.args[0] == 'Unable to find shellcheck command'
        else:
            assert shellcheck.shellcheck_command == command

    assert (
        m_shutil.which.call_args
        == [("shellcheck", ), {}])
    if command:
        assert "shellcheck_command" in shellcheck.__dict__


def test_shellcheck_shellcheck_executable(patches):
    directory = MagicMock()
    shellcheck = check.AShellcheckCheck(directory)
    patched = patches(
        "partial",
        "AShellcheckCheck.run_shellcheck",
        ("AShellcheckCheck.shellcheck_command",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.shellcheck")

    with patched as (m_partial, m_run, m_command):
        assert (
            shellcheck.shellcheck_executable
            == m_partial.return_value)

    assert (
        m_partial.call_args
        == [(m_run,
             directory.path,
             m_command.return_value,
             "-x"), {}])


@pytest.mark.parametrize("files", [True, False])
async def test_shellcheck__possible_shebang_files(patches, files):
    directory = MagicMock()
    shellcheck = check.AShellcheckCheck(directory)
    patched = patches(
        "set",
        ("AShellcheckCheck.path_match_exclude_re",
         dict(new_callable=PropertyMock)),
        ("AShellcheckCheck.path_match_re",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.shellcheck")
    files = AsyncMock(return_value=range(0, 20))
    directory.files = files()

    with patched as (m_set, m_exc_re, m_re):
        m_re.return_value.match.side_effect = lambda x: not (x % 2)
        m_exc_re.return_value.match.side_effect = lambda x: x % 3
        assert (
            await shellcheck._possible_shebang_files
            == m_set.return_value)
        iterator = m_set.call_args[0][0]
        called = list(iterator)

    assert (
        called
        == [x for x in range(0, 20)
            if not (x % 3)
            and x % 2])
    assert (
        m_re.return_value.match.call_args_list
        == [[(x, ), {}] for x in range(0, 20)])
    assert (
        m_exc_re.return_value.match.call_args_list
        == [[(x, ), {}]
            for x
            in range(0, 20)
            if x % 2])
    assert not (
        hasattr(
            shellcheck,
            check.AShellcheckCheck.sh_files.cache_name))
