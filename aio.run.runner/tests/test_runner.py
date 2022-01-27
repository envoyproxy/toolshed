
import logging
import sys
from unittest.mock import MagicMock, PropertyMock

import pytest

from aio.run import runner


class DummyRunner(runner.Runner):

    def __init__(self):
        self.args = PropertyMock()


def test_base_log_filter():
    filter = runner.runner.BaseLogFilter("APP_LOGGER")
    assert isinstance(filter, logging.Filter)
    assert filter.app_logger == "APP_LOGGER"


@pytest.mark.parametrize("name", ["APP_LOGGER", "SOMETHING_ELSE"])
def test_root_log_filter(name):
    app_logger = MagicMock()
    app_logger.name = "APP_LOGGER"
    filter = runner.runner.RootLogFilter(app_logger)
    assert isinstance(filter, runner.runner.BaseLogFilter)
    assert filter.app_logger == app_logger
    record = MagicMock()
    record.name = name
    assert (
        filter.filter(record)
        == (name != "APP_LOGGER"))


def test_runner_constructor(patches):
    patched = patches(
        "Runner.setup_logging",
        prefix="aio.run.runner.runner")

    with patched as (m_setup, ):
        run = runner.Runner("path1", "path2", "path3")

    assert (
        m_setup.call_args
        == [(), {}])
    assert run._args == ("path1", "path2", "path3")
    assert run.log_field_styles == runner.runner.LOG_FIELD_STYLES
    assert run.log_level_styles == runner.runner.LOG_LEVEL_STYLES
    assert run.log_fmt == runner.runner.LOG_FMT


@pytest.mark.parametrize("raises", [None, KeyboardInterrupt])
def test_runner_dunder_call(patches, raises):
    patched = patches(
        "asyncio",
        ("Runner.log", dict(new_callable=MagicMock)),
        ("Runner.run", dict(new_callable=MagicMock)),
        "Runner.setup_logging",
        prefix="aio.run.runner.runner")

    # TODO: TEST LOG

    with patched as (m_asyncio, m_log, m_run, m_setup):
        run = runner.Runner()
        if raises:
            m_run.side_effect = raises("DIE")
        assert (
            run()
            == (m_asyncio.run.return_value
                if not raises
                else 1))

    if not raises:
        assert (
            m_asyncio.run.call_args
            == [(m_run.return_value, ), {}])
    else:
        assert not m_asyncio.run.called
    assert (
        m_run.call_args
        == [(), {}])


def test_runner_args(patches):
    patched = patches(
        ("Runner.parser",
         dict(new_callable=PropertyMock)),
        "Runner.setup_logging",
        prefix="aio.run.runner.runner")

    with patched as (m_parser, m_setup):
        run = runner.Runner('path1', 'path2', 'path3')
        known_args = m_parser.return_value.parse_known_args
        assert (
            run.args
            == known_args.return_value.__getitem__.return_value)

    assert (
        known_args.call_args
        == [(('path1', 'path2', 'path3'),), {}])
    assert (
        known_args.return_value.__getitem__.call_args
        == [(0,), {}])
    assert "args" in run.__dict__


def test_runner_extra_args(patches):
    patched = patches(
        ("Runner.parser",
         dict(new_callable=PropertyMock)),
        "Runner.setup_logging",
        prefix="aio.run.runner.runner")

    with patched as (m_parser, m_setup):
        run = runner.Runner('path1', 'path2', 'path3')
        known_args = m_parser.return_value.parse_known_args
        assert (
            run.extra_args
            == known_args.return_value.__getitem__.return_value)

    assert (
        known_args.call_args
        == [(('path1', 'path2', 'path3'),), {}])
    assert (
        known_args.return_value.__getitem__.call_args
        == [(1,), {}])
    assert "extra_args" in run.__dict__


def test_runner_log(patches):
    patched = patches(
        "coloredlogs",
        "verboselogs",
        ("Runner.log_field_styles",
         dict(new_callable=PropertyMock)),
        ("Runner.log_fmt",
         dict(new_callable=PropertyMock)),
        ("Runner.log_level_styles",
         dict(new_callable=PropertyMock)),
        ("Runner.name",
         dict(new_callable=PropertyMock)),
        ("Runner.verbosity",
         dict(new_callable=PropertyMock)),
        "Runner.setup_logging",
        prefix="aio.run.runner.runner")

    with patched as patchy:
        (m_color, m_verb, m_fstyle, m_fmt,
         m_lstyle, m_name, m_verbosity, m_setup) = patchy
        run = runner.Runner('path1', 'path2', 'path3')
        assert run.log == m_verb.VerboseLogger.return_value

    assert (
        m_verb.VerboseLogger.call_args
        == [(m_name.return_value, ), {}])

    assert (
        m_color.install.call_args
        == [(),
            {'fmt': m_fmt.return_value,
             'isatty': True,
             'field_styles': m_fstyle.return_value,
             'level': m_verbosity.return_value,
             'level_styles': m_lstyle.return_value,
             'logger': m_verb.VerboseLogger.return_value}])
    assert "log" in run.__dict__


