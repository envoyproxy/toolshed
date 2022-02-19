
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

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
            check.AFlake8Check.check_flake8_files(path, files, args)
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
            check.AFlake8Check.filter_flake8_files(path, files, args)
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
    assert flake8._errors == {}
    assert "_errors" in flake8.__dict__


@pytest.mark.parametrize("files", [True, False])
async def test_flake8_checker_files(patches, files):
    directory = MagicMock()
    flake8 = check.AFlake8Check(directory)
    patched = patches(
        ("AFlake8Check.flake8_args",
         dict(new_callable=PropertyMock)),
        "AFlake8Check.execute",
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
             files.return_value,
             m_args.return_value), {}])
    assert not (
        hasattr(
            flake8,
            check.AFlake8Check.checker_files.cache_name))


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
        "threaded",
        ("AFlake8Check.absolute_paths",
         dict(new_callable=PropertyMock)),
        ("AFlake8Check.flake8_args",
         dict(new_callable=PropertyMock)),
        ("AFlake8Check._errors",
         dict(new_callable=PropertyMock)),
        "AFlake8Check.check_flake8_files",
        "AFlake8Check._handle_error",
        prefix="envoy.code.check.abstract.flake8")

    with patched as (m_threaded, m_abs, m_args, m_errs, m_checks, m_handle):
        files = AsyncMock()
        m_abs.side_effect = files
        assert (
            await flake8.errors
            == m_errs.return_value)

    assert (
        m_threaded.call_args
        == [(m_checks,
             directory.absolute_path,
             files.return_value,
             m_args.return_value),
            dict(stdout=m_handle)])

    assert not (
        hasattr(
            flake8,
            check.AFlake8Check.errors.cache_name))


@pytest.mark.parametrize("files", [True, False])
async def test_flake8_problem_files(patches, files):
    directory = MagicMock()
    flake8 = check.AFlake8Check(directory)
    patched = patches(
        ("AFlake8Check.errors",
         dict(new_callable=PropertyMock)),
        ("AFlake8Check.files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.flake8")

    with patched as (m_errors, m_files):
        m_files.side_effect = AsyncMock(return_value=files)
        errors = AsyncMock()
        m_errors.side_effect = errors
        result = await flake8.problem_files

    assert (
        getattr(
            flake8,
            check.AFlake8Check.problem_files.cache_name)[
                "problem_files"]
        == result
        == (errors.return_value
            if files
            else {}))
    if not files:
        assert not m_errors.called


@pytest.mark.parametrize("msg", [True, False])
async def test_flake8__handle_error(patches, msg):
    directory = MagicMock()
    flake8 = check.AFlake8Check(directory)
    patched = patches(
        "str",
        ("AFlake8Check._errors",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.flake8")

    with patched as (m_str, m_errors):
        if not msg:
            m_str.return_value = None
        assert not await flake8._handle_error("ERROR")

    assert (
        m_str.call_args
        == [("ERROR", ), {}])
    if not msg:
        assert not directory.relative_path.called
        return
    message = m_str.return_value
    assert (
        directory.relative_path.call_args
        == [(m_str.return_value.split.return_value.__getitem__.return_value, ),
            {}])
    path = directory.relative_path.return_value
    assert (
        m_errors.return_value.__setitem__.call_args
        == [(path, m_errors.return_value.get.return_value, ), {}])
    assert (
        m_errors.return_value.get.call_args
        == [(path, []), {}])
    assert (
        m_errors.return_value.__getitem__.call_args
        == [(path, ), {}])
    assert (
        m_errors.return_value.__getitem__.return_value.append.call_args
        == [(f"{path}: {message.split.return_value.__getitem__.return_value}",
             ), {}])

    assert (
        message.split.call_args_list
        == [[(":", ), {}],
            [(":", 1), {}]])
    assert (
        message.split.return_value.__getitem__.call_args_list
        == [[(0, ), {}],
            [(1, ), {}]])


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


@pytest.mark.parametrize("filename_matches", [True, False])
@pytest.mark.parametrize("include_dir", [True, False])
@pytest.mark.parametrize("is_excluded", [True, False])
def test_flake8app__include_file(
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


@pytest.mark.parametrize("any_paths", [True, False])
@pytest.mark.parametrize("is_excluded", [True, False])
def test_flake8app__include_path(patches, any_paths, is_excluded):
    flake8 = check.abstract.flake8.Flake8App("PATH", "ARGS")
    patched = patches(
        "any",
        ("Flake8App._excluded_paths",
         dict(new_callable=PropertyMock)),
        "Flake8App._is_excluded",
        prefix="envoy.code.check.abstract.flake8")
    paths = [MagicMock() for x in range(0, 5)]
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


def test_flake8__is_excluded(patches):
    flake8 = check.abstract.flake8.Flake8App("PATH", "ARGS")
    patched = patches(
        ("Flake8App.app",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.flake8")

    with patched as (m_app, ):
        assert (
            flake8._is_excluded("EXCPATH")
            == (m_app.return_value
                     .file_checker_manager.is_path_excluded.return_value))

    assert (
        m_app.return_value.file_checker_manager.is_path_excluded.call_args
        == [("EXCPATH", ), {}])
