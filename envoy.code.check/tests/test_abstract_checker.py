
import types
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
    def changelog_class(self):
        return super().changelog_class

    @property
    def extensions_class(self):
        return super().extensions_class

    @property
    def flake8_class(self):
        return super().flake8_class

    @property
    def fs_directory_class(self):
        return super().fs_directory_class

    @property
    def git_directory_class(self):
        return super().git_directory_class

    @property
    def glint_class(self):
        return super().glint_class

    @property
    def gofmt_class(self):
        return super().gofmt_class

    @property
    def path(self):
        return super().path

    @property
    def project_class(self):
        return super().project_class

    @property
    def runtime_guards_class(self):
        return super().runtime_guards_class

    @property
    def shellcheck_class(self):
        return super().shellcheck_class

    @property
    def yamllint_class(self):
        return super().yamllint_class

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
        "git_directory_class", "glint_class", "gofmt_class", "project_class",
        "runtime_guards_class", "shellcheck_class", "yapf_class",
        "changelog_class", "yamllint_class"]

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
        == ("changelog",
            "extensions_fuzzed", "extensions_metadata",
            "extensions_registered",
            "glint", "gofmt", "python_yapf", "python_flake8",
            "runtime_guards", "shellcheck", "yamllint"))
    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(checker, prop)


@pytest.mark.parametrize(
    "subcheck",
    (("glint", "glint"),
     ("gofmt", "gofmt"),
     ("python_flake8", "flake8"),
     ("python_yapf", "yapf"),
     ("shellcheck", "shellcheck"),
     ("yamllint", "yamllint")))
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


def test_abstract_checker_extensions(iters, patches):
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
    kwargs = iters(dict)

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
      "gofmt",
      "flake8",
      "yapf",
      "shellcheck",
      "yamllint")))
def test_abstract_checker_tools(iters, patches, tool):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.directory",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.check_kwargs",
         dict(new_callable=PropertyMock)),
        (f"ACodeChecker.{tool}_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")
    kwargs = iters(dict)

    with patched as (m_dir, m_kwargs, m_tool):
        m_kwargs.return_value = kwargs
        assert (
            getattr(checker, tool)
            == m_tool.return_value.return_value)

    assert (
        m_tool.return_value.call_args
        == [(m_dir.return_value, ), kwargs])
    assert tool in checker.__dict__


