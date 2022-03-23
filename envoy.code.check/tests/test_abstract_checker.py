
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio import run

from envoy.code import check


def test_checker_summary_constructor():
    checker = MagicMock()
    summary = check.abstract.checker.CodeCheckerSummary(checker)
    assert isinstance(
        summary,
        run.checker.CheckerSummary)


@pytest.mark.parametrize("glint_errors", [True, False])
def test_checker_summary_print_summary(patches, glint_errors):
    checker = MagicMock()
    summary = check.abstract.checker.CodeCheckerSummary(checker)
    patched = patches(
        "checker.CheckerSummary.print_summary",
        "CodeCheckerSummary.writer_for",
        prefix="envoy.code.check.abstract.checker")
    checker.errors.__contains__.return_value = glint_errors

    with patched as (m_super, m_writer):
        assert not summary.print_summary()

    assert (
        m_super.call_args
        == [(), {}])
    assert (
        checker.errors.__contains__.call_args
        == [("glint", ), {}])
    if glint_errors:
        assert (
            m_writer.call_args
            == [("error", ), {}])
        assert (
            m_writer.return_value.call_args
            == [(check.abstract.checker.GLINT_ADVICE, ), {}])
        return
    assert not m_writer.called


@abstracts.implementer(check.ACodeChecker)
class DummyCodeChecker:

    @property
    def fs_directory_class(self):
        return super().fs_directory_class

    @property
    def extensions_class(self):
        return super().extensions_class

    @property
    def flake8_class(self):
        return super().flake8_class

    @property
    def git_directory_class(self):
        return super().git_directory_class

    @property
    def glint_class(self):
        return super().glint_class

    @property
    def path(self):
        return super().path

    @property
    def shellcheck_class(self):
        return super().shellcheck_class

    @property
    def yapf_class(self):
        return super().yapf_class


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_abstract_checker_constructor(patches, args, kwargs):
    patched = patches(
        "checker.Checker.__init__",
        prefix="envoy.code.check.abstract.checker")
    iface_props = [
        "extensions_class", "fs_directory_class", "flake8_class",
        "git_directory_class", "glint_class",
        "shellcheck_class", "yapf_class"]

    with patched as (m_super, ):
        m_super.return_value = None
        with pytest.raises(TypeError):
            check.ACodeChecker(*args, **kwargs)
        checker = DummyCodeChecker(*args, **kwargs)

    assert isinstance(checker, run.checker.Checker)
    assert (
        checker.summary_class
        == check.abstract.checker.CodeCheckerSummary)
    assert "summary_class" not in checker.__dict__
    assert (
        m_super.call_args
        == [tuple(args), kwargs])
    assert (
        checker.checks
        == ("extensions_fuzzed", "extensions_metadata",
            "extensions_registered",
            "glint", "python_yapf", "python_flake8", "shellcheck"))
    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(checker, prop)


