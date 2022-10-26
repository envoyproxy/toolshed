
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio.core import directory

from envoy.code import check


@pytest.mark.parametrize("args", [[], [f"ARG{i}" for i in range(0, 5)]])
def test_yamllint_yamllintfilescheck_constructor(args):
    yamllint_check = check.abstract.yamllint.YamllintFilesCheck(
        "PATH", "CONFIG", *args)
    assert isinstance(yamllint_check, directory.IDirectoryContext)
    assert isinstance(yamllint_check, directory.ADirectoryContext)
    assert yamllint_check.config == "CONFIG"
    assert yamllint_check.args == tuple(args)


def test_yamllint_yamllintfilescheck_check_results(iters, patches):
    args = iters()

    yamllint_check = check.abstract.yamllint.YamllintFilesCheck(
        "PATH", "CONFIG", *args)
    patched = patches(
        ("YamllintFilesCheck.in_directory",
         dict(new_callable=PropertyMock)),
        "YamllintFilesCheck.run_check",
        prefix="envoy.code.check.abstract.yamllint")
    result = MagicMock()

    def run_check(path):
        i = int(path[-1])
        if i % 2:
            return path

    with patched as (m_dir, m_run):
        m_run.side_effect = run_check
        genresult = yamllint_check.check_results
        result = list(genresult)

    assert (
        m_dir.return_value.__enter__.call_args
        == [(), {}])
    assert isinstance(genresult, types.GeneratorType)
    assert result == [x for x in args if int(x[-1]) % 2]
    assert "check_results" not in yamllint_check.__dict__


@pytest.mark.parametrize("has_problems", [True, False])
def test_yamllint_yamllintfilescheck_handle_result(patches, has_problems):
    yamllint_check = check.abstract.yamllint.YamllintFilesCheck(
        "PATH", "CONFIG")
    patched = patches(
        "checker",
        "YamllintFilesCheck._parse_problems",
        prefix="envoy.code.check.abstract.yamllint")
    path = MagicMock()
    result = MagicMock()
    problems = MagicMock()

    with patched as (m_checker, m_problems):
        m_problems.return_value = (
            problems
            if has_problems
            else None)
        assert (
            yamllint_check.handle_result(path, result)
            == ((path,  m_checker.Problems.return_value)
                if has_problems
                else None))

    assert (
        m_problems.call_args
        == [(path, result), {}])
    if not has_problems:
        assert not m_checker.Problems.called
        assert not problems.get.called
        return
    assert (
        m_checker.Problems.call_args
        == [(),
            dict(errors=problems.get.return_value,
                 warnings=problems.get.return_value)])
    assert (
        problems.get.call_args_list
        == [[("error", ), {}], [("warning", ), {}]])


def test_yamllint_yamllintfilescheck_run_check(patches):
    config = MagicMock()
    yamllint_check = check.abstract.yamllint.YamllintFilesCheck(
        "PATH", config)
    patched = patches(
        "io",
        "linter",
        "YamllintFilesCheck.handle_result",
        prefix="envoy.code.check.abstract.yamllint")
    path = MagicMock()

    with patched as (m_io, m_linter, m_handle):
        assert (
            yamllint_check.run_check(path)
            == m_handle.return_value)

    assert (
        m_io.open.call_args
        == [(path, ), dict(newline="")])
    assert (
        m_io.open.return_value.__enter__.call_args
        == [(), {}])
    assert (
        m_handle.call_args
        == [(path, m_linter.run.return_value), {}])
    assert (
        m_linter.run.call_args
        == [(m_io.open.return_value.__enter__.return_value,
             config, path), {}])


