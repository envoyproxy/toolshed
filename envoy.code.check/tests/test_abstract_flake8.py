
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from flake8.main.application import Application

from envoy.code import check


def test_check_flake8_files(patches):
    patched = patches(
        "Flake8App",
        prefix="envoy.code.check.abstract.flake8")
    path = MagicMock()
    files = MagicMock()
    args = MagicMock()

    with patched as (m_app, ):
        assert (
            check.AFlake8Check.check_flake8_files(path, args, files)
            == m_app.return_value.run_checks.return_value)

    assert (
        m_app.call_args
        == [(path, args), {}])
    assert (
        m_app.return_value.run_checks.call_args
        == [(files, ), {}])


def test_filter_flake8_files(patches):
    patched = patches(
        "Flake8App",
        prefix="envoy.code.check.abstract.flake8")
    path = MagicMock()
    files = MagicMock()
    args = MagicMock()

    with patched as (m_app, ):
        assert (
            check.AFlake8Check.filter_flake8_files(path, args, files)
            == m_app.return_value.include_files.return_value)

    assert (
        m_app.call_args
        == [(path, args), {}])
    assert (
        m_app.return_value.include_files.call_args
        == [(files, ), {}])


def test_flake8_constructor():
    flake8 = check.AFlake8Check("DIRECTORY")
    assert flake8.directory == "DIRECTORY"
    assert isinstance(flake8, check.ACodeCheck)


async def test_flake8_checker_files(patches):
    directory = MagicMock()
    flake8 = check.AFlake8Check(directory)
    patched = patches(
        ("AFlake8Check.flake8_args",
         dict(new_callable=PropertyMock)),
        ("AFlake8Check.execute",
         dict(new_callable=AsyncMock)),
        "AFlake8Check.filter_flake8_files",
        prefix="envoy.code.check.abstract.flake8")
    files = AsyncMock()
    directory.files = files()

    with patched as (m_args, m_execute, m_filter):
        assert (
            await flake8.checker_files
            == m_execute.return_value)

    assert (
        m_execute.call_args
        == [(m_filter,
             directory.absolute_path,
             m_args.return_value,
             files.return_value), {}])
    assert not (
        hasattr(
            flake8,
            check.AFlake8Check.checker_files.cache_name))


async def test_flake8_problem_files(patches):
    directory = MagicMock()
    flake8 = check.AFlake8Check(directory)
    patched = patches(
        ("AFlake8Check.flake8_errors",
         dict(new_callable=PropertyMock)),
        "AFlake8Check.handle_errors",
        prefix="envoy.code.check.abstract.flake8")

    with patched as (m_errors, m_handle):
        errors = AsyncMock()
        m_errors.side_effect = errors
        assert (
            await flake8.problem_files
            == m_handle.return_value
            == getattr(
                flake8,
                check.AFlake8Check.problem_files.cache_name)["problem_files"])

    assert (
        m_handle.call_args
        == [(errors.return_value, ), {}])


