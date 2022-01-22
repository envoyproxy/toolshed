import types
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock

import pytest

from envoy.code_format import python_check


class DummyPythonChecker(python_check.APythonChecker):

    @property
    def path(self):
        return super().path


def test_abstract_python_checker_constructor():
    checker = DummyPythonChecker("path1", "path2", "path3")
    assert checker.checks == ("flake8", "yapf")
    assert checker.args.paths == ['path1', 'path2', 'path3']


@pytest.mark.parametrize("diff_path", ["", None, "PATH"])
def test_abstract_python_checker_diff_path(patches, diff_path):
    checker = DummyPythonChecker("path1", "path2", "path3")
    patched = patches(
        "pathlib",
        ("APythonChecker.args", dict(new_callable=PropertyMock)),
        prefix="envoy.code_format.python_check.abstract")

    with patched as (m_plib, m_args):
        m_args.return_value.diff_file = diff_path
        assert (
            checker.diff_file_path
            == (m_plib.Path.return_value if diff_path else None))

    if diff_path:
        assert (
            list(m_plib.Path.call_args)
            == [(m_args.return_value.diff_file, ), {}])
    else:
        assert not m_plib.Path.called


def test_abstract_python_checker_flake8_app(patches):
    checker = DummyPythonChecker("path1", "path2", "path3")
    patched = patches(
        ("APythonChecker.flake8_args", dict(new_callable=PropertyMock)),
        "Flake8Application",
        prefix="envoy.code_format.python_check.abstract")

    with patched as (m_flake8_args, m_flake8_app):
        assert checker.flake8_app == m_flake8_app.return_value

    assert (
        list(m_flake8_app.call_args)
        == [(), {}])
    assert (
        list(m_flake8_app.return_value.initialize.call_args)
        == [(m_flake8_args.return_value,), {}])


def test_abstract_python_checker_flake8_args(patches):
    checker = DummyPythonChecker("path1", "path2", "path3")
    patched = patches(
        ("APythonChecker.flake8_config_path", dict(new_callable=PropertyMock)),
        ("APythonChecker.path", dict(new_callable=PropertyMock)),
        prefix="envoy.code_format.python_check.abstract")

    with patched as (m_flake8_config, m_path):
        assert (
            checker.flake8_args
            == ('--config',
                str(m_flake8_config.return_value),
                str(m_path.return_value)))


def test_abstract_python_checker_flake8_config_path(patches):
    checker = DummyPythonChecker("path1", "path2", "path3")
    patched = patches(
        ("APythonChecker.path", dict(new_callable=PropertyMock)),
        prefix="envoy.code_format.python_check.abstract")

    with patched as (m_path, ):
        assert (
            checker.flake8_config_path
            == m_path.return_value.joinpath.return_value)

    assert (
        list(m_path.return_value.joinpath.call_args)
        == [(python_check.abstract.FLAKE8_CONFIG, ), {}])


def test_abstract_python_checker_path(patches):
    checker = DummyPythonChecker("path1", "path2", "path3")
    patched = patches(
        ("checker.Checker.path", dict(new_callable=PropertyMock)),
        prefix="envoy.code_format.python_check.abstract")

    with patched as (m_super, ):
        assert checker.path == m_super.return_value


def test_abstract_python_checker_yapf_config_path(patches):
    checker = DummyPythonChecker("path1", "path2", "path3")
    patched = patches(
        ("APythonChecker.path", dict(new_callable=PropertyMock)),
        prefix="envoy.code_format.python_check.abstract")

    with patched as (m_path, ):
        assert (
            checker.yapf_config_path
            == m_path.return_value.joinpath.return_value)

    assert (
        list(m_path.return_value.joinpath.call_args)
        == [(python_check.abstract.YAPF_CONFIG, ), {}])


def test_abstract_python_checker_yapf_files(patches):
    checker = DummyPythonChecker("path1", "path2", "path3")

    patched = patches(
        ("APythonChecker.args", dict(new_callable=PropertyMock)),
        ("APythonChecker.path", dict(new_callable=PropertyMock)),
        "yapf.file_resources.GetCommandLineFiles",
        "yapf.file_resources.GetExcludePatternsForDir",
        prefix="envoy.code_format.python_check.abstract")

    with patched as (m_args, m_path, m_yapf_files, m_yapf_exclude):
        assert checker.yapf_files == m_yapf_files.return_value

    assert (
        list(m_yapf_files.call_args)
        == [(m_args.return_value.paths,),
            {'recursive': m_args.return_value.recurse,
             'exclude': m_yapf_exclude.return_value}])
    assert (
        list(m_yapf_exclude.call_args)
        == [(str(m_path.return_value),), {}])