def test_yamllint_yamllintfilescheck_run_checks(patches):
    yamllint_check = check.abstract.yamllint.YamllintFilesCheck(
        "PATH", "CONFIG")
    patched = patches(
        "tuple",
        ("YamllintFilesCheck.check_results",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.yamllint")

    with patched as (m_tuple, m_results):
        assert (
            yamllint_check.run_checks()
            == m_tuple.return_value)

    assert (
        m_tuple.call_args
        == [(m_results.return_value, ), {}])


def test_yamllint_yamllintfilescheck__parse_problems(iters):
    yamllint_check = check.abstract.yamllint.YamllintFilesCheck(
        "PATH", "CONFIG")
    path = MagicMock()

    def problem(i):
        p = MagicMock()
        p.level = "L{i % 2}"
        return p

    problems = iters(cb=problem)
    expected = {}

    for p in problems:
        if not expected.get(p.level):
            expected[p.level] = []
        expected[p.level].append(
            f"{path} ({p.rule} {p.line}:{p.column}): {p.desc}")
    assert (
        yamllint_check._parse_problems(path, problems)
        == expected)


@pytest.mark.parametrize("fix", [None, True, False])
def test_yamllint_yamllint(iters, patches, fix):
    patched = patches(
        "YamllintFilesCheck",
        prefix="envoy.code.check.abstract.yamllint")
    root_path = MagicMock()
    config = MagicMock()
    args = iters(cb=lambda i: MagicMock())

    with patched as (m_yamllint, ):
        assert (
            check.AYamllintCheck.yamllint(
                root_path,
                config,
                *args)
            == m_yamllint.return_value.run_checks.return_value)

    assert (
        m_yamllint.call_args
        == [(root_path,
             config,
             *args), {}])
    assert (
        m_yamllint.return_value.run_checks.call_args
        == [(), {}])


def test_yamllint_constructor():
    yamllint = check.AYamllintCheck("DIRECTORY")
    assert yamllint.directory == "DIRECTORY"


@pytest.mark.parametrize("files", [True, False])
async def test_yamllint_checker_files(patches, files):
    directory = MagicMock()
    yamllint = check.AYamllintCheck(directory)
    patched = patches(
        "set",
        ("AYamllintCheck.path_match_exclude_re",
         dict(new_callable=PropertyMock)),
        ("AYamllintCheck.path_match_re",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.yamllint")
    files = AsyncMock(return_value=range(0, 20))
    directory.files = files()

    with patched as (m_set, m_exc_re, m_re):
        m_exc_re.return_value.match.side_effect = lambda x: x % 3
        m_re.return_value.match.side_effect = lambda x: x % 2
        assert (
            await yamllint.checker_files
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
            yamllint,
            check.AYamllintCheck.checker_files.cache_name))


def test_yamllint_checker_path_match_exclude_re(patches):
    yamllint = check.AYamllintCheck("DIRECTORY")
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.yamllint")

    with patched as (m_re, ):
        assert (
            yamllint.path_match_exclude_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [("|".join(check.abstract.yamllint.YAMLLINT_NOMATCH_RE), ),
            {}])
    assert "path_match_exclude_re" in yamllint.__dict__


def test_yamllint_checker_path_match_re(patches):
    yamllint = check.AYamllintCheck("DIRECTORY")
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.yamllint")

    with patched as (m_re, ):
        assert (
            yamllint.path_match_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [("|".join(check.abstract.yamllint.YAMLLINT_MATCH_RE), ),
            {}])
    assert "path_match_re" in yamllint.__dict__


def test_yamllint_config(patches):
    yamllint = check.AYamllintCheck("DIRECTORY")
    patched = patches(
        "YamlLintConfig",
        ("AYamllintCheck.config_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.yamllint")

    with patched as (m_config, m_config_path):
        assert yamllint.config == m_config.return_value

    assert (
        m_config.call_args
        == [(), dict(file=m_config_path.return_value)])

    assert "config" in yamllint.__dict__


def test_yamllint_config_path():
    directory = MagicMock()
    yamllint = check.AYamllintCheck(directory)
    assert (
        yamllint.config_path
        == directory.path.joinpath.return_value)
    assert (
        directory.path.joinpath.call_args
        == [(check.abstract.yamllint.YAMLLINT_CONFIG, ), {}])
    assert "config_path" not in yamllint.__dict__


@pytest.mark.parametrize("files", [True, False])
async def test_yamllint_problem_files(patches, files):
    yamllint = check.AYamllintCheck("DIRECTORY")
    patched = patches(
        "dict",
        ("AwaitableGenerator",
         dict(new_callable=AsyncMock)),
        ("AYamllintCheck._problem_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.yamllint")

    with patched as (m_dict, m_agen, m_problems):
        result = await yamllint.problem_files
        assert (
            result
            == m_dict.return_value
            == getattr(
                yamllint,
                check.AFileCodeCheck.problem_files.cache_name)[
                    "problem_files"])

    assert (
        m_dict.call_args
        == [(m_agen.return_value, ), {}])
    assert (
        m_agen.call_args
        == [(m_problems.return_value, ), {}])


@pytest.mark.parametrize("files", [True, False])
async def test_yamllint__problem_files(patches, files):
    directory = MagicMock()
    yamllint = check.AYamllintCheck(directory)
    patched = patches(
        "partial",
        "str",
        "AYamllintCheck.yamllint",
        ("AYamllintCheck.config",
         dict(new_callable=PropertyMock)),
        ("AYamllintCheck.files",
         dict(new_callable=PropertyMock)),
        "AYamllintCheck.execute_in_batches",
        prefix="envoy.code.check.abstract.yamllint")
    batched = [
        [f"PROB{x}" for x in range(0, 10)],
        [f"PROB{x}" for x in range(10, 20)],
        [f"PROB{x}" for x in range(20, 30)]]
    files = (
        [f"FILE{i}" for i in range(0, 5)]
        if files
        else [])
    expected = batched[0] + batched[1] + batched[2]
    results = []

    async def batch_iter(*x):
        for batch in batched:
            yield batch

    with patched as (m_partial, m_str, m_lint, m_conf, m_files, m_execute):
        m_files.side_effect = AsyncMock(return_value=files)
        m_execute.side_effect = batch_iter

        async for p in yamllint._problem_files:
            results.append(p)

        assert (
            results
            == ([]
                if not files
                else expected))

    assert not (
        hasattr(
            yamllint,
            check.AYamllintCheck._problem_files.cache_name))
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
        == [(m_lint,
             m_str.return_value,
             m_conf.return_value), {}])
    assert (
        m_str.call_args
        == [(directory.path, ), {}])
