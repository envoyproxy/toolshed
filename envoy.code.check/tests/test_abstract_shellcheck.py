
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio.core import subprocess

from envoy.code import check


def test_shellcheck_constructor():
    shellcheck = check.abstract.shellcheck.Shellcheck("PATH")
    assert isinstance(shellcheck, subprocess.ISubprocessHandler)
    assert isinstance(shellcheck, subprocess.ASubprocessHandler)


def test_shellcheck_error_line_re(patches):
    shellcheck = check.abstract.shellcheck.Shellcheck("PATH")
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.shellcheck")

    with patched as (m_re, ):
        assert (
            shellcheck.error_line_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [(check.abstract.shellcheck.SHELLCHECK_ERROR_LINE_RE, ),
            {}])
    assert "error_line_re" in shellcheck.__dict__


def test_shellcheck_handle():
    shellcheck = check.abstract.shellcheck.Shellcheck("PATH")
    assert shellcheck.handle("RESPONSE") == {}


def test_shellcheck_handle_error(patches):
    shellcheck = check.abstract.shellcheck.Shellcheck("PATH")
    patched = patches(
        "Shellcheck._render_errors",
        "Shellcheck._shellcheck_errors",
        prefix="envoy.code.check.abstract.shellcheck")
    response = MagicMock()

    with patched as (m_render, m_errors):
        assert (
            shellcheck.handle_error(response)
            == m_render.return_value)

    assert (
        m_render.call_args
        == [(m_errors.return_value, ), {}])
    assert (
        m_errors.call_args
        == [(response, ), {}])