def test_abstract_python_checker_add_arguments(patches):
    checker = DummyPythonChecker("path1", "path2", "path3")
    add_mock = patch(
        "envoy.code_format.python_check.abstract"
        ".checker.Checker.add_arguments")
    m_parser = MagicMock()

    with add_mock as m_add:
        checker.add_arguments(m_parser)

    assert (
        list(m_add.call_args)
        == [(m_parser,), {}])
    assert (
        list(list(c) for c in m_parser.add_argument.call_args_list)
        == [[('--recurse', '-r'),
             {'choices': ['yes', 'no'],
              'default': 'yes',
              'help': 'Recurse path or paths directories'}],
            [('--diff-file',),
             {'default': None,
              'help': 'Specify the path to a diff file with fixes'}]])


@pytest.mark.parametrize("errors", [[], ["err1", "err2"]])
async def test_abstract_python_checker_check_flake8(patches, errors):
    checker = DummyPythonChecker("path1", "path2", "path3")

    patched = patches(
        "utils.buffered",
        "APythonChecker.error",
        "APythonChecker._strip_lines",
        ("APythonChecker.flake8_app", dict(new_callable=PropertyMock)),
        prefix="envoy.code_format.python_check.abstract")

    @contextmanager
    def mock_buffered(stdout=None, mangle=None):
        yield
        stdout.extend(errors)

    with patched as (m_buffered, m_error, m_mangle, m_flake8_app):
        m_buffered.side_effect = mock_buffered
        assert not await checker.check_flake8()

    assert (
        list(m_buffered.call_args)
        == [(), {'stdout': errors, 'mangle': m_mangle}])
    assert (
        list(m_flake8_app.return_value.run_checks.call_args)
        == [(), {}])
    assert (
        list(m_flake8_app.return_value.report.call_args)
        == [(), {}])

    if errors:
        assert (
            list(m_error.call_args)
            == [('flake8', ['err1', 'err2']), {}])
    else:
        assert not m_error.called


def test_abstract_python_checker_check_recurse():
    checker = DummyPythonChecker("path1", "path2", "path3")
    args_mock = patch(
        "envoy.code_format.python_check.abstract.APythonChecker.args",
        new_callable=PropertyMock)

    with args_mock as m_args:
        assert checker.recurse == m_args.return_value.recurse
    assert "recurse" not in checker.__dict__


async def test_abstract_python_checker_check_yapf(patches):
    checker = DummyPythonChecker("path1", "path2", "path3")
    patched = patches(
        ("concurrent", dict(new_callable=MagicMock)),
        ("APythonChecker.yapf_format", dict(new_callable=MagicMock)),
        "APythonChecker.yapf_result",
        ("APythonChecker.yapf_files", dict(new_callable=PropertyMock)),
        prefix="envoy.code_format.python_check.abstract")
    files = ["file1", "file2", "file3"]

    async def concurrent(iters):
        assert isinstance(iters, types.GeneratorType)
        for i, format_result in enumerate(iters):
            yield (
                format_result,
                (f"REFORMAT{i}", f"ENCODING{i}", f"CHANGED{i}"))

    with patched as (m_concurrent, m_yapf_format, m_yapf_result, m_yapf_files):
        m_yapf_files.return_value = files
        m_concurrent.side_effect = concurrent
        assert not await checker.check_yapf()

    assert (
        list(list(c) for c in m_yapf_format.call_args_list)
        == [[(file,), {}] for file in files])
    assert (
        list(list(c) for c in m_yapf_result.call_args_list)
        == [[(m_yapf_format.return_value, f"REFORMAT{i}", f"CHANGED{i}"), {}]
            for i, _ in enumerate(files)])


@pytest.mark.parametrize(
    "errors",
    [[], ["check2", "check3"], ["check1", "check3"]])
@pytest.mark.parametrize(
    "warnings",
    [[], ["check4", "check5"], ["check1", "check5"]])
async def test_abstract_python_checker_on_check_run(patches, errors, warnings):
    checker = DummyPythonChecker("path1", "path2", "path3")
    checkname = "check1"
    patched = patches(
        "APythonChecker.succeed",
        ("APythonChecker.name", dict(new_callable=PropertyMock)),
        ("APythonChecker.failed", dict(new_callable=PropertyMock)),
        ("APythonChecker.warned", dict(new_callable=PropertyMock)),
        prefix="envoy.code_format.python_check.abstract")

    with patched as (m_succeed, m_name, m_failed, m_warned):
        m_failed.return_value = errors
        m_warned.return_value = warnings
        assert not await checker.on_check_run(checkname)

    if checkname in warnings or checkname in errors:
        assert not m_succeed.called
    else:
        assert (
            list(m_succeed.call_args)
            == [(checkname, [checkname]), {}])


