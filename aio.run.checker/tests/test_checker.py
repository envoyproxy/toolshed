import logging
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from aio.run.checker import (
    Checker, CheckerSummary)
from aio.run.runner import Runner


class DummyChecker(Checker):

    def __init__(self):
        self.args = PropertyMock()


class DummyCheckerWithChecks(Checker):
    checks = ("check1", "check2")

    def __init__(self, *args):
        self.check1 = MagicMock()
        self.check2 = MagicMock()

    def check_check1(self):
        pass

    def check_check2(self):
        pass


class SomeError(BaseException):
    pass


class OtherError(BaseException):
    pass


def test_checker_constructor(patches):
    patched = patches(
        "getattr",
        ("runner.Runner.__init__", dict(new_callable=MagicMock)),
        prefix="aio.run.checker.checker")

    with patched as (m_get, m_super):
        m_super.return_value = None
        checker = Checker("path1", "path2", "path3")

    assert isinstance(checker, Runner)

    assert (
        m_super.call_args
        == [('path1', 'path2', 'path3'), {}])
    assert checker.summary_class == CheckerSummary
    assert checker.active_check == ""
    assert "active_check" not in checker.__dict__
    assert checker.disabled_checks == {}
    assert "disabled_checks" in checker.__dict__
    assert checker.preload_pending_tasks == set()
    assert "preload_pending_tasks" in checker.__dict__
    assert checker.preloaded_checks == set()
    assert "preloaded_checks" in checker.__dict__
    assert checker.removed_checks == set()
    assert "removed_checks" in checker.__dict__
    assert checker.completed_checks == set()
    assert "completed_checks" in checker.__dict__


def test_checker_checks_to_run(patches):
    checker = Checker("path1", "path2", "path3")
    patched = patches(
        "Checker.get_checks",
        prefix="aio.run.checker.checker")

    with patched as (m_checks, ):
        assert checker.checks_to_run == m_checks.return_value

    assert "checks_to_run" in checker.__dict__


def test_checker_diff():
    checker = Checker("path1", "path2", "path3")
    args_mock = patch(
        "aio.run.checker.checker.Checker.args",
        new_callable=PropertyMock)

    with args_mock as m_args:
        assert checker.diff == m_args.return_value.diff
    assert "diff" not in checker.__dict__


def test_checker_error_count():
    checker = Checker("path1", "path2", "path3")
    checker.errors = dict(foo=["err"] * 3, bar=["err"] * 5, baz=["err"] * 7)
    assert checker.error_count == 15
    assert "error_count" not in checker.__dict__


@pytest.mark.parametrize(
    "errors",
    [{}, dict(exiting="EEK"), dict(notexiting="OK")])
def test_checker_exiting(errors):
    checker = Checker("path1", "path2", "path3")
    checker.errors = errors
    assert checker.exiting == bool("exiting" in errors)
    assert "exiting" not in checker.__dict__


