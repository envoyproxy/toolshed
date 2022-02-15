
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from envoy.code import check


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
        "dict",
        ("AShellcheckCheck.files",
         dict(new_callable=PropertyMock)),
        ("AShellcheckCheck._problem_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.shellcheck")

    with patched as (m_dict, m_files, m_problems):
        m_files.side_effect = AsyncMock(return_value=files)
        problems = AsyncMock()
        m_problems.side_effect = problems
        result = await shellcheck.problem_files
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
            shellcheck,
            check.ACodeCheck.problem_files.cache_name)[
                "problem_files"]
        == result)


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


@pytest.mark.parametrize("files", [True, False])
async def test_shellcheck_shebang_files(patches, files):
    directory = MagicMock()
    shellcheck = check.AShellcheckCheck(directory)
    patched = patches(
        "set",
        ("AShellcheckCheck.shebang_re_expr",
         dict(new_callable=PropertyMock)),
        ("AShellcheckCheck._possible_shebang_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.shellcheck")
    directory.grep = AsyncMock(return_value=range(0, 20))
    files = [f"F{i}" for i in range(0, 5)]

    with patched as (m_set, m_re, m_files):
        m_files.side_effect = AsyncMock(return_value=files)
        assert (
            await shellcheck.shebang_files
            == m_set.return_value)
        iterator = m_set.call_args[0][0]
        called = list(iterator)

    assert called == list(range(0, 20))
    assert (
        directory.grep.call_args
        == [(['-lE', m_re.return_value, *files], ), {}])
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


async def test_shellcheck__problem_files(patches):
    directory = MagicMock()
    shellcheck = check.AShellcheckCheck(directory)
    patched = patches(
        ("AShellcheckCheck.files",
         dict(new_callable=PropertyMock)),
        ("AShellcheckCheck.shellcheck_command",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.shellcheck")
    directory.shell.parallel = AsyncMock()
    paths = [f"P{i}" for i in range(0, 5)]

    with patched as (m_files, m_command):
        m_files.side_effect = AsyncMock(
            return_value=paths)
        assert (
            await shellcheck._problem_files
            == directory.shell.parallel.return_value)

        command_iter = directory.shell.parallel.call_args[0][0]
        command_list = list(command_iter)
        predicate = directory.shell.parallel.call_args[1]["predicate"]
        result = directory.shell.parallel.call_args[1]["result"]

    assert (
        command_list
        == [[m_command.return_value, "-x", path]
            for path in paths])
    assert (
        directory.shell.parallel.call_args
        == [(command_iter, ), dict(predicate=predicate, result=result)])
    predicate_result = MagicMock()
    assert predicate(predicate_result) == predicate_result.returncode
    result_response = MagicMock()
    assert (
        result(result_response)
        == (result_response.args.__getitem__.return_value,
            [f"Issues found: {result_response.args.__getitem__.return_value}\n"
             f"{result_response.stdout}"]))
    assert (
        result_response.args.__getitem__.call_args_list
        == [[(-1, ), {}], [(-1, ), {}]])
    assert not (
        hasattr(
            shellcheck,
            check.AShellcheckCheck._problem_files.cache_name))


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