@pytest.mark.parametrize("diff_path", ["", "DIFF1"])
@pytest.mark.parametrize("failed", [True, False])
async def test_abstract_python_checker_on_checks_complete(
        patches, diff_path, failed):
    checker = DummyPythonChecker("path1", "path2", "path3")
    patched = patches(
        "run",
        ("checker.Checker.on_checks_complete",
         dict(new_callable=AsyncMock)),
        ("APythonChecker.diff_file_path",
         dict(new_callable=PropertyMock)),
        ("APythonChecker.has_failed",
         dict(new_callable=PropertyMock)),
        ("APythonChecker.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code_format.python_check.abstract")

    with patched as (m_run, m_super, m_diff, m_failed, m_path):
        if not diff_path:
            m_diff.return_value = None
        m_failed.return_value = failed
        assert await checker.on_checks_complete() == m_super.return_value

    if diff_path and failed:
        assert (
            list(m_run.call_args)
            == [(['git', 'diff', 'HEAD'],),
                dict(capture_output=True, cwd=m_path.return_value)])
        assert (
            list(m_diff.return_value.write_bytes.call_args)
            == [(m_run.return_value.stdout,), {}])
    else:
        assert not m_run.called

    assert (
        list(m_super.call_args)
        == [(), {}])


@pytest.mark.parametrize("fix", [True, False])
async def test_abstract_python_checker_yapf_format(patches, fix):
    checker = DummyPythonChecker("path1", "path2", "path3")
    patched = patches(
        "yapf.yapf_api.FormatFile",
        ("APythonChecker.yapf_config_path", dict(new_callable=PropertyMock)),
        ("APythonChecker.fix", dict(new_callable=PropertyMock)),
        prefix="envoy.code_format.python_check.abstract")

    with patched as (m_format, m_config, m_fix):
        m_fix.return_value = fix
        assert (
            await checker.yapf_format("FILENAME")
            == ("FILENAME", m_format.return_value))

    assert (
        list(m_format.call_args)
        == [('FILENAME',),
            {'style_config': str(m_config.return_value),
             'in_place': fix,
             'print_diff': not fix}])
    assert (
        list(list(c) for c in m_fix.call_args_list)
        == [[(), {}], [(), {}]])


@pytest.mark.parametrize("reformatted", ["", "REFORMAT"])
@pytest.mark.parametrize("fix", [True, False])
@pytest.mark.parametrize("changed", [True, False])
def test_abstract_python_checker_yapf_result(
        patches, reformatted, fix, changed):
    checker = DummyPythonChecker("path1", "path2", "path3")
    patched = patches(
        "APythonChecker.succeed",
        "APythonChecker.warn",
        "APythonChecker.error",
        ("APythonChecker.fix", dict(new_callable=PropertyMock)),
        prefix="envoy.code_format.python_check.abstract")

    with patched as (m_succeed, m_warn, m_error, m_fix):
        m_fix.return_value = fix
        checker.yapf_result("FILENAME", reformatted, changed)

    if not changed:
        assert (
            list(m_succeed.call_args)
            == [('yapf', ['FILENAME']), {}])
        assert not m_warn.called
        assert not m_error.called
        assert not m_fix.called
        return
    assert not m_succeed.called
    if fix:
        assert not m_error.called
        assert len(m_warn.call_args_list) == 1
        assert (
            list(m_warn.call_args)
            == [('yapf', ['FILENAME: reformatted']), {}])
        return
    if reformatted:
        assert not m_error.called
        assert len(m_warn.call_args_list) == 1
        assert (
            list(m_warn.call_args)
            == [('yapf', [f'FILENAME: diff\n{reformatted}']), {}])
        return
    assert not m_warn.called
    assert (
        list(m_error.call_args)
        == [('yapf', ['FILENAME']), {}])


def test_abstract_python_checker_strip_lines():
    checker = DummyPythonChecker("path1", "path2", "path3")
    strip_mock = patch(
        "envoy.code_format.python_check.abstract.APythonChecker._strip_line")
    lines = ["", "foo", "", "bar", "", "", "baz", "", ""]

    with strip_mock as m_strip:
        assert (
            checker._strip_lines(lines)
            == [m_strip.return_value] * 3)

    assert (
        list(list(c) for c in m_strip.call_args_list)
        == [[('foo',), {}], [('bar',), {}], [('baz',), {}]])


@pytest.mark.parametrize(
    "line",
    ["REMOVE/foo", "REMOVE", "bar", "other", "REMOVE/baz", "baz"])
def test_abstract_python_checker_strip_line(line):
    checker = DummyPythonChecker("path1", "path2", "path3")
    path_mock = patch(
        "envoy.code_format.python_check.abstract.APythonChecker.path",
        new_callable=PropertyMock)

    with path_mock as m_path:
        m_path.return_value = "REMOVE"
        assert (
            checker._strip_line(line)
            == line[7:] if line.startswith("REMOVE/") else line)