def test_runner_log_level(patches):
    run = DummyRunner()
    patched = patches(
        "dict",
        ("Runner.args", dict(new_callable=PropertyMock)),
        prefix="aio.run.runner.runner")
    with patched as (m_dict, m_args):
        assert run.log_level == m_dict.return_value.__getitem__.return_value

    assert (
        m_dict.call_args
        == [(runner.runner.LOG_LEVELS, ), {}])
    assert (
        m_dict.return_value.__getitem__.call_args
        == [(m_args.return_value.log_level,), {}])
    assert "log_level" in run.__dict__


def test_runner_name():
    run = DummyRunner()
    assert run.name == run.__class__.__name__
    assert "name" not in run.__dict__


def test_runner_parser(patches):
    run = DummyRunner()
    patched = patches(
        "argparse",
        "Runner.add_arguments",
        prefix="aio.run.runner.runner")
    with patched as (m_parser, m_add_args):
        assert run.parser == m_parser.ArgumentParser.return_value

    assert (
        m_parser.ArgumentParser.call_args
        == [(), {"allow_abbrev": False}])
    assert (
        m_add_args.call_args
        == [(m_parser.ArgumentParser.return_value,), {}])
    assert "parser" in run.__dict__


def test_runner_path(patches):
    run = DummyRunner()
    patched = patches(
        "pathlib",
        prefix="aio.run.runner.runner")

    with patched as (m_plib, ):
        assert run.path == m_plib.Path.return_value

    assert (
        m_plib.Path.call_args
        == [(".", ), {}])


def test_runner_root_log_format(patches):
    run = DummyRunner()
    patched = patches(
        "logging",
        prefix="aio.run.runner.runner")

    with patched as (m_logging, ):
        assert run.root_log_format == m_logging.Formatter.return_value

    assert (
        m_logging.Formatter.call_args
        == [("%(name)s: %(levelname)s %(message)s", ), {}])
    assert "root_log_format" not in run.__dict__


def test_runner_root_log_handler(patches):
    run = DummyRunner()
    patched = patches(
        "logging",
        "RootLogFilter",
        ("Runner.log", dict(new_callable=PropertyMock)),
        ("Runner.log_level", dict(new_callable=PropertyMock)),
        ("Runner.root_log_format", dict(new_callable=PropertyMock)),
        prefix="aio.run.runner.runner")

    with patched as (m_logging, m_filter, m_log, m_level, m_format):
        assert run.root_log_handler == m_logging.StreamHandler.return_value

    assert (
        m_logging.StreamHandler.call_args
        == [(), {}])
    assert (
        m_logging.StreamHandler.return_value.setLevel.call_args
        == [(m_level.return_value, ), {}])
    assert (
        m_logging.StreamHandler.return_value.addFilter.call_args
        == [(m_filter.return_value, ), {}])
    assert (
        m_filter.call_args
        == [(m_log.return_value, ), {}])
    assert (
        m_logging.StreamHandler.return_value.setFormatter.call_args
        == [(m_format.return_value, ), {}])
    assert "root_log_handler" in run.__dict__


def test_runner_root_logger(patches):
    run = DummyRunner()
    patched = patches(
        "logging",
        ("Runner.log", dict(new_callable=PropertyMock)),
        ("Runner.root_log_handler", dict(new_callable=PropertyMock)),
        prefix="aio.run.runner.runner")

    with patched as (m_logging, m_log, m_handler):
        assert run.root_logger == m_logging.getLogger.return_value

    assert (
        m_logging.getLogger.call_args
        == [(), {}])
    assert (
        m_logging.getLogger.return_value.handlers.__getitem__.call_args
        == [(0, ), {}])
    assert (
        m_logging.getLogger.return_value.removeHandler.call_args
        == [(m_logging.getLogger.return_value
                      .handlers.__getitem__.return_value, ),
            {}])
    assert (
        m_logging.getLogger.return_value.addHandler.call_args
        == [(m_handler.return_value, ), {}])
    assert "root_logger" in run.__dict__


def test_runner_stdout(patches):
    run = DummyRunner()
    patched = patches(
        "logging",
        ("Runner.log_level", dict(new_callable=PropertyMock)),
        prefix="aio.run.runner.runner")

    with patched as (m_log, m_level):
        assert run.stdout == m_log.getLogger.return_value

    assert (
        m_log.getLogger.call_args
        == [('stdout',), {}])
    assert (
        m_log.getLogger.return_value.setLevel.call_args
        == [(m_level.return_value,), {}])
    assert (
        m_log.StreamHandler.call_args
        == [(sys.stdout,), {}])
    assert (
        m_log.Formatter.call_args
        == [('%(message)s',), {}])
    assert (
        m_log.StreamHandler.return_value.setFormatter.call_args
        == [(m_log.Formatter.return_value,), {}])
    assert (
        m_log.getLogger.return_value.addHandler.call_args
        == [(m_log.StreamHandler.return_value,), {}])