@pytest.mark.parametrize("warning", [True, False, "cabbage", "error"])
def test_checker_fail_on_warn(patches, warning):
    checker = Checker("path1", "path2", "path3")
    patched = patches(
        ("Checker.args", dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    with patched as (m_args, ):
        m_args.return_value.warning = warning
        assert (
            checker.fail_on_warn
            == (warning == "error"))
    assert "fail_on_warn" not in checker.__dict__


def test_checker_failed():
    checker = Checker("path1", "path2", "path3")
    checker.errors = dict(foo=["err"] * 3, bar=["err"] * 5, baz=["err"] * 7)
    assert checker.failed == {'foo': 3, 'bar': 5, 'baz': 7}
    assert "failed" not in checker.__dict__


def test_checker_fix():
    checker = Checker("path1", "path2", "path3")
    args_mock = patch(
        "aio.run.checker.checker.Checker.args",
        new_callable=PropertyMock)

    with args_mock as m_args:
        assert checker.fix == m_args.return_value.fix
    assert "fix" not in checker.__dict__


@pytest.mark.parametrize("failed", [True, False])
@pytest.mark.parametrize("warned", [True, False])
@pytest.mark.parametrize("fail_on_warn", [True, False])
def test_checker_has_failed(patches, failed, warned, fail_on_warn):
    checker = Checker("path1", "path2", "path3")
    patched = patches(
        ("Checker.fail_on_warn", dict(new_callable=PropertyMock)),
        ("Checker.failed", dict(new_callable=PropertyMock)),
        ("Checker.warned", dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    with patched as (m_fail_warn, m_failed, m_warned):
        m_fail_warn.return_value = fail_on_warn
        m_failed.return_value = failed
        m_warned.return_value = warned
        result = checker.has_failed

    if failed or (warned and fail_on_warn):
        assert result is True
    else:
        assert result is False
    assert "has_failed" not in checker.__dict__


@pytest.mark.parametrize("path", [None, "PATH"])
@pytest.mark.parametrize("paths", [[], ["PATH0"]])
@pytest.mark.parametrize("isdir", [True, False])
def test_checker_path(patches, path, paths, isdir):
    class DummyError(Exception):
        pass
    checker = Checker("path1", "path2", "path3")
    patched = patches(
        "pathlib",
        ("Checker.args", dict(new_callable=PropertyMock)),
        ("Checker.parser", dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    with patched as (m_plib, m_args, m_parser):
        m_parser.return_value.error = DummyError
        m_args.return_value.path = path
        m_args.return_value.paths = paths
        m_plib.Path.return_value.is_dir.return_value = isdir
        if not path and not paths:
            with pytest.raises(DummyError) as e:
                checker.path
            assert (
                e.value.args
                == ("Missing path: `path` must be set either as an arg or "
                    "with --path",))
        elif not isdir:
            with pytest.raises(DummyError) as e:
                checker.path
            assert (
                e.value.args
                == ("Incorrect path: `path` must be a directory, set either "
                    "as first arg or with --path",))
        else:
            assert checker.path == m_plib.Path.return_value
            assert (
                m_plib.Path.call_args
                == [(path or paths[0],), {}])
            assert "path" in checker.__dict__
    if path or paths:
        assert (
            m_plib.Path.return_value.is_dir.call_args
            == [(), {}])


@pytest.mark.parametrize("paths", [[], ["path1", "path2"]])
def test_checker_paths(patches, paths):
    checker = Checker("path1", "path2", "path3")
    patched = patches(
        ("Checker.args", dict(new_callable=PropertyMock)),
        ("Checker.path", dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    with patched as (m_args, m_path):
        m_args.return_value.paths = paths
        result = checker.paths

    if paths:
        assert result == paths
    else:
        assert result == [m_path.return_value]
    assert "paths" not in checker.__dict__


@pytest.mark.parametrize("summary", [True, False])
@pytest.mark.parametrize("error_count", [0, 1])
@pytest.mark.parametrize("warning_count", [0, 1])
@pytest.mark.parametrize("exiting", [True, False])
def test_checker_show_summary(
        patches, summary, error_count, warning_count, exiting):
    checker = Checker("path1", "path2", "path3")
    patched = patches(
        ("Checker.args", dict(new_callable=PropertyMock)),
        ("Checker.exiting", dict(new_callable=PropertyMock)),
        ("Checker.error_count", dict(new_callable=PropertyMock)),
        ("Checker.warning_count", dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    with patched as (m_args, m_exit, m_errors, m_warnings):
        m_args.return_value.summary = summary
        m_errors.return_value = error_count
        m_warnings.return_value = warning_count
        m_exit.return_value = exiting
        result = checker.show_summary

    if exiting:
        assert result is False
    elif summary or error_count or warning_count:
        assert result is True
    else:
        assert result is False
    assert "show_summary" not in checker.__dict__


def test_checker_status(patches):
    checker = Checker("path1", "path2", "path3")
    patched = patches(
        ("Checker.success_count", dict(new_callable=PropertyMock)),
        ("Checker.error_count", dict(new_callable=PropertyMock)),
        ("Checker.warning_count", dict(new_callable=PropertyMock)),
        ("Checker.failed", dict(new_callable=PropertyMock)),
        ("Checker.warned", dict(new_callable=PropertyMock)),
        ("Checker.succeeded", dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    with patched as args:
        (m_success_count, m_error_count, m_warning_count,
         m_failed, m_warned, m_succeeded) = args
        assert (
            checker.status
            == dict(
                success=m_success_count.return_value,
                errors=m_error_count.return_value,
                warnings=m_warning_count.return_value,
                failed=m_failed.return_value,
                warned=m_warned.return_value,
                succeeded=m_succeeded.return_value))
    assert "status" not in checker.__dict__


def test_checker_succeeded():
    checker = Checker("path1", "path2", "path3")
    checker.success = dict(
        foo=["check"] * 3,
        bar=["check"] * 5,
        baz=["check"] * 7)
    assert (
        checker.succeeded
        == dict(foo=3, bar=5, baz=7))
    assert "succeeded" not in checker.__dict__


def test_checker_success_count():
    checker = Checker("path1", "path2", "path3")
    checker.success = dict(foo=["err"] * 3, bar=["err"] * 5, baz=["err"] * 7)
    assert checker.success_count == 15
    assert "success_count" not in checker.__dict__


def test_checker_summary():
    checker = Checker("path1", "path2", "path3")
    summary_mock = patch(
        "aio.run.checker.checker.Checker.summary_class",
        new_callable=PropertyMock)

    with summary_mock as m_summary:
        assert checker.summary == m_summary.return_value.return_value

    assert (
        m_summary.return_value.call_args
        == [(checker,), {}])
    assert "summary" in checker.__dict__


def test_checker_warned():
    checker = Checker("path1", "path2", "path3")
    checker.warnings = dict(
        foo=["check"] * 3,
        bar=["check"] * 5,
        baz=["check"] * 7)
    assert (
        checker.warned
        == dict(foo=3, bar=5, baz=7))
    assert "warned" not in checker.__dict__


def test_checker_warning_count():
    checker = Checker("path1", "path2", "path3")
    checker.warnings = dict(
        foo=["warn"] * 3,
        bar=["warn"] * 5,
        baz=["warn"] * 7)
    assert checker.warning_count == 15
    assert "warning_count" not in checker.__dict__


def test_checker_add_arguments(patches):
    checker = DummyCheckerWithChecks("path1", "path2", "path3")
    parser = MagicMock()
    patched = patches(
        "runner.Runner.add_arguments",
        prefix="aio.run.checker.checker")

    with patched as (m_super, ):
        assert checker.add_arguments(parser) is None

    assert (
        m_super.call_args
        == [(parser,), {}])

    assert (
        parser.add_argument.call_args_list
        == [[('--fix',),
             {'action': 'store_true',
              'default': False,
              'help': 'Attempt to fix in place'}],
            [('--diff',),
             {'action': 'store_true',
              'default': False,
              'help': 'Display a diff in the console where available'}],
            [('--warning', '-w'),
             {'choices': ['warn', 'error'],
              'default': 'warn',
              'help': 'Handle warnings as warnings or errors'}],
            [('--summary',),
             {'action': 'store_true',
              'default': False,
              'help': 'Show a summary of check runs'}],
            [('--summary-errors',),
             {'type': int,
              'default': 5,
              'help': (
                  'Number of errors to show in the summary, -1 shows all')}],
            [('--summary-warnings',),
             {'type': int,
              'default': 5,
              'help': (
                  "Number of warnings to show in the summary, -1 shows all")}],
            [('--check', '-c'),
             {'choices': ("check1", "check2"),
              'nargs': '*',
              'help': (
                  "Specify which checks to run, can be specified for multiple "
                  "checks")}],
            [('--config-check1',),
             {'default': '',
              'help': 'Custom configuration for the check1 check'}],
            [('--config-check2',),
             {'default': '',
              'help': 'Custom configuration for the check2 check'}],
            [('--path', '-p'),
             {'default': None,
              'help': (
                  "Path to the test root (usually Envoy source dir). If not "
                  "specified the first path of paths is used")}],
            [('paths',),
             {'nargs': '*',
              'help': (
                  "Paths to check. At least one path must be specified, or "
                  "the `path` argument should be provided")}]])


TEST_ERRORS: tuple = (
    {},
    dict(myerror=[]),
    dict(myerror=["a", "b", "c"]),
    dict(othererror=["other1", "other2", "other3"]),
    dict(othererror=["other1", "other2", "other3"], myerror=["a", "b", "c"]))


@pytest.mark.parametrize("log", [True, False])
@pytest.mark.parametrize("log_type", [None, "fatal"])
@pytest.mark.parametrize("errors", TEST_ERRORS)
@pytest.mark.parametrize("newerrors", [[], ["err1", "err2", "err3"]])
def test_checker_error(log, log_type, errors, newerrors):
    checker = Checker("path1", "path2", "path3")
    log_mock = patch(
        "aio.run.checker.checker.Checker.log",
        new_callable=PropertyMock)
    checker.errors = errors.copy()
    result = 1 if newerrors else 0

    with log_mock as m_log:
        if log_type:
            assert (
                checker.error("mycheck", newerrors, log, log_type=log_type)
                == result)
        else:
            assert checker.error("mycheck", newerrors, log) == result

    if not newerrors:
        assert not m_log.called
        assert "mycheck" not in checker.errors
        return

    assert checker.errors["mycheck"] == errors.get("mycheck", []) + newerrors
    for k, v in errors.items():
        if k != "mycheck":
            assert checker.errors[k] == v
    if log:
        assert (
            getattr(
                m_log.return_value,
                log_type or "error").call_args_list
            == [[(f'[mycheck] err{i}',), {}] for i in range(1, 4)])
    else:
        assert not getattr(m_log.return_value, log_type or "error").called


def test_checker_exit(patches):
    checker = Checker("path1", "path2", "path3")
    patched = patches(
        "Checker.error",
        ("Checker.root_logger", dict(new_callable=PropertyMock)),
        ("Checker.stdout", dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    with patched as (m_error, m_log, m_stdout):
        assert checker.exit() == m_error.return_value

    stdout = m_stdout.return_value.handlers.__getitem__
    log = m_log.return_value.handlers.__getitem__
    assert (
        log.call_args
        == [(0,), {}])
    assert (
        log.return_value.setLevel.call_args
        == [(logging.FATAL,), {}])
    assert (
        stdout.call_args
        == [(0,), {}])
    assert (
        stdout.return_value.setLevel.call_args
        == [(logging.FATAL,), {}])
    assert (
        m_error.call_args
        == [('exiting', ['Keyboard exit']), {'log_type': 'fatal'}])


@pytest.mark.parametrize(
    "checks",
    (None,
     (),
     ("check1", ),
     ("check1", "check2", "check3"),
     ("check3", "check4", "check5"),
     ("check4", "check5")))
@pytest.mark.parametrize(
    "disabled_checks",
    [{},
     dict(foo=23, bar=73),
     dict(check2="CHECK2 REASON"),
     {f"check{i}": f"CHECK{i} REASON" for i in range(0, 5)}])
def test_checker_get_checks(patches, checks, disabled_checks):
    checker = Checker("path1", "path2", "path3")
    checker.checks = ("check1", "check2", "check3")
    patched = patches(
        ("Checker.args",
         dict(new_callable=PropertyMock)),
        ("Checker.disabled_checks",
         dict(new_callable=PropertyMock)),
        ("Checker.log",
         dict(new_callable=PropertyMock)),
        "Checker.error",
        prefix="aio.run.checker.checker")
    expected = list(checker.checks)
    if checks:
        expected = [c for c in expected if c in checks]
    requested = expected
    if disabled_checks:
        expected = [c for c in expected if c not in disabled_checks]
    filtered = [c for c in requested if c not in expected]

    with patched as (m_args, m_disabled, m_log, m_error):
        m_args.return_value.check = checks
        m_disabled.return_value = disabled_checks
        assert checker.get_checks() == expected

    if not filtered:
        assert not m_log.called
        assert not m_error.called
        return
    if checks:
        assert not m_log.called
        assert (
            m_error.call_args_list
            == [[(check,
                  [f"Cannot run disabled check ({check}): "
                   f"{disabled_checks[check]}"]), {}]
                for check in filtered])
        return
    assert not m_error.called
    assert (
        m_log.return_value.notice.call_args_list
        == [[(f"Cannot run disabled check ({check}): "
              f"{disabled_checks[check]}", ), {}]
            for check in filtered])


def test_checker_install_reactor(patches):
    checker = Checker()
    patched = patches(
        "asyncio",
        "runner.Runner.install_reactor",
        "Checker.on_async_error",
        prefix="aio.run.checker.checker")

    with patched as (m_async, m_reactor, m_onerror):
        assert not checker.install_reactor()

    assert (
        m_reactor.call_args
        == [(), {}])
    assert (
        m_async.get_event_loop.call_args
        == [(), {}])
    assert (
        m_async.get_event_loop.return_value.set_exception_handler.call_args
        == [(m_onerror, ), {}])


async def test_checker_on_check_begin(patches):
    checker = Checker()
    patched = patches(
        ("Checker.log", dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    with patched as (m_log, ):
        assert not await checker.on_check_begin("CHECKNAME")

    assert checker.active_check == "CHECKNAME"
    assert (
        m_log.return_value.notice.call_args
        == [('[CHECKNAME] Running check...',), {}])


@pytest.mark.parametrize(
    "errors", [[], ["CHECK1", "CHECK2", "CHECK3"], ["CHECK2", "CHECK3"]])
@pytest.mark.parametrize(
    "warnings", [[], ["CHECK1", "CHECK2", "CHECK3"], ["CHECK2", "CHECK3"]])
@pytest.mark.parametrize(
    "success",
    [{},
     {f"CHECK{i}": [f"V1{i}"] for i in range(1, 3)},
     {f"CHECK{i}": [f"V1{i}", f"V2{i}"] for i in range(2, 3)}])
@pytest.mark.parametrize("exiting", [True, False])
async def test_checker_on_check_run(
        patches, errors, warnings, success, exiting):
    checker = Checker("path1", "path2", "path3")
    patched = patches(
        ("Checker.exiting", dict(new_callable=PropertyMock)),
        ("Checker.log", dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    check = "CHECK1"
    checker.errors = errors
    checker.warnings = warnings
    checker.success = success
    checker._active_check = check

    with patched as (m_exit, m_log):
        m_exit.return_value = exiting
        assert not await checker.on_check_run(check)

    assert checker.active_check == ""

    if exiting:
        assert not m_log.called
        return
    if check in errors:
        assert (
            m_log.return_value.error.call_args
            == [('[CHECK1] Check failed',), {}])
        assert not m_log.return_value.warning.called
        assert not m_log.return_value.success.called
        return
    if check in warnings:
        assert (
            m_log.return_value.warning.call_args
            == [('[CHECK1] Check has warnings',), {}])
        assert not m_log.return_value.error.called
        assert not m_log.return_value.info.called
        return
    if check in success:
        assert (
            m_log.return_value.notice.call_args
            == [(f"[{check}] Checks ({len(success[check])}) "
                 "completed successfully",), {}])
    else:
        assert (
            m_log.return_value.notice.call_args
            == [(f'[{check}] No checks ran',), {}])
    assert not m_log.return_value.warning.called
    assert not m_log.return_value.error.called


async def test_checker_on_checks_begin(patches):
    checker = Checker("path1", "path2", "path3")
    patched = patches(
        "Checker._notify_checks",
        "Checker._notify_preload",
        prefix="aio.run.checker.checker")

    with patched as (m_checks, m_preload):
        assert not await checker.on_checks_begin()

    assert (
        m_checks.call_args
        == [(), {}])
    assert (
        m_preload.call_args
        == [(), {}])


@pytest.mark.parametrize("failed", [True, False])
@pytest.mark.parametrize("show_summary", [True, False])
async def test_checker_on_checks_complete(patches, failed, show_summary):
    checker = Checker("path1", "path2", "path3")
    patched = patches(
        ("Checker.has_failed", dict(new_callable=PropertyMock)),
        ("Checker.show_summary", dict(new_callable=PropertyMock)),
        ("Checker.summary", dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    with patched as (m_failed, m_show_summary, m_summary):
        m_failed.return_value = failed
        m_show_summary.return_value = show_summary
        assert await checker.on_checks_complete() is (1 if failed else 0)

    if show_summary:
        assert (
            m_summary.return_value.print_summary.call_args
            == [(), {}])
    else:
        assert not m_summary.return_value.print_summary.called


@pytest.mark.parametrize(
    "raises",
    [None, RuntimeError, KeyboardInterrupt, Exception])
def test_checker_dunder_call(patches, raises):
    checker = Checker()
    patched = patches(
        "asyncio",
        "Checker.exit",
        ("Checker.cleanup", dict(new_callable=MagicMock)),
        ("Checker.run", dict(new_callable=MagicMock)),
        ("Checker.on_checks_complete", dict(new_callable=MagicMock)),
        "Checker.on_async_error",
        "Checker.setup_logging",
        "Checker.install_reactor",
        prefix="aio.run.checker.checker")

    with patched as patchy:
        (m_async, m_exit, m_cleanup,
         m_run, m_complete, m_on_err, m_log, m_reactor) = patchy
        run_until_complete = (
            m_async.get_event_loop.return_value.run_until_complete)
        if raises:
            m_run.side_effect = raises

            if raises == KeyboardInterrupt:
                result = checker.__call__()
            elif raises == RuntimeError:
                result = checker.__call__()
            else:
                with pytest.raises(raises):
                    checker.run()
                return
        else:
            assert (
                checker.__call__()
                == m_async.run.return_value)

    assert (
        m_run.call_args
        == [(), {}])

    if raises == KeyboardInterrupt:
        assert not m_async.run.called
        assert (
            m_exit.call_args
            == [(), {}])
        assert (
            m_async.get_event_loop.call_args
            == [(), {}])
        assert (
            run_until_complete.call_args
            == [(m_complete.return_value,), {}])
        assert (
            m_complete.call_args
            == [(), {}])
        assert (
            result
            == run_until_complete.return_value)
        return
    assert not m_exit.called
    assert not run_until_complete.called
    if not raises:
        assert (
            m_async.run.call_args
            == [(m_run.return_value,), {}])


TEST_WARNS: tuple = (
    {},
    dict(mywarn=[]),
    dict(mywarn=["a", "b", "c"]),
    dict(otherwarn=["other1", "other2", "other3"]),
    dict(otherwarn=["other1", "other2", "other3"], mywarn=["a", "b", "c"]))


@pytest.mark.parametrize("log", [True, False])
@pytest.mark.parametrize("warns", TEST_WARNS)
def test_checker_warn(patches, log, warns):
    checker = Checker("path1", "path2", "path3")
    log_mock = patch(
        "aio.run.checker.checker.Checker.log",
        new_callable=PropertyMock)
    checker.warnings = warns.copy()

    with log_mock as m_log:
        checker.warn("mycheck", ["warn1", "warn2", "warn3"], log)

    assert (
        checker.warnings["mycheck"]
        == warns.get("mycheck", []) + ["warn1", "warn2", "warn3"])
    for k, v in warns.items():
        if k != "mycheck":
            assert checker.warnings[k] == v
    if log:
        assert (
            m_log.return_value.warning.call_args_list
            == [[(f'[mycheck] warn{i}',), {}] for i in range(1, 4)])
    else:
        assert not m_log.return_value.warn.called


TEST_SUCCESS: tuple = (
    {},
    dict(mysuccess=[]),
    dict(mysuccess=["a", "b", "c"]),
    dict(othersuccess=["other1", "other2", "other3"]),
    dict(othersuccess=["other1", "other2", "other3"],
         mysuccess=["a", "b", "c"]))


@pytest.mark.parametrize("log", [True, False])
@pytest.mark.parametrize("success", TEST_SUCCESS)
def test_checker_succeed(patches, log, success):
    checker = Checker("path1", "path2", "path3")
    log_mock = patch(
        "aio.run.checker.checker.Checker.log",
        new_callable=PropertyMock)
    checker.success = success.copy()

    with log_mock as m_log:
        checker.succeed("mycheck", ["success1", "success2", "success3"], log)

    assert (
        checker.success["mycheck"]
        == (success.get("mycheck", [])
            + ["success1", "success2", "success3"]))
    for k, v in success.items():
        if k != "mycheck":
            assert checker.success[k] == v
    if log:
        assert (
            m_log.return_value.success.call_args_list
            == [[(f'[mycheck] success{i}',), {}] for i in range(1, 4)])
    else:
        assert not m_log.return_value.success.called


# CheckerSummary tests

def test_checker_summary_constructor():
    checker = DummyChecker()
    summary = CheckerSummary(checker)
    assert summary.checker == checker


@pytest.mark.parametrize("max_errors", [-1, 0, 1, 23])
def test_checker_summary_max_errors(max_errors):
    checker = DummyChecker()
    summary = CheckerSummary(checker)
    checker.args.summary_errors = max_errors
    assert summary.max_errors == max_errors
    assert "max_errors" not in summary.__dict__


@pytest.mark.parametrize("max_warnings", [-1, 0, 1, 23])
def test_checker_summary_max_warnings(max_warnings):
    checker = DummyChecker()
    summary = CheckerSummary(checker)
    checker.args.summary_warnings = max_warnings
    assert summary.max_warnings == max_warnings
    assert "max_warnings" not in summary.__dict__


@pytest.mark.parametrize("global_max", range(-1, 5))
def test_checker_summary_max_problems_of(patches, global_max):
    checker = DummyChecker()
    summary = CheckerSummary(checker)
    patched = patches(
        "getattr",
        "min",
        prefix="aio.run.checker.checker")

    with patched as (m_get, m_min):
        m_get.return_value = global_max
        assert (
            summary.max_problems_of("PROBLEM_TYPE", 23)
            == (m_min.return_value
                if global_max >= 0
                else 23))
    assert (
        m_get.call_args
        == [(summary, "max_PROBLEM_TYPE"), {}])
    if global_max >= 0:
        assert (
            m_min.call_args
            == [(23, global_max), {}])
    else:
        assert not m_min.called


@pytest.mark.parametrize(
    "problems",
    [{},
     {f"CHECK{i}": f"PROBLEMS{i}" for i in range(0, 5)}])
def test_checker_summary_print_failed(patches, problems):
    checker = DummyChecker()
    summary = CheckerSummary(checker)
    patched = patches(
        "getattr",
        "CheckerSummary.print_failed_check",
        prefix="aio.run.checker.checker")

    with patched as (m_get, m_print):
        m_get.return_value.items.return_value = problems.items()
        assert not summary.print_failed("PROBLEM_TYPE")

    assert (
        m_get.call_args
        == [(checker, "PROBLEM_TYPE"), {}])
    assert (
        m_print.call_args_list
        == [[("PROBLEM_TYPE", k, v), {}]
            for k, v in problems.items()])


def test_checker_summary_print_failed_check(patches):
    checker = DummyChecker()
    summary = CheckerSummary(checker)
    patched = patches(
        "CheckerSummary.writer_for",
        "CheckerSummary.problem_section",
        prefix="aio.run.checker.checker")

    with patched as (m_writer, m_section):
        assert not summary.print_failed_check(
            "PROBLEM_TYPE", "CHECK", "PROBLEMS")

    assert (
        m_writer.call_args
        == [("PROBLEM_TYPE", ), {}])
    assert (
        m_writer.return_value.call_args
        == [(m_section.return_value, ), {}])
    assert (
        m_section.call_args
        == [("PROBLEM_TYPE", "CHECK", "PROBLEMS"), {}])


def test_checker_summary_print_summary(patches):
    checker = DummyChecker()
    summary = CheckerSummary(checker)
    patched = patches(
        "CheckerSummary.print_failed",
        "CheckerSummary.print_status",
        prefix="aio.run.checker.checker")

    with patched as (m_failed, m_status):
        summary.print_summary()
    assert (
        m_failed.call_args_list
        == [[('warnings',), {}], [('errors',), {}]])
    assert m_status.called


@pytest.mark.parametrize("errors", (True, False))
@pytest.mark.parametrize("warnings", (True, False))
def test_checker_summary_print_status(patches, errors, warnings):
    checker = DummyChecker()
    summary = CheckerSummary(checker)
    summary.checker = MagicMock()
    summary.checker.errors = errors
    summary.checker.warnings = warnings

    assert not summary.print_status()

    if errors:
        assert (
            summary.checker.log.error.call_args
            == [(f"{summary.checker.status}",), {}])
        assert not summary.checker.log.warning.called
        assert not summary.checker.log.info.called
        return

    if warnings:
        assert (
            summary.checker.log.warning.call_args
            == [(f"{summary.checker.status}",), {}])
        assert not summary.checker.log.error.called
        assert not summary.checker.log.info.called
        return

    assert (
        summary.checker.log.info.call_args
        == [(f"{summary.checker.status}",), {}])
    assert not summary.checker.log.error.called
    assert not summary.checker.log.warning.called


@pytest.mark.parametrize(
    "section",
    (("MSG1", ["a", "b", "c"]),
     ("MSG2", ["a\nx", "b\ny", "c\nz"]),
     ("MSG3", [])))
@pytest.mark.parametrize("max_display", range(0, 5))
def test_checker_summary_problem_section(patches, section, max_display):
    checker = DummyChecker()
    summary = CheckerSummary(checker)
    patched = patches(
        "CheckerSummary.max_problems_of",
        "CheckerSummary.problem_title",
        prefix="aio.run.checker.checker")
    check, problems = section
    problem_type = "meltdown"

    with patched as (m_max, m_title):
        m_max.return_value = max_display
        expected = [
            (f"{problem_type.upper()} Summary "
             f"[{check}]{m_title.return_value}"),
            "-" * 80]
        expected += [
            problem.split("\n")[0] for problem in problems[:max_display]]
        expected = "\n".join(expected + [""])
        assert (
            summary.problem_section(problem_type, check, problems)
            == expected)

    assert (
        m_max.call_args
        == [(problem_type, len(problems)), {}])
    assert (
        m_title.call_args
        == [(problem_type, len(problems), max_display), {}])


@pytest.mark.parametrize("n", range(0, 5))
@pytest.mark.parametrize("max_display", range(0, 5))
def test_checker_summary_problem_title(n, max_display):
    checker = DummyChecker()
    summary = CheckerSummary(checker)
    if n > max_display and max_display > 0:
        expected = f": (showing first {max_display} of {n})"
    else:
        expected = ":"
    assert (
        summary.problem_title("PROBLEM_TYPE", n, max_display)
        == expected)


@pytest.mark.parametrize(
    "problem_type", ["warnings", "errors", "SOMETHING_ELSE"])
def test_checker_summary_writer_for(problem_type):
    checker = MagicMock()
    summary = CheckerSummary(checker)
    if problem_type == "warnings":
        expected = checker.log.notice
    else:
        expected = checker.log.error
    assert summary.writer_for(problem_type) == expected


def test_checker_check_queue(patches):
    checker = Checker()
    patched = patches(
        "asyncio",
        prefix="aio.run.checker.checker")

    with patched as (m_async, ):
        assert checker.check_queue == m_async.Queue.return_value

    assert (
        m_async.Queue.call_args
        == [(), {}])
    assert "check_queue" in checker.__dict__


@pytest.mark.parametrize(
    "checks",
    [[],
     [f"CHECK_0_{i}" for i in range(0, 5)]
     + [f"CHECK_3_{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "blocks",
    [[],
     [f"BLOCK_{i}" for i in range(0, 6)]])
def test_checker_preload_checks(checks, blocks):
    checker = Checker()
    checkers = {}
    preload_checks_data = MagicMock()
    checker.preload_checks_data = preload_checks_data
    expected = {}

    for check in checks:
        i = check.split("_")[-1]
        task = MagicMock()
        task.get.return_value = [
            block
            for block
            in blocks if block.endswith(f"_{i}")]
        checkers[check] = task

    for i, block in enumerate(blocks):
        blocked_checks = [check for check in checks if check.endswith(f"_{i}")]
        if blocked_checks:
            expected[block] = blocked_checks

    preload_checks_data.items.return_value = checkers.items()

    assert checker.preload_checks == expected

    assert (
        preload_checks_data.items.call_args
        == [(), {}])
    for task in checkers.values():
        assert (
            task.get.call_args
            == [("blocks", []), {}])
    assert "preload_checks" in checker.__dict__


def test_checker_preload_checks_data(patches):
    checker = Checker()
    patched = patches(
        "dict",
        "getattr",
        prefix="aio.run.checker.checker")

    with patched as (m_dict, m_get):
        assert checker.preload_checks_data == m_dict.return_value

    assert (
        m_dict.call_args
        == [(m_get.return_value, ), {}])
    assert (
        m_get.call_args
        == [(checker, "_preload_checks_data", ()), {}])
    assert "preload_checks_data" in checker.__dict__


@pytest.mark.parametrize(
    "checks", [[], [f"C{i}" for i in range(0, 5)]])
def test_checker_preload_tasks(patches, checks):
    checker = Checker()
    patched = patches(
        ("Checker.preload_data",
         dict(new_callable=MagicMock)),
        prefix="aio.run.checker.checker")
    checker.preload_checks_data = MagicMock()

    def iter_checks():
        for check in checks:
            yield check

    checker.preload_checks_data.__iter__.side_effect = iter_checks

    def preloader(name):
        if int(name[1:]) % 2:
            return name

    with patched as (m_preload, ):
        m_preload.side_effect = preloader
        assert (
            checker.preload_tasks
            == tuple(k for k in checks if int(k[1:]) % 2))

    assert (
        m_preload.call_args_list
        == [[(k, ), {}] for k in checks])
    assert "preload_tasks" in checker.__dict__


@pytest.mark.parametrize(
    "checks",
    [[],
     [f"C{i}" for i in range(0, 5)],
     [f"C{i}" for i in range(0, 10)]])
@pytest.mark.parametrize(
    "removed",
    [[],
     [f"C{i}" for i in range(0, 5)],
     [f"C{i}" for i in range(0, 10)]])
@pytest.mark.parametrize(
    "completed",
    [[],
     [f"C{i}" for i in range(0, 5)],
     [f"C{i}" for i in range(0, 10)]])
def test_checker_remaining_checks(patches, checks, removed, completed):
    checker = Checker()
    patched = patches(
        ("Checker.checks_to_run",
         dict(new_callable=PropertyMock)),
        ("Checker.completed_checks",
         dict(new_callable=PropertyMock)),
        ("Checker.removed_checks",
         dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    expected = []
    for check in checks:
        if check not in removed:
            if check not in completed:
                expected.append(check)

    with patched as (m_checks, m_completed, m_removed):
        m_checks.return_value = checks
        m_completed.return_value = completed
        m_removed.return_value = removed
        assert checker.remaining_checks == tuple(expected)

    assert "remaining_checks" not in checker.__dict__


@pytest.mark.parametrize(
    "to_run",
    [[],
     [f"CHECK{i}" for i in range(0, 5)],
     [f"CHECK{i}" for i in range(3, 7)],
     [f"CHECK{i}" for i in range(5, 10)]])
@pytest.mark.parametrize(
    "to_pre",
    [[],
     [f"CHECK{i}" for i in range(0, 5)],
     [f"CHECK{i}" for i in range(3, 7)],
     [f"CHECK{i}" for i in range(5, 10)]])
async def test_checker_begin_checks(patches, to_run, to_pre):
    checker = Checker()
    patched = patches(
        "asyncio",
        ("Checker.check_queue",
         dict(new_callable=PropertyMock)),
        ("Checker.checks_to_run",
         dict(new_callable=PropertyMock)),
        ("Checker.preload_checks",
         dict(new_callable=PropertyMock)),
        ("Checker.preload",
         dict(new_callable=MagicMock)),
        "Checker.on_checks_begin",
        prefix="aio.run.checker.checker")

    expected = [c for c in to_run if c not in to_pre]

    with patched as (m_io, m_q, m_run, m_checks, m_preload, m_begin):
        m_run.return_value = to_run
        m_checks.return_value = to_pre
        m_q.return_value.put = AsyncMock()
        assert not await checker.begin_checks()

    assert (
        m_begin.call_args
        == [(), {}])
    assert (
        m_preload.call_args
        == [(), {}])
    assert (
        m_io.create_task.call_args
        == [(m_preload.return_value, ), {}])

    if not expected:
        assert not m_q.return_value.put.called
    assert (
        m_q.return_value.put.call_args_list
        == [[(check, ), {}] for check in expected])


def test_checker_on_async_error():
    checker = Checker()
    loop = MagicMock()
    context = MagicMock()
    assert not checker.on_async_error(loop, context)
    assert (
        loop.default_exception_handler.call_args
        == [(context, ), {}])
    assert (
        loop.stop.call_args
        == [(), {}])


@pytest.mark.parametrize("checks", [[], [f"C{i}" for i in range(0, 5)]])
@pytest.mark.parametrize("removed", [True, False])
@pytest.mark.parametrize("pending", [True, False])
async def test_checker_on_preload(patches, checks, removed, pending):
    checker = Checker()
    patched = patches(
        ("Checker.check_queue",
         dict(new_callable=PropertyMock)),
        ("Checker.checks_to_run",
         dict(new_callable=PropertyMock)),
        ("Checker.preloaded_checks",
         dict(new_callable=PropertyMock)),
        ("Checker.preload_pending_tasks",
         dict(new_callable=PropertyMock)),
        ("Checker.removed_checks",
         dict(new_callable=PropertyMock)),
        "Checker._check_should_run",
        "Checker.on_preload_errors",
        prefix="aio.run.checker.checker")
    preload_pending = ["TASK"]
    if pending:
        preload_pending.append("OTHER_TASK")

    def should_run(check):
        return bool(int(check[1:]) % 2)

    with patched as patchy:
        (m_q, m_run, m_preload,
         m_pending, m_removed, m_should, m_err) = patchy
        m_run.return_value = checks
        m_q.return_value.put = AsyncMock()
        m_should.side_effect = should_run
        m_removed.return_value = (["TASK"] if removed else [])
        m_pending.return_value = preload_pending
        assert not await checker.on_preload("TASK")

    assert (
        m_should.call_args_list
        == [[(check, ), {}] for check in checks])
    assert (
        m_preload.return_value.add.call_args_list
        == [[(check, ), {}] for check in checks if int(check[1:]) % 2])
    assert (
        m_q.return_value.put.call_args_list
        == [[(check, ), {}] for check in checks if int(check[1:]) % 2])

    if removed and not preload_pending:
        assert (
            m_err.call_args
            == [(), {}])
    else:
        assert not m_err.called


@pytest.mark.parametrize("checks", range(0, 10))
@pytest.mark.parametrize("removed", range(0, 10))
@pytest.mark.parametrize("remaining", [True, False])
async def test_checker_on_preload_errors(
        patches, checks, removed, remaining):
    checker = Checker()
    patched = patches(
        "_sentinel",
        ("Checker.check_queue",
         dict(new_callable=PropertyMock)),
        ("Checker.checks_to_run",
         dict(new_callable=PropertyMock)),
        ("Checker.log",
         dict(new_callable=PropertyMock)),
        ("Checker.remaining_checks",
         dict(new_callable=PropertyMock)),
        ("Checker.removed_checks",
         dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")
    check_items = [""] * checks
    removed_items = [""] * removed

    with patched as (m_sentinel, m_q, m_checks, m_log, m_remaining, m_removed):
        m_checks.return_value = check_items
        m_removed.return_value = removed_items
        m_remaining.return_value = remaining
        m_q.return_value.put = AsyncMock()
        assert not await checker.on_preload_errors()

    if removed < checks:
        error_message = (
            "Some checks "
            f"({removed}/{checks}) "
            "were not run as required data failed to load")
    else:
        error_message = (
            f"All ({checks}) checks failed as required "
            "data failed to load")
    assert (
        m_log.return_value.error.call_args
        == [(error_message, ), {}])
    if remaining:
        assert not m_q.return_value.put.called
    else:
        assert (
            m_q.return_value.put.call_args
            == [(m_sentinel, ), {}])


@pytest.mark.parametrize(
    "checks",
    [[],
     [f"C{i}" for i in range(0, 5)],
     [f"C{i}" for i in range(0, 5)] + [f"C{i}" for i in range(0, 5)],
     [f"C{i}" for i in range(0, 10)]])
@pytest.mark.parametrize(
    "removed",
    [[],
     [f"C{i}" for i in range(0, 5)],
     [f"C{i}" for i in range(0, 10)]])
async def test_checker_on_preload_task_failed(patches, checks, removed):
    checker = Checker()
    patched = patches(
        ("Checker.preload_checks_data",
         dict(new_callable=PropertyMock)),
        ("Checker.removed_checks",
         dict(new_callable=PropertyMock)),
        "Checker.error",
        prefix="aio.run.checker.checker")
    # get an ordered unique list
    to_remove = list(dict.fromkeys([x for x in checks if x not in removed]))
    removed = set(removed)

    with patched as (m_data, m_removed, m_error):
        (m_data.return_value
               .__getitem__.return_value
               .__getitem__.return_value) = checks
        m_removed.return_value.__contains__.side_effect = (
            lambda x: x in removed)
        m_removed.return_value.add.side_effect = (
            lambda x: removed.add(x))
        assert not await checker.on_preload_task_failed("TASK", "ERROR")

    assert (
        m_data.return_value.__getitem__.call_args
        == [("TASK", ), {}])
    assert (
        m_data.return_value.__getitem__.return_value.__getitem__.call_args
        == [("blocks", ), {}])
    assert (
        m_removed.return_value.add.call_args_list
        == [[(check, ), {}] for check in to_remove])
    assert (
        m_error.call_args_list
        == [[(check,
              ["Check disabled: data download (TASK) failed ERROR"], ),
             {}]
            for check in to_remove])


@pytest.mark.parametrize(
    "tasks",
    [[],
     ["T23"],
     [f"T{i}" for i in range(0, 5)]])
async def test_checker_preload(patches, tasks):
    checker = Checker()
    patched = patches(
        "asyncio",
        ("Checker.preload_tasks",
         dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    with patched as (m_aio, m_tasks):
        m_aio.gather = AsyncMock()
        m_tasks.return_value = tasks
        assert not await checker.preload()

    if not tasks:
        assert not m_aio.gather.called
    else:
        assert (
            m_aio.gather.call_args
            == [tuple(tasks), {}])


@pytest.mark.parametrize("should", [True, False])
def test_checker_preload_data(patches, should):
    checker = Checker()
    patched = patches(
        ("Checker.preload_checks_data",
         dict(new_callable=PropertyMock)),
        ("Checker.preload_pending_tasks",
         dict(new_callable=PropertyMock)),
        "Checker._task_should_preload",
        ("Checker.preloader",
         dict(new_callable=MagicMock)),
        prefix="aio.run.checker.checker")

    with patched as (m_data, m_pending, m_should, m_preloader):
        m_should.return_value = should
        assert (
            checker.preload_data("TASK")
            == (m_preloader.return_value
                if should
                else None))
    assert (
        m_should.call_args
        == [("TASK", ), {}])
    if not should:
        assert not m_pending.called
        assert not m_preloader.called
        assert not m_data.called
        return
    assert (
        m_pending.return_value.add.call_args
        == [("TASK", ), {}])
    assert (
        m_preloader.call_args
        == [("TASK",
             (m_data.return_value.__getitem__.return_value
                                 .__getitem__.return_value
                                 .return_value)),
            {}])
    assert (
        m_data.return_value.__getitem__.call_args
        == [("TASK", ), {}])
    assert (
        (m_data.return_value.__getitem__.return_value
                            .__getitem__.call_args)
        == [("fun", ), {}])
    assert (
        (m_data.return_value.__getitem__.return_value
                            .__getitem__.return_value
                            .call_args)
        == [(checker, ), {}])


@pytest.mark.parametrize(
    "catches",
    [[], [Exception], [SomeError, OtherError]])
@pytest.mark.parametrize(
    "raises",
    [None, BaseException, Exception, SomeError, OtherError])
async def test_checker_preloader(patches, catches, raises):
    checker = Checker()
    patched = patches(
        "time",
        ("Checker.log",
         dict(new_callable=PropertyMock)),
        "Checker.on_preload",
        "Checker.on_preload_task_failed",
        "Checker.preloader_catches",
        prefix="aio.run.checker.checker")
    error = (
        raises("AN ERROR OCCURRED")
        if raises
        else None)

    class OrderMock:
        time_called = False
        order = MagicMock()

        def debug(self, message):
            self.order("debug", message)

        def failed(self, task, e):
            self.order("failed", task, e)

        def on_pre(self, task):
            self.order("on_pre", task)

        async def task(self):
            self.order("task")
            if error:
                raise error

        def time(self):
            self.order("time")
            if self.time_called:
                return 23
            self.time_called = True
            return 7

    order_mock = OrderMock()
    task = AsyncMock(side_effect=order_mock.task)()
    will_catch = (
        any(issubclass(raises, e) for e in catches)
        if raises
        else False)

    with patched as (m_time, m_log, m_on_pre, m_failed, m_catches):
        m_log.return_value.debug.side_effect = order_mock.debug
        m_time.time.side_effect = order_mock.time
        m_on_pre.side_effect = order_mock.on_pre
        m_failed.side_effect = order_mock.failed
        m_catches.return_value = tuple(catches)
        if raises and not will_catch:
            with pytest.raises(raises):
                await checker.preloader("NAME", task)
        else:
            assert not await checker.preloader("NAME", task)

    if raises:
        if not will_catch:
            assert (
                order_mock.order.call_args_list
                == [[('time', ), {}],
                    [('debug', 'Preloading NAME...'), {}],
                    [('task',), {}]])
            return
        assert (
            order_mock.order.call_args_list
            == [[('time',), {}],
                [('debug', 'Preloading NAME...'), {}],
                [('task',), {}],
                [('time',), {}],
                [('debug', 'Preload failed NAME in 16s'), {}],
                [('failed', 'NAME', error), {}],
                [('on_pre', "NAME"), {}]])
        return
    assert (
        order_mock.order.call_args_list
        == [[('time',), {}],
            [('debug', 'Preloading NAME...'), {}],
            [('task',), {}],
            [('time',), {}],
            [('debug', 'Preloaded NAME in 16s'), {}],
            [('on_pre', "NAME"), {}]])


def test_checker_preloader_catches(patches):
    checker = Checker()
    patched = patches(
        "tuple",
        ("Checker.preload_checks_data",
         dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    with patched as (m_tuple, m_data):
        assert (
            checker.preloader_catches("TASK")
            == m_tuple.return_value)

    assert (
        m_tuple.call_args
        == [(m_data.return_value.__getitem__.return_value.get.return_value, ),
            {}])
    assert (
        m_data.return_value.__getitem__.call_args
        == [("TASK", ), {}])
    assert (
        m_data.return_value.__getitem__.return_value.get.call_args
        == [("catches", ()), {}])


@pytest.mark.parametrize("preloads", [True, False])
@pytest.mark.parametrize("preloaded", [True, False])
@pytest.mark.parametrize("removed", [True, False])
@pytest.mark.parametrize(
    "pending", [[], ["T1"], ["T1", "T3", "T6"], ["T7"], ["T8", "T9"]])
def test_checker__check_should_run(
        patches, preloads, preloaded, removed, pending):
    checker = Checker()
    patched = patches(
        ("Checker.checks_to_run",
         dict(new_callable=PropertyMock)),
        ("Checker.preload_checks",
         dict(new_callable=PropertyMock)),
        ("Checker.preload_pending_tasks",
         dict(new_callable=PropertyMock)),
        ("Checker.preloaded_checks",
         dict(new_callable=PropertyMock)),
        ("Checker.removed_checks",
         dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")
    tasks = [f"T{i}" for i in range(0, 5)]
    task_pending = any(t in tasks for t in pending)

    with patched as (m_run, m_preloads, m_pending, m_preloaded, m_removed):
        m_preloads.return_value.__contains__.return_value = preloads
        m_preloads.return_value.__getitem__.return_value = tasks
        m_preloaded.return_value.__contains__.return_value = preloaded
        m_removed.return_value.__contains__.return_value = removed
        m_pending.return_value = pending
        assert (
            checker._check_should_run("CHECK")
            == (preloads
                and not preloaded
                and not removed
                and not task_pending))

    if not preloads:
        assert not m_preloaded.called
        assert not m_removed.called
        assert not m_preloads.return_value.__getitem__.called
        return
    if preloaded:
        assert not m_removed.called
        assert not m_preloads.return_value.__getitem__.called
        return
    if removed:
        assert not m_preloads.return_value.__getitem__.called
        return
    assert (
        m_preloads.return_value.__getitem__.call_args
        == [("CHECK", ), {}])


def test_checker__notify_checks(patches):
    checker = Checker("path1", "path2", "path3")
    patched = patches(
        ("Checker.checks_to_run", dict(new_callable=PropertyMock)),
        ("Checker.log", dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")
    checks = [f"C{i}" for i in range(0, 5)]
    joined_checks = ", ".join(checks)

    with patched as (m_checks, m_log):
        m_checks.return_value = checks
        assert not checker._notify_checks()

    assert (
        m_log.return_value.notice.call_args
        == [(f"Running checks: {joined_checks}", ), {}])


@pytest.mark.parametrize(
    "checks",
    [[],
     [f"C{i}" for i in range(0, 5)],
     [f"C{i}" for i in range(0, 10)]])
@pytest.mark.parametrize(
    "preload_checks",
    [[],
     [f"C{i}" for i in reversed(range(0, 5))],
     [f"C{i}" for i in reversed(range(0, 10))]])
def test_checker__notify_preload(patches, checks, preload_checks):
    checker = Checker("path1", "path2", "path3")
    patched = patches(
        ("Checker.checks_to_run", dict(new_callable=PropertyMock)),
        ("Checker.log", dict(new_callable=PropertyMock)),
        ("Checker.preload_checks", dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")
    preload = [x for x in checks if x in preload_checks]
    joined_checks = ", ".join(preload)

    with patched as (m_checks, m_log, m_preload):
        m_checks.return_value = checks
        m_preload.return_value = preload_checks
        assert not checker._notify_preload()

    if not joined_checks:
        assert not m_log.called
    else:
        assert (
            m_log.return_value.notice.call_args
            == [(f"Preloading: {joined_checks}", ), {}])


@pytest.mark.parametrize("raises", [True, False])
@pytest.mark.parametrize("exiting", [True, False])
async def test_checker_run(patches, raises, exiting):
    checker = Checker()
    patched = patches(
        "Checker.begin_checks",
        "Checker._run_from_queue",
        "Checker.on_checks_complete",
        ("Checker.exiting", dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    with patched as (m_start, m_run_q, m_complete, m_exit):
        m_exit.return_value = exiting
        if raises:
            m_run_q.side_effect = SomeError("AN ERROR OCCURRED")

            with pytest.raises(SomeError):
                await checker.run()
        elif exiting:
            assert await checker.run() == 1
        else:
            assert await checker.run() == m_complete.return_value

    assert (
        m_start.call_args
        == [(), {}])
    assert (
        m_run_q.call_args
        == [(), {}])

    if exiting:
        assert not m_complete.called
    else:
        assert (
            m_complete.call_args
            == [(), {}])


async def test_checker__run_check(patches):
    checker = Checker()
    patched = patches(
        "getattr",
        "Checker.on_check_begin",
        "Checker.on_check_run",
        prefix="aio.run.checker.checker")

    class OrderMock:
        order = MagicMock()

        def on_check_begin(self, check):
            self.order("on_check_begin", check)

        async def call(self):
            self.order("call")

        def on_check_run(self, check):
            self.order("on_check_run", check)

    order_mock = OrderMock()

    with patched as (m_attr, m_begin, m_run):
        m_attr.return_value.side_effect = order_mock.call
        m_begin.side_effect = order_mock.on_check_begin
        m_run.side_effect = order_mock.on_check_run
        assert not await checker._run_check("CHECK")

    assert (
        order_mock.order.call_args_list
        == [[('on_check_begin', 'CHECK'), {}],
            [('call',), {}],
            [('on_check_run', 'CHECK'), {}]])
    assert (
        m_begin.call_args
        == m_run.call_args
        == [("CHECK", ), {}])
    assert (
        m_attr.call_args
        == [(checker, "check_CHECK"), {}])


@pytest.mark.parametrize(
    "checks",
    [[],
     ["SENTINEL"],
     [f"C{i}" for i in range(0, 5)],
     ["SENTINEL"] + [f"C{i}" for i in range(0, 5)],
     [f"C{i}" for i in range(0, 5)] + ["SENTINEL"],
     ([f"C{i}" for i in range(0, 2)]
      + ["SENTINEL"]
      + [f"C{i}" for i in range(0, 2)])])
async def test_checker__run_from_queue(patches, checks):
    checker = Checker()
    patched = patches(
        "_sentinel",
        "Checker.log",
        "Checker._run_check",
        ("Checker.check_queue",
         dict(new_callable=PropertyMock)),
        ("Checker.completed_checks",
         dict(new_callable=PropertyMock)),
        ("Checker.remaining_checks",
         dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")

    class Getter:
        i = 0

        def __init__(self, sentinel):
            self.sentinel = sentinel

        def remaining(self):
            return len(checks) - self.i

        async def get(self):
            result = checks[self.i]
            self.i += 1
            if result == "SENTINEL":
                return self.sentinel
            return result

    if "SENTINEL" in checks:
        expected = checks[:checks.index("SENTINEL")]
    else:
        expected = checks

    with patched as patchy:
        (m_sentinel, m_log, m_run,
         m_q, m_completed, m_remaining) = patchy

        getter = Getter(m_sentinel)
        m_q.return_value.get = AsyncMock(side_effect=getter.get)
        m_remaining.side_effect = getter.remaining
        assert not await checker._run_from_queue()

    if not checks:
        assert not m_q.called
        assert not m_run.called
        assert not m_completed.called
        return
    get_calls = (
        len(expected) + 1
        if "SENTINEL" in checks
        else len(expected))
    assert (
        m_q.return_value.get.call_args_list
        == [[(), {}]] * get_calls)
    assert (
        m_run.call_args_list
        == [[(check, ), {}] for check in expected])
    assert (
        m_q.return_value.task_done.call_args_list
        == [[(), {}] for check in expected])
    assert (
        m_completed.return_value.add.call_args_list
        == [[(check, ), {}] for check in expected])


@pytest.mark.parametrize("pending", [True, False])
@pytest.mark.parametrize(
    "when", [[], ["C1"], ["C1", "C3", "C6"], ["C7"], ["C8", "C9"]])
@pytest.mark.parametrize(
    "unless", [[], ["C1"], ["C1", "C3", "C6"], ["C7"], ["C8", "C9"]])
def test_checker__task_should_preload(patches, pending, when, unless):
    checker = Checker()
    patched = patches(
        ("Checker.preload_checks_data",
         dict(new_callable=PropertyMock)),
        ("Checker.checks_to_run",
         dict(new_callable=PropertyMock)),
        ("Checker.preload_pending_tasks",
         dict(new_callable=PropertyMock)),
        prefix="aio.run.checker.checker")
    checks_to_run = [f"C{i}" for i in range(0, 5)]
    handler = MagicMock()
    when_matches = any(c in checks_to_run for c in when)
    unless_matches = any(c in checks_to_run for c in unless)

    def getter(of, default):
        if of == "when":
            return when
        return unless

    handler.get.side_effect = getter

    with patched as (m_data, m_run, m_pending):
        m_pending.return_value.__contains__.return_value = pending
        m_run.return_value = checks_to_run
        m_data.return_value.__getitem__.return_value = handler
        assert (
            checker._task_should_preload("TASK")
            == (not (pending or not when_matches or unless_matches)))

    assert (
        m_data.return_value.__getitem__.call_args
        == [("TASK", ), {}])
    if pending:
        assert not m_run.called
        assert not handler.get.called
        return
    if not when_matches:
        assert (
            handler.get.call_args_list
            == [[('when', []), {}]])
        return
    assert (
        handler.get.call_args_list
        == [[('when', []), {}],
            [('unless', []), {}]])