def test_flake8_flake8_args(patches):
    directory = MagicMock()
    flake8 = check.AFlake8Check(directory)
    patched = patches(
        ("AFlake8Check.flake8_config_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.flake8")

    with patched as (m_config, ):
        assert (
            flake8.flake8_args
            == ("--config", str(m_config.return_value), str(directory.path)))

    assert "flake8_args" not in flake8.__dict__


def test_flake8_flake8_config_path():
    directory = MagicMock()
    flake8 = check.AFlake8Check(directory)
    assert (
        flake8.flake8_config_path
        == directory.path.joinpath.return_value)
    assert (
        directory.path.joinpath.call_args
        == [(check.abstract.flake8.FLAKE8_CONFIG, ), {}])
    assert "flake8_config_path" not in flake8.__dict__


async def test_flake8_flake8_errors(patches):
    directory = MagicMock()
    flake8 = check.AFlake8Check(directory)
    patched = patches(
        ("AFlake8Check.files",
         dict(new_callable=PropertyMock)),
        ("AFlake8Check.flake8_args",
         dict(new_callable=PropertyMock)),
        "AFlake8Check.check_flake8_files",
        ("AFlake8Check.execute",
         dict(new_callable=AsyncMock)),
        prefix="envoy.code.check.abstract.flake8")

    with patched as (m_files, m_args, m_checks, m_execute):
        files = AsyncMock()
        m_files.side_effect = files
        assert (
            await flake8.flake8_errors
            == m_execute.return_value)

    assert (
        m_execute.call_args
        == [(m_checks,
             directory.absolute_path,
             m_args.return_value,
             files.return_value), {}])
    assert not (
        hasattr(
            flake8,
            check.AFlake8Check.flake8_errors.cache_name))


def test_flake8_handle_errors(iters, patches):
    flake8 = check.AFlake8Check("DIRECTORY")
    patched = patches(
        "checker",
        "AFlake8Check._parse_error",
        prefix="envoy.code.check.abstract.flake8")
    errors = iters(cb=lambda i: MagicMock())

    class Handler:
        counter = 0

        def _parse_error(self, error):
            self.counter += 1
            if self.counter % 2:
                return "PATH1", f"MESSAGE{self.counter}"
            return "PATH2", f"MESSAGE{self.counter}"

    handler = Handler()

    with patched as (m_checker, m_parse):
        m_parse.side_effect = handler._parse_error
        assert (
            flake8.handle_errors(errors)
            == {'PATH1': m_checker.Problems.return_value,
                'PATH2': m_checker.Problems.return_value})

    assert (
        m_checker.Problems.call_args_list
        == [[(), dict(errors=['MESSAGE1', 'MESSAGE3', 'MESSAGE5'])],
            [(), dict(errors=['MESSAGE2', 'MESSAGE4'])]])

    assert (
        m_parse.call_args_list
        == [[(error, ),
             {}]
            for error in errors])


def test_flake8__parse_error():
    directory = MagicMock()
    flake8 = check.AFlake8Check(directory)
    error = MagicMock()
    assert (
        flake8._parse_error(error)
        == (error.split.return_value.__getitem__.return_value,
            (f"{error.split.return_value.__getitem__.return_value}: "
             f"{error.split.return_value.__getitem__.return_value}")))
    assert (
        error.split.call_args_list
        == [[(":", ), {}],
            [(":", 1), {}]])
    assert (
        error.split.return_value.__getitem__.call_args_list
        == [[(0,), {}],
            [(1, ), {}]])


def test_flake8app_constructor(patches):
    flake8app = check.abstract.flake8.Flake8App("PATH", "ARGS")
    assert flake8app.path == "PATH"
    assert flake8app.args == "ARGS"
    assert flake8app._excluded_paths == set()
    assert "_excluded_paths" in flake8app.__dict__


def test_flake8app_app(patches):
    flake8app = check.abstract.flake8.Flake8App("PATH", "ARGS")
    patched = patches(
        "Flake8Application",
        prefix="envoy.code.check.abstract.flake8")

    with patched as (m_app, ):
        assert flake8app.app == m_app.return_value

    assert (
        m_app.call_args
        == [(), {}])
    assert (
        m_app.return_value.initialize.call_args
        == [("ARGS", ), {}])
    assert "app" in flake8app.__dict__


def test_flake8app_exclude(patches):
    flake8app = check.abstract.flake8.Flake8App("PATH", "ARGS")
    patched = patches(
        ("Flake8App.manager",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.flake8")

    with patched as (m_manager, ):
        assert (
            flake8app.exclude
            == m_manager.return_value.options.exclude)

    assert "exclude" not in flake8app.__dict__


def test_flake8app_manager(patches):
    flake8app = check.abstract.flake8.Flake8App("PATH", "ARGS")
    patched = patches(
        ("Flake8App.app",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.flake8")

    with patched as (m_app, ):
        assert (
            flake8app.manager
            == m_app.return_value.file_checker_manager)

    assert "manager" not in flake8app.__dict__


@pytest.mark.parametrize("filename_matches", [True, False])
@pytest.mark.parametrize("include_dir", [True, False])
@pytest.mark.parametrize("is_excluded", [True, False])
def test_flake8app_include_file(
        patches, filename_matches, include_dir, is_excluded):
    path = MagicMock()
    flake8 = check.abstract.flake8.Flake8App(path, "ARGS")
    patched = patches(
        "os",
        "Flake8App._filename_matches",
        "Flake8App._include_directory",
        "Flake8App._is_excluded",
        prefix="envoy.code.check.abstract.flake8")

    with patched as (m_os, m_match, m_include, m_exclude):
        m_match.return_value = filename_matches
        m_include.return_value = include_dir
        m_exclude.return_value = is_excluded
        assert (
            flake8.include_file("INCPATH")
            == (filename_matches
                and include_dir
                and not is_excluded))

    assert (
        m_os.path.join.call_args
        == [(path, "INCPATH"), {}])
    assert (
        m_match.call_args
        == [(m_os.path.join.return_value, ), {}])
    if not filename_matches:
        assert not m_include.called
        assert not m_exclude.called
        assert not m_os.path.dirname.called
        return
    assert (
        m_include.call_args
        == [(m_os.path.dirname.return_value, ), {}])
    assert (
        m_os.path.dirname.call_args
        == [(m_os.path.join.return_value, ), {}])
    if not include_dir:
        assert not m_exclude.called
        return
    assert (
        m_exclude.call_args
        == [(m_os.path.join.return_value, ), {}])


@pytest.mark.parametrize("n", range(1, 5))
def test_flake8app_include_files(iters, patches, n):
    flake8 = check.abstract.flake8.Flake8App("PATH", "ARGS")
    patched = patches(
        "os",
        "Flake8App.include_file",
        prefix="envoy.code.check.abstract.flake8")
    files = iters(cb=lambda i: f"F{i}", count=7)

    class Includer:
        counter = 0

        def include_file(self, f):
            self.counter += 1
            return bool(self.counter % n)

    includer = Includer()

    with patched as (m_os, m_include):
        m_include.side_effect = includer.include_file
        assert (
            flake8.include_files(files)
            == set([
                f
                for i, f
                in enumerate(files)
                if (i + 1) % n]))

    assert (
        m_include.call_args_list
        == [[(m_os.path.join.return_value, ), {}]] * 7)
    assert (
        m_os.path.join.call_args_list
        == [[("PATH", f), {}]
            for f in files])


def test_flake8app_run_checks(patches):
    flake8 = check.abstract.flake8.Flake8App("PATH", "ARGS")
    patched = patches(
        "directory_context",
        ("Flake8App.app",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.flake8")
    paths = MagicMock()

    with patched as (m_dir_ctx, m_app):
        assert (
            flake8.run_checks(paths)
            == m_app.return_value._results)

    assert (
        m_dir_ctx.call_args
        == [("PATH", ), {}])
    assert (
        m_app.return_value.file_checker_manager.start.call_args
        == [(paths, ), {}])
    assert (
        m_app.return_value.report.call_args
        == [(), {}])


def test_flake8app__filename_matches(patches):
    flake8 = check.abstract.flake8.Flake8App("PATH", "ARGS")
    patched = patches(
        "flake8_utils",
        ("Flake8App.app",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.flake8")

    with patched as (m_utils, m_app):
        assert (
            flake8._filename_matches("PATHMATCH")
            == m_utils.fnmatch.return_value)

    assert (
        m_utils.fnmatch.call_args
        == [("PATHMATCH", m_app.return_value.options.filename), {}])


@pytest.mark.parametrize(
    "paths",
    [[],
     [f"PATH{i}" for i in range(0, 5)]])
@pytest.mark.parametrize("exclude", [None, "PATH0", "PATH3", "PATH23"])
def test_flake8app__include_directory(patches, paths, exclude):
    flake8 = check.abstract.flake8.Flake8App("DIR_PATH", "ARGS")
    patched = patches(
        "os",
        "str",
        "Flake8App._include_path",
        prefix="envoy.code.check.abstract.flake8")

    class DummyPaths:
        i = 0

        def get_path(self, path):
            if len(paths) > self.i:
                path = paths[self.i]
                self.i += 1
                return path
            return "DIR_PATH"

    dummy_paths = DummyPaths()

    with patched as (m_os, m_str, m_include):
        m_os.path.dirname.side_effect = dummy_paths.get_path
        m_include.side_effect = lambda p: p != exclude
        assert (
            flake8._include_directory("INCPATH")
            == (exclude not in paths))

    pindex = len(paths)
    if exclude in paths:
        pindex = paths.index(exclude)
    assert (
        m_os.path.dirname.call_args_list
        == [[(p, ), {}]
            for p in ["INCPATH", *paths[:pindex]]])
    assert (
        m_include.call_args_list
        == [[(p, ), {}]
            for p in ["INCPATH", *paths[:pindex + 1]]])
    assert flake8._include_directory.cache_info().misses >= 1
    assert flake8._include_directory.cache_info().currsize >= 1


@pytest.mark.parametrize("any_paths", [True, False])
@pytest.mark.parametrize("is_excluded", [True, False])
def test_flake8app__include_path(iters, patches, any_paths, is_excluded):
    flake8 = check.abstract.flake8.Flake8App("PATH", "ARGS")
    patched = patches(
        "any",
        ("Flake8App._excluded_paths",
         dict(new_callable=PropertyMock)),
        "Flake8App._is_excluded",
        prefix="envoy.code.check.abstract.flake8")
    paths = iters(cb=lambda i: MagicMock())
    path = MagicMock()

    def iter_paths():
        for path in paths:
            yield path

    with patched as (m_any, m_paths, m_exclude):
        m_paths.return_value.__iter__.side_effect = iter_paths
        m_any.return_value = any_paths
        m_exclude.return_value = is_excluded
        assert (
            flake8._include_path(path)
            == (not (any_paths or is_excluded)))
        any_iter = m_any.call_args[0][0]
        any_args = list(any_iter)

    assert (
        any_args
        == ([path.startswith.return_value]
            * len(paths)))
    assert (
        path.startswith.call_args_list
        == [[(p, ), {}] for p in paths])
    if any_paths:
        assert not m_exclude.called
    if any_paths or is_excluded:
        assert (
            m_paths.return_value.add.call_args
            == [(path, ), {}])
    else:
        assert not m_paths.return_value.add.called
    assert flake8._include_path.cache_info().misses >= 1
    assert flake8._include_path.cache_info().currsize >= 1


@pytest.mark.parametrize("exclude", [True, False])
@pytest.mark.parametrize("base_match", [True, False])
@pytest.mark.parametrize("abs_match", [True, False])
def test_flake8__is_excluded(patches, exclude, base_match, abs_match):
    flake8 = check.abstract.flake8.Flake8App("PATH", "ARGS")
    patched = patches(
        "os",
        "flake8_utils",
        "logger",
        ("Flake8App.exclude",
         dict(new_callable=PropertyMock)),
        ("Flake8App.manager",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.flake8")
    base_path = MagicMock()
    abs_path = MagicMock()
    exclude = (MagicMock() if exclude else False)

    def _fnmatch(path, exclude):
        if path == base_path:
            return base_match
        return abs_match

    with patched as (m_os, m_utils, m_logger, m_exclude, m_manager):
        m_exclude.return_value = exclude
        m_utils.fnmatch.side_effect = _fnmatch
        m_os.path.basename.return_value = base_path
        m_os.path.abspath.return_value = abs_path

        assert (
            flake8._is_excluded("EXCPATH")
            == (exclude
                and (base_match or abs_match)))

    if not exclude:
        assert not m_os.path.basename.called
        assert not m_os.path.abspath.called
        assert not m_utils.fnmatch.called
        assert not m_logger.debug.called
        return

    assert (
        m_os.path.basename.call_args
        == [("EXCPATH", ), {}])
    assert (
        m_utils.fnmatch.call_args_list[0]
        == [(base_path, exclude), {}])
    if base_match:
        assert (
            m_logger.debug.call_args
            == [(f'"{base_path}" has been excluded', ), {}])
        assert len(m_utils.fnmatch.call_args_list) == 1
        assert not m_os.path.abspath.called
        return
    assert (
        m_utils.fnmatch.call_args_list[1]
        == [(abs_path, exclude), {}])
    assert (
        m_logger.debug.call_args
        == [(
            f'"{abs_path}" has '
            f'{"" if abs_match else "not "}been excluded', ),
            {}])


def test_flake8application_constructor():
    app = check.abstract.flake8.Flake8Application()
    assert isinstance(app, Application)


def test_flake8application_output_fd(patches):
    app = check.abstract.flake8.Flake8Application()
    patched = patches(
        "io",
        prefix="envoy.code.check.abstract.flake8")

    with patched as (m_io, ):
        assert (
            app.output_fd
            == m_io.StringIO.return_value)

    assert (
        m_io.StringIO.call_args
        == [(), {}])
    assert "output_fd" in app.__dict__


@pytest.mark.parametrize("n", range(1, 5))
def test_flake8application__stop(patches, n):
    app = check.abstract.flake8.Flake8Application()
    patched = patches(
        ("Flake8Application.output_fd",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.flake8")
    app._formatter_stop = MagicMock()
    results = [
        ("F{i}"
         if i % n
         else None)
        for i
        in range(0, 7)]

    class Splitter:

        def split(self, f):
            return results

    splitter = Splitter()

    with patched as (m_out, ):
        (m_out.return_value.read
              .return_value.strip
              .return_value.split.side_effect) = splitter.split
        assert not app._stop()

    assert (
        m_out.return_value.seek.call_args
        == [(0, ), {}])
    assert (
        app._formatter_stop.call_args
        == [(), {}])
    assert (
        app._results
        == [r for r in results if r])


def test_flake8application_make_formatter(patches):
    app = check.abstract.flake8.Flake8Application()
    patched = patches(
        ("Application.make_formatter",
         dict(new_callable=PropertyMock)),
        ("Flake8Application.output_fd",
         dict(new_callable=PropertyMock)),
        "Flake8Application._stop",
        prefix="envoy.code.check.abstract.flake8")
    app.formatter = MagicMock()
    stop = app.formatter.stop

    with patched as (m_super, m_out, m_stop):
        assert not app.make_formatter()

    assert (
        m_super.call_args
        == [(), {}])
    assert app.formatter.output_fd == m_out.return_value
    assert app._formatter_stop == stop
    assert app.formatter.stop == m_stop