@pytest.mark.parametrize("missing", [True, False])
def test_runner_tempdir(patches, missing):
    run = DummyRunner()
    patched = patches(
        "tempfile",
        ("Runner.log", dict(new_callable=PropertyMock)),
        ("Runner._missing_cleanup", dict(new_callable=PropertyMock)),
        prefix="aio.run.runner.runner")

    with patched as (m_tmp, m_log, m_missing):
        m_missing.return_value = missing
        assert run.tempdir == m_tmp.TemporaryDirectory.return_value

    if missing:
        assert (
            m_log.return_value.warning.call_args
            == [(("Tempdir created but instance has a `run` method "
                  "which is not decorated with `@runner.cleansup`"), ), {}])
    else:
        assert not m_log.called

    assert (
        m_tmp.TemporaryDirectory.call_args
        == [(), {}])
    assert "tempdir" in run.__dict__


def test_runner_verbosity(patches):
    run = DummyRunner()
    patched = patches(
        "dict",
        ("Runner.args", dict(new_callable=PropertyMock)),
        prefix="aio.run.runner.runner")
    with patched as (m_dict, m_args):
        assert run.verbosity == m_dict.return_value.__getitem__.return_value

    assert (
        m_dict.call_args
        == [(runner.runner.LOG_LEVELS, ), {}])
    assert (
        m_dict.return_value.__getitem__.call_args
        == [(m_args.return_value.verbosity,), {}])
    assert "verbosity" in run.__dict__


def test_runner_add_arguments():
    run = DummyRunner()
    parser = MagicMock()

    assert run.add_arguments(parser) is None

    assert (
        parser.add_argument.call_args_list
        == [[('--verbosity',
              '-v'),
             {'choices': ['debug',
                          'info',
                          'warn',
                          'error'],
              'default': 'info',
              'help': 'Application log level'}],
            [('--log-level', '-l'),
             {'choices': ['debug', 'info', 'warn', 'error'],
              'default': 'warn',
              'help': 'Log level for non-application logs'}]])


def test_runner_setup_logging(patches):
    run = DummyRunner()
    patched = patches(
        "logging",
        ("Runner.log",
         dict(new_callable=PropertyMock)),
        ("Runner.log_level",
         dict(new_callable=PropertyMock)),
        ("Runner.root_logger",
         dict(new_callable=PropertyMock)),
        ("Runner.verbosity",
         dict(new_callable=PropertyMock)),
        prefix="aio.run.runner.runner")

    with patched as (m_logging, m_log, m_level, m_root, m_verb):
        assert not run.setup_logging()

    assert (
        m_logging.basicConfig.call_args
        == [(), dict(level=m_level.return_value)])
    assert (
        m_root.return_value.setLevel.call_args
        == [(m_level.return_value, ), {}])
    assert (
        m_log.return_value.setLevel.call_args
        == [(m_verb.return_value, ), {}])


@pytest.mark.parametrize("has_fun", [True, False])
@pytest.mark.parametrize("is_wrapped", [True, False])
@pytest.mark.parametrize("cleansup", [True, False])
def test_runner__missing_cleanup(has_fun, is_wrapped, cleansup):

    def _runner_factory():
        if not has_fun:
            return DummyRunner()

        class _Wrap:
            if cleansup:
                __cleansup__ = True

        class _Wrapper:
            if is_wrapped:
                __wrapped__ = _Wrap()

        class DummyRunner2(DummyRunner):
            run = _Wrapper()

        return DummyRunner2()

    run = _runner_factory()

    assert (
        run._missing_cleanup
        == (has_fun
            and not (is_wrapped and cleansup)))
    assert "_missing_cleanup" not in run.__dict__


@pytest.mark.parametrize("cached", [True, False])
def test_runner__cleanup_tempdir(patches, cached):
    run = DummyRunner()
    patched = patches(
        ("Runner.tempdir", dict(new_callable=PropertyMock)),
        prefix="aio.run.runner.runner")
    if cached:
        run.__dict__["tempdir"] = "TEMPDIR"

    with patched as (m_temp, ):
        assert not run._cleanup_tempdir()

    if cached:
        assert (
            m_temp.return_value.cleanup.call_args
            == [(), {}])
    else:
        assert not m_temp.called
    assert "tempdir" not in run.__dict__


async def test_runner_cleanup(patches):
    patched = patches(
        "Runner._cleanup_tempdir",
        "Runner.setup_logging",
        prefix="aio.run.runner.runner")

    with patched as (m_temp, m_setup):
        run = runner.Runner()
        assert not await run.cleanup()

    assert (
        m_temp.call_args
        == [(), {}])