@pytest.mark.parametrize("all_files", [True, False])
def test_abstract_checker_grep_globs(patches, all_files):
    checker = DummyCodeChecker()
    patched = patches(
        "GREP_EXCLUDE_GLOBS",
        "GREP_EXCLUDE_DIR_GLOBS",
        ("ACodeChecker.all_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_globs, m_dir_globs, m_all):
        m_all.return_value = all_files
        assert (
            checker.exclude_from_grep
            == (m_globs if all_files else ()))
        assert (
            checker.exclude_dirs_from_grep
            == (m_dir_globs if all_files else ()))

    assert "exclude_from_grep" not in checker.__dict__
    assert "exclude_dirs_from_grep" not in checker.__dict__


@pytest.mark.parametrize(
    "subcheck",
    (("glint", "glint"),
     ("python_flake8", "flake8"),
     ("python_yapf", "yapf"),
     ("shellcheck", "shellcheck")))
async def test_abstract_checker_checks(patches, subcheck):
    checkname, tool = subcheck
    checker = DummyCodeChecker()
    patched = patches(
        (f"ACodeChecker.{tool}",
         dict(new_callable=PropertyMock)),
        "ACodeChecker._code_check",
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_tool, m_check):
        assert not await getattr(checker, f"check_{checkname}")()

    assert (
        m_check.call_args
        == [(m_tool.return_value, ), {}])


def test_abstract_checker_extensions(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.args",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.directory",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.check_kwargs",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.extensions_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 5)}

    with patched as (m_args, m_dir, m_kwargs, m_tool):
        m_kwargs.return_value = kwargs
        assert (
            checker.extensions
            == m_tool.return_value.return_value)

    kwargs["extensions_build_config"] = (
        m_args.return_value.extensions_build_config)
    assert (
        m_tool.return_value.call_args
        == [(m_dir.return_value,),
            kwargs])

    assert "extensions" in checker.__dict__


@pytest.mark.parametrize(
    "tool",
    (("glint",
      "flake8",
      "yapf",
      "shellcheck")))
def test_abstract_checker_tools(patches, tool):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.directory",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.check_kwargs",
         dict(new_callable=PropertyMock)),
        (f"ACodeChecker.{tool}_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 5)}

    with patched as (m_dir, m_kwargs, m_tool):
        m_kwargs.return_value = kwargs
        assert (
            getattr(checker, tool)
            == m_tool.return_value.return_value)

    assert (
        m_tool.return_value.call_args
        == [(m_dir.return_value, ), kwargs])
    assert tool in checker.__dict__


@pytest.mark.parametrize(
    "preloader",
    (("glint", "glint"),
     ("python_flake8", "flake8"),
     ("python_yapf", "yapf"),
     ("shellcheck", "shellcheck")))
async def test_abstract_checker_preloaders(patches, preloader):
    when, name = preloader
    checker = DummyCodeChecker()
    patched = patches(
        (f"ACodeChecker.{name}",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_tool, ):
        problem_files = AsyncMock()
        m_tool.return_value.problem_files = problem_files()
        assert not await getattr(checker, f"preload_{name}")()

    problem_files.assert_awaited()
    assert (
        getattr(check.ACodeChecker, f"preload_{name}").when
        == (when,))


def test_abstract_checker_all_files(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_args, ):
        assert (
            checker.all_files
            == m_args.return_value.all_files)

    assert "all_files" not in checker.__dict__


@pytest.mark.parametrize("build_config", [None, "BUILD CONFIG"])
def test_abstract_checker_disabled_checks(patches, build_config):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")
    disabled_dict = {
        k: check.abstract.checker.NO_EXTENSIONS_ERROR_MSG
        for k
        in ["extensions_fuzzed",
            "extensions_metadata",
            "extensions_registered"]}

    with patched as (m_args, ):
        m_args.return_value.extensions_build_config = build_config
        assert (
            checker.disabled_checks
            == ({}
                if build_config
                else disabled_dict))

    assert "disabled_checks" in checker.__dict__


def test_abstract_checker_changed_since(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_args, ):
        assert (
            checker.changed_since
            == m_args.return_value.since)

    assert "changed_since" not in checker.__dict__


def test_abstract_checker_check_kwargs(patches):
    checker = DummyCodeChecker()
    patched = patches(
        "dict",
        ("ACodeChecker.fix",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.loop",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.pool",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_dict, m_fix, m_loop, m_pool):
        assert (
            checker.check_kwargs
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(),
            dict(fix=m_fix.return_value,
                 loop=m_loop.return_value,
                 pool=m_pool.return_value)])
    assert "check_kwargs" not in checker.__dict__


def test_abstract_checker_directory(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.directory_class",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.directory_kwargs",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_class, m_kwargs, m_path):
        m_kwargs.return_value = dict(foo="BAR")
        assert (
            checker.directory
            == m_class.return_value.return_value)

    assert (
        m_class.return_value.call_args
        == [(m_path.return_value, ), dict(foo="BAR")])
    assert "directory" in checker.__dict__


@pytest.mark.parametrize("all_files", [True, False])
def test_abstract_checker_directory_class(patches, all_files):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.all_files",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.fs_directory_class",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.git_directory_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_all, m_class, m_git_class):
        m_all.return_value = all_files
        assert (
            checker.directory_class
            == (m_class.return_value
                if all_files
                else m_git_class.return_value))

    assert "directory_class" not in checker.__dict__


@pytest.mark.parametrize("all_files", [True, False])
def test_abstract_checker_directory_kwargs(patches, all_files):
    checker = DummyCodeChecker()
    patched = patches(
        "dict",
        ("ACodeChecker.all_files",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.changed_since",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.grep_excluding_re",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.grep_matching_re",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.exclude_from_grep",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.exclude_dirs_from_grep",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.loop",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.pool",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as patchy:
        (m_dict, m_all, m_changed, m_exc_re,
         m_match_re, m_exc, m_exc_dirs,
         m_loop, m_pool) = patchy
        m_all.return_value = all_files
        assert (
            checker.directory_kwargs
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(),
            dict(exclude_matcher=m_exc_re.return_value,
                 path_matcher=m_match_re.return_value,
                 exclude=m_exc.return_value,
                 exclude_dirs=m_exc_dirs.return_value,
                 loop=m_loop.return_value,
                 pool=m_pool.return_value)])
    if all_files:
        assert not m_dict.return_value.__setitem__.called
        assert not m_changed.called
    else:
        assert (
            m_dict.return_value.__setitem__.call_args
            == [("changed", m_changed.return_value), {}])
    assert "directory_kwargs" not in checker.__dict__


def test_abstract_checker_grep_excluding_re(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.args",
         dict(new_callable=PropertyMock)),
        "ACodeChecker._grep_re",
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_args, m_re):
        assert (
            checker.grep_excluding_re
            == m_re.return_value)

    assert (
        m_re.call_args
        == [(m_args.return_value.excluding, ), {}])
    assert "grep_excluding_re" not in checker.__dict__


def test_abstract_checker_grep_matching_re(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.args",
         dict(new_callable=PropertyMock)),
        "ACodeChecker._grep_re",
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_args, m_re):
        assert (
            checker.grep_matching_re
            == m_re.return_value)

    assert (
        m_re.call_args
        == [(m_args.return_value.matching, ), {}])
    assert "grep_matching_re" not in checker.__dict__


def test_abstract_checker_path(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("checker.Checker.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_super, ):
        assert (
            checker.path
            == m_super.return_value)

    assert "path" not in checker.__dict__


@pytest.mark.parametrize("fuzzed", [True, False])
async def test_abstract_checker_check_extensions_fuzzed(patches, fuzzed):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.extensions",
         dict(new_callable=PropertyMock)),
        "ACodeChecker.error",
        "ACodeChecker.succeed",
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_extensions, m_error, m_succeed):
        m_extensions.return_value.all_fuzzed = fuzzed
        assert not await checker.check_extensions_fuzzed()

    if fuzzed:
        assert (
            m_succeed.call_args
            == [("extensions_fuzzed",
                 ["All network filters are fuzzed"]), {}])
        assert not m_error.called
    else:
        assert (
            m_error.call_args
            == [("extensions_fuzzed",
                 ["Check that all network filters robust against untrusted "
                  "downstreams are fuzzed by adding them to filterNames() "
                  f"in {m_extensions.return_value.fuzz_test_path}"]),
                {}])
        assert not m_succeed.called


async def test_abstract_checker_check_extensions_metadata(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.extensions",
         dict(new_callable=PropertyMock)),
        "ACodeChecker.error",
        "ACodeChecker.succeed",
        prefix="envoy.code.check.abstract.checker")
    errors = {}
    for k in range(0, 10):
        errors[f"K{k}"] = (
            [f"E{k}.{i}" for i in range(0, 7)]
            if k % 2
            else [])

    with patched as (m_extensions, m_error, m_succeed):
        m_extensions.return_value.metadata_errors = errors
        assert not await checker.check_extensions_metadata()

    assert (
        m_error.call_args_list
        == [[("extensions_metadata", v)]
            for k, v in errors.items()
            if (int(k[1:]) % 2)])
    assert (
        m_succeed.call_args_list
        == [[("extensions_metadata", [k])]
            for k in errors
            if not (int(k[1:]) % 2)])


@pytest.mark.parametrize(
    "errors",
    [[],
     [f"E{i}" for i in range(0, 5)]])
async def test_abstract_checker_check_extensions_registered(patches, errors):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.extensions",
         dict(new_callable=PropertyMock)),
        "ACodeChecker.error",
        "ACodeChecker.succeed",
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_extensions, m_error, m_succeed):
        m_extensions.return_value.registration_errors = errors
        assert not await checker.check_extensions_registered()

    if errors:
        assert (
            m_error.call_args
            == [("extensions_registered", errors), {}])
        assert not m_succeed.called
    else:
        assert (
            m_succeed.call_args
            == [("extensions_registered",
                 ["Registered metadata matches found extensions"]), {}])
        assert not m_error.called