async def test_abstract_checker_preload_changelog(patches):
    checker = DummyCodeChecker()
    patched = patches(
        "inflate",
        ("ACodeChecker.changelog",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")
    clogs = []

    for x in range(0, 5):
        clog = MagicMock()
        clog.version = x
        clogs.append(clog)

    async def inflate(thing, fun):
        for clog in clogs:
            yield clog

    with patched as (m_inflate, m_clog, m_log):
        m_inflate.side_effect = inflate
        assert not await checker.preload_changelog()

    inflater = m_inflate.call_args[0][1]
    assert (
        m_inflate.call_args
        == [(m_clog.return_value,
             inflater), {}])
    assert (
        m_log.return_value.debug.call_args_list
        == [[(f"Preloaded changelog: {clog.version}", ), {}]
            for clog in clogs])
    thing = MagicMock()
    assert (
        inflater(thing)
        == (thing.errors, ))
    assert (
        check.ACodeChecker.preload_changelog.when
        == ("changelog", ))


async def test_abstract_checker_preload_extensions(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.extensions",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_extensions, m_log):
        metadata = AsyncMock()
        metadata.return_value.__len__.return_value = 23
        m_extensions.return_value.metadata = metadata()
        assert not await checker.preload_extensions()

    assert (
        check.ACodeChecker.preload_extensions.when
        == ("extensions_fuzzed",
            "extensions_metadata",
            "extensions_registered", ))
    assert (
        m_log.return_value.debug.call_args
        == [("Preloaded extensions (23)", ), {}])


async def test_abstract_checker_preload_runtime_guards(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.runtime_guards",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_guards, ):
        missing = AsyncMock()
        m_guards.return_value.missing = missing()
        assert not await checker.preload_runtime_guards()

    assert missing.called
    assert (
        check.ACodeChecker.preload_runtime_guards.when
        == ("runtime_guards", ))


@pytest.mark.parametrize(
    "preloader",
    (("glint", "glint"),
     ("gofmt", "gofmt"),
     ("python_flake8", "flake8"),
     ("python_yapf", "yapf"),
     ("shellcheck", "shellcheck"),
     ("yamllint", "yamllint")))
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


@pytest.mark.parametrize("bins", [True, False])
def test_abstract_checker_binaries(iters, patches, bins):
    checker = DummyCodeChecker()
    patched = patches(
        "dict",
        ("ACodeChecker.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")
    binaries = iters(cb=lambda i: f"K{i}:V{i}")

    with patched as (m_dict, m_args):
        m_args.return_value.binary = (binaries if bins else None)
        assert (
            checker.binaries
            == m_dict.return_value)
        resultgen = m_dict.call_args[0][0]
        resultlist = list(resultgen)

    assert isinstance(resultgen, types.GeneratorType)
    assert (
        m_dict.call_args
        == [(resultgen, ), {}])
    assert (
        resultlist
        == [bin.split(":") for bin in (binaries if bins else [])])
    assert "binaries" in checker.__dict__


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


def test_abstract_checker_changelog(iters, patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.changelog_class",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.check_kwargs",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.project",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")
    kwargs = iters(dict)

    with patched as (m_class, m_kwa, m_project):
        m_kwa.return_value = kwargs
        assert (
            checker.changelog
            == m_class.return_value.return_value)

    assert (
        m_class.return_value.call_args
        == [(m_project.return_value, ), kwargs])
    assert "changelog" in checker.__dict__


def test_abstract_checker_check_kwargs(patches):
    checker = DummyCodeChecker()
    patched = patches(
        "dict",
        ("ACodeChecker.binaries",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.fix",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.loop",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.pool",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_dict, m_bin, m_fix, m_loop, m_pool):
        assert (
            checker.check_kwargs
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(),
            dict(binaries=m_bin.return_value,
                 fix=m_fix.return_value,
                 loop=m_loop.return_value,
                 pool=m_pool.return_value)])
    assert "check_kwargs" in checker.__dict__


def test_abstract_checker_directory(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.directory_kwargs",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.project",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_kwargs, m_project):
        m_kwargs.return_value = dict(foo="BAR")
        assert (
            checker.directory
            == m_project.return_value.directory.filtered.return_value)

    assert (
        m_project.return_value.directory.filtered.call_args
        == [(), dict(foo="BAR")])
    assert "directory" in checker.__dict__


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
        prefix="envoy.code.check.abstract.checker")

    with patched as patchy:
        (m_dict, m_all, m_changed, m_exc_re,
         m_match_re) = patchy
        m_all.return_value = all_files
        assert (
            checker.directory_kwargs
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(),
            dict(exclude_matcher=m_exc_re.return_value,
                 path_matcher=m_match_re.return_value,
                 untracked=all_files)])
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


def test_abstract_checker_project(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.path",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.project_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")

    with patched as (m_path, m_class):
        assert (
            checker.project
            == m_class.return_value.return_value)

    assert (
        m_class.return_value.call_args
        == [(m_path.return_value, ), {}])
    assert "project" in checker.__dict__


def test_abstract_checker_runtime_guards(iters, patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.check_kwargs",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.project",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.runtime_guards_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.checker")
    kwargs = iters(dict)

    with patched as (m_kwargs, m_project, m_class):
        m_kwargs.return_value = kwargs
        assert (
            checker.runtime_guards
            == m_class.return_value.return_value)

    assert (
        m_class.return_value.call_args
        == [(m_project.return_value, ), kwargs])
    assert "runtime_guards" in checker.__dict__


async def test_abstract_checker_check_changelogs(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.changelog",
         dict(new_callable=PropertyMock)),
        "ACodeChecker.error",
        "ACodeChecker.succeed",
        prefix="envoy.code.check.abstract.checker")

    clogs = []
    for i in range(0, 10):
        clog = MagicMock()
        clog._errors = AsyncMock(
            return_value=(
                []
                if i % 2
                else [f"ERROR{i}"]))
        clog.errors = clog._errors()
        clogs.append(clog)

    def iter_clogs():
        for clog in clogs:
            yield clog

    with patched as (m_clog, m_error, m_succeed):
        m_clog.return_value.__iter__.side_effect = iter_clogs
        assert not await checker.check_changelog()

    assert (
        m_succeed.call_args_list
        == [[("changelog", [f"{c.version}"]), {}]
            for i, c
            in enumerate(clogs)
            if i % 2])
    assert (
        m_error.call_args_list
        == [[("changelog", c._errors.return_value), {}]
            for i, c
            in enumerate(clogs)
            if not i % 2])


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
        m_extensions.return_value.all_fuzzed = AsyncMock(
            return_value=fuzzed)()
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


async def test_abstract_checker_check_extensions_metadata(iters, patches):
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
            iters(cb=lambda i: f"E{k}.{i}", count=7)
            if k % 2
            else [])

    with patched as (m_extensions, m_error, m_succeed):
        m_extensions.return_value.metadata_errors = AsyncMock(
            return_value=errors)()
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
        m_extensions.return_value.registration_errors = AsyncMock(
            return_value=errors)()
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


async def test_abstract_checker_check_runtime_guards(patches):
    checker = DummyCodeChecker()
    patched = patches(
        ("ACodeChecker.log",
         dict(new_callable=PropertyMock)),
        ("ACodeChecker.runtime_guards",
         dict(new_callable=PropertyMock)),
        "ACodeChecker.error",
        "ACodeChecker.succeed",
        prefix="envoy.code.check.abstract.checker")
    _status = [None, 0, "", "XX", {}, "YY", None, "ZZ"]

    async def status():
        for i, stat in enumerate(_status):
            yield f"GUARD{i}", stat

    with patched as (m_log, m_guards, m_error, m_succeed):
        m_guards.return_value.status = status()
        assert not await checker.check_runtime_guards()

    assert (
        m_log.return_value.info.call_args_list
        == [[(f"Ignoring runtime guard: GUARD{i}", ), {}]
            for i, status
            in enumerate(_status)
            if status is None])
    assert (
        m_error.call_args_list
        == [[("runtime_guards", [f"Missing from changelogs: GUARD{i}"]), {}]
            for i, status
            in enumerate(_status)
            if status is not None and not status])
    assert (
        m_succeed.call_args_list
        == [[("runtime_guards", [f"In changelogs: GUARD{i}"]), {}]
            for i, status
            in enumerate(_status)
            if status])


@pytest.mark.parametrize(
    "files",
    [[],
     [f"F{i}" for i in range(0, 5)],
     [f"F{i}" for i in range(5, 10)],
     [f"F{i}" for i in range(0, 10)]])
@pytest.mark.parametrize(
    "error_files",
    [{},
     {f"F{i}": f"P{i}" for i in range(0, 5)},
     {f"F{i}": f"P{i}" for i in range(5, 10)},
     {f"F{i}": f"P{i}" for i in range(0, 10)}])
@pytest.mark.parametrize(
    "warning_files",
    [{},
     {f"F{i}": f"P{i}" for i in range(0, 5)},
     {f"F{i}": f"P{i}" for i in range(5, 10)},
     {f"F{i}": f"P{i}" for i in range(0, 10)}])
def test_abstract_checker__check_output(
        patches, files, error_files, warning_files):
    checker = DummyCodeChecker()
    patched = patches(
        "sorted",
        ("ACodeChecker.active_check",
         dict(new_callable=PropertyMock)),
        "ACodeChecker.error",
        "ACodeChecker.succeed",
        "ACodeChecker.warn",
        prefix="envoy.code.check.abstract.checker")
    check_files = MagicMock()
    errors = []
    warnings = []
    success = []
    problems = {}
    for f in files:
        problems[f] = MagicMock()
        if f in error_files:
            errors.append(f)
            problems[f].errors = []
            problems[f].warnings = None
        elif f in warning_files:
            warnings.append(f)
            problems[f].warnings = []
            problems[f].errors = None
        else:
            del problems[f]
            success.append(f)

    for f in error_files:
        if f not in files:
            continue
        problems[f].errors.append(error_files[f])

    for f in warning_files:
        if f not in files or f in error_files:
            continue
        problems[f].warnings.append(warning_files[f])

    with patched as (m_sorted, m_active, m_error, m_succeed, m_warning):
        m_sorted.return_value = files
        assert not checker._check_output(
            check_files, problems)

    assert (
        m_sorted.call_args
        == [(check_files, ), {}])
    assert (
        m_error.call_args_list
        == [[(m_active.return_value, [error_files[error]]), {}]
            for error in errors])
    assert (
        m_warning.call_args_list
        == [[(m_active.return_value, [warning_files[warning]]), {}]
            for warning in warnings])
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