@pytest.mark.parametrize("matched", [True, False])
def test_shellcheck_parse_error_line(patches, matched):
    shellcheck = check.abstract.shellcheck.Shellcheck("PATH")
    patched = patches(
        "int",
        ("Shellcheck.error_line_re",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.shellcheck")
    matched_re = (
        MagicMock()
        if matched
        else None)
    line = MagicMock()

    with patched as (m_int, m_re):
        m_re.return_value.search.return_value = matched_re
        assert (
            shellcheck.parse_error_line(line)
            == ((matched_re.groups.return_value.__getitem__.return_value,
                 m_int.return_value)
                if matched
                else ("", None)))

    assert (
        m_re.return_value.search.call_args
        == [(line, ), {}])
    if matched:
        assert (
            m_int.call_args
            == [(matched_re.groups.return_value.__getitem__.return_value, ),
                {}])
        assert (
            matched_re.groups.call_args_list
            == [[(), {}]] * 2)
        assert (
            matched_re.groups.return_value.__getitem__.call_args_list
            == [[(0, ), {}], [(1, ), {}]])


def test_shellcheck__render_errors(patches):
    shellcheck = check.abstract.shellcheck.Shellcheck("PATH")
    patched = patches(
        "Shellcheck._render_file_errors",
        prefix="envoy.code.check.abstract.shellcheck")
    errors = [
        (MagicMock(), MagicMock())
        for i in range(0, 5)]

    with patched as (m_render, ):
        assert (
            shellcheck._render_errors(errors)
            == {e: m_render.return_value
                for e, info
                in errors})

    assert (
        m_render.call_args_list
        == [[(e, info), {}]
            for e, info
            in errors])


@pytest.mark.parametrize("line_nums", range(0, 5))
def test_shellcheck__render_file_errors(patches, line_nums):
    shellcheck = check.abstract.shellcheck.Shellcheck("PATH")
    patched = patches(
        "str",
        prefix="envoy.code.check.abstract.shellcheck")
    path = MagicMock()
    errors = MagicMock()
    line_numbers = [MagicMock() for i in range(0, line_nums)]
    lines = [f"LINE{i}" for i in range(0, 3)]
    line_or_lines = (
        "lines"
        if line_nums > 1
        else "line")

    def getitem(k):
        if k == "line_numbers":
            return line_numbers
        return lines

    errors.__getitem__.side_effect = getitem
    joined_line_numbers = ", ".join(str(line) for line in line_numbers)

    with patched as (m_str, ):
        m_str.side_effect = lambda x: str(x)
        assert (
            shellcheck._render_file_errors(path, errors)
            == ["\n".join(
                [f"{path} ({line_or_lines}: {joined_line_numbers})",
                 *lines])])


@pytest.mark.parametrize("filename", [None, "FILENAME"])
def test_shellcheck__shellcheck_error_info(patches, filename):
    shellcheck = check.abstract.shellcheck.Shellcheck("PATH")
    patched = patches(
        "dict",
        prefix="envoy.code.check.abstract.shellcheck")
    args = (
        (filename, )
        if filename is not None
        else ())

    with patched as (m_dict, ):
        assert (
            shellcheck._shellcheck_error_info(*args)
            == (filename, m_dict.return_value))

    assert (
        m_dict.call_args
        == [(), dict(line_numbers=[], lines=[])])


SHELLCHECK_INPUTS = (
    (),
    ("", ),
    ("MATCH FNAME1 23",
     "DATA 0",
     "DATA 1",
     "DATA 2",
     "",
     "MATCH FNAME1 73",
     "MORE DATA 0",
     "MORE DATA 1",
     "MORE DATA 2",
     "",
     "MATCH FNAME2 23",
     "MORE DATA 0",
     "MORE DATA 1",
     "MORE DATA 2",
     ""),
    ("",
     "MATCH FNAME1 23",
     "DATA 0",
     "DATA 1",
     "DATA 2",
     "",
     "MATCH FNAME1 73",
     "MORE DATA 0",
     "MORE DATA 1",
     "MORE DATA 2",
     "",
     "MATCH FNAME2 23",
     "MORE DATA 0",
     "MORE DATA 1",
     "MORE DATA 2",
     ""))


@pytest.mark.parametrize("input", SHELLCHECK_INPUTS)
def test_shellcheck__shellcheck_errors(patches, input):
    shellcheck = check.abstract.shellcheck.Shellcheck("PATH")
    patched = patches(
        "Shellcheck.parse_error_line",
        "Shellcheck._shellcheck_error_info",
        prefix="envoy.code.check.abstract.shellcheck")
    response = MagicMock()
    response.stdout.split.return_value = input

    def parse(line):
        if line.startswith("MATCH"):
            return line.split(" ")[1:]
        return "", None

    def info(fname=None):
        return fname, dict(lines=[], line_numbers=[])

    with patched as (m_parse, m_info):
        m_parse.side_effect = parse
        m_info.side_effect = info
        resultgen = shellcheck._shellcheck_errors(response)
        assert isinstance(resultgen, types.GeneratorType)
        result = list(resultgen)

    if not input or not any(input):
        assert not result
        return

    assert (
        result
        == [('FNAME1',
             {'lines': [
                 'MATCH FNAME1 23',
                 'DATA 0',
                 'DATA 1',
                 'DATA 2',
                 "",
                 'MATCH FNAME1 73',
                 'MORE DATA 0',
                 'MORE DATA 1',
                 'MORE DATA 2',
                 ""],
              'line_numbers': [
                  '23',
                  '73']}),
            ('FNAME2',
             {'lines': [
                 'MATCH FNAME2 23',
                 'MORE DATA 0',
                 'MORE DATA 1',
                 'MORE DATA 2',
                 ""],
              'line_numbers': ['23']})])


def test_shellcheck_checker_run_shellcheck(patches):
    patched = patches(
        "Shellcheck",
        prefix="envoy.code.check.abstract.shellcheck")
    path = MagicMock()
    args = [MagicMock() for x in range(0, 5)]

    with patched as (m_shellcheck, ):
        assert (
            check.AShellcheckCheck.run_shellcheck(path, *args)
            == m_shellcheck.return_value.return_value)

    assert (
        m_shellcheck.call_args
        == [(path, ), {}])
    assert (
        m_shellcheck.return_value.call_args
        == [tuple(args), {}])


def test_shellcheck_checker_constructor():
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
                check.AFileCodeCheck.problem_files.cache_name)[
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
            with pytest.raises(subprocess.exceptions.OSCommandError) as e:
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