@pytest.mark.parametrize(
    "files",
    [[],
     [f"F{i}" for i in range(0, 5)],
     [f"F{i}" for i in range(5, 10)],
     [f"F{i}" for i in range(0, 10)]])
@pytest.mark.parametrize(
    "problem_files",
    [{},
     {f"F{i}": f"P{i}" for i in range(0, 5)},
     {f"F{i}": f"P{i}" for i in range(5, 10)},
     {f"F{i}": f"P{i}" for i in range(0, 10)}])
def test_abstract_checker__check_output(patches, files, problem_files):
    checker = DummyCodeChecker()
    patched = patches(
        "sorted",
        ("ACodeChecker.active_check",
         dict(new_callable=PropertyMock)),
        "ACodeChecker.error",
        "ACodeChecker.succeed",
        prefix="envoy.code.check.abstract.checker")
    check_files = MagicMock()
    errors = []
    success = []
    for f in files:
        if f in problem_files:
            errors.append(f)
        else:
            success.append(f)

    with patched as (m_sorted, m_active, m_error, m_succeed):
        m_sorted.return_value = files
        assert not checker._check_output(
            check_files, problem_files)

    assert (
        m_sorted.call_args
        == [(check_files, ), {}])
    assert (
        m_error.call_args_list
        == [[(m_active.return_value, problem_files[error]), {}]
            for error in errors])
    assert (
        m_succeed.call_args_list
        == [[(m_active.return_value, [succeed]), {}]
            for succeed in success])


async def test_abstract_checker__code_check(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.loop",
         dict(new_callable=PropertyMock)),
        "ACodeChecker._check_output",
        prefix="envoy.code.check.abstract.checker")
    check = MagicMock()
    files_mock = AsyncMock()
    check.files = files_mock()
    problems_mock = AsyncMock()
    check.problem_files = problems_mock()

    with patched as (m_loop, m_check):
        execute = AsyncMock()
        m_loop.return_value.run_in_executor = execute
        assert not await checker._code_check(check)

    assert (
        execute.call_args
        == [(None,
             m_check,
             files_mock.return_value,
             problems_mock.return_value), {}])


@pytest.mark.parametrize("arg", [None, False, (), ["A1"], ["A1", "A2"]])
def test_abstract_checker__grep_re(patches, arg):
    checker = DummyCodeChecker()
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_re, ):
        assert (
            checker._grep_re(arg)
            == (m_re.compile.return_value
                if arg
                else None))

    if not arg:
        assert not m_re.compile.called
    else:
        assert (
            m_re.compile.call_args
            == [("|".join(arg), ), {}])
