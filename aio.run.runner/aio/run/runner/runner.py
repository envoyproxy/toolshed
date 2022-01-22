#
# Generic runner class for use by cli implementations
#

import argparse
import asyncio
import logging
import pathlib
import sys
import tempfile
from functools import cached_property
from typing import Optional

from frozendict import frozendict

import coloredlogs  # type:ignore
import verboselogs  # type:ignore

from .decorators import cleansup


LOG_LEVELS = (
    ("debug", logging.DEBUG),
    ("info", logging.INFO),
    ("warn", logging.WARN),
    ("error", logging.ERROR))
LOG_FIELD_STYLES: frozendict = frozendict(
    name=frozendict(color="blue"),
    levelname=frozendict(color="cyan", bold=True))
LOG_FMT = "%(name)s %(levelname)s %(message)s"
LOG_LEVEL_STYLES: frozendict = frozendict(
    critical=frozendict(bold=True, color="red"),
    debug=frozendict(color="green"),
    error=frozendict(color="red", bold=True),
    info=frozendict(color="white", bold=True),
    notice=frozendict(color="magenta", bold=True),
    spam=frozendict(color="green", faint=True),
    success=frozendict(bold=True, color="green"),
    verbose=frozendict(color="blue"),
    warning=frozendict(color="yellow", bold=True))


class BazelRunError(Exception):
    pass


class BaseLogFilter(logging.Filter):

    def __init__(self, app_logger: logging.Logger, *args, **kwargs) -> None:
        self.app_logger = app_logger


class AppLogFilter(BaseLogFilter):

    def filter(self, record) -> bool:
        return record.name == self.app_logger.name


class RootLogFilter(BaseLogFilter):

    def filter(self, record) -> bool:
        return record.name != self.app_logger.name


class Runner:

    def __init__(self, *args):
        self._args = args
        self.setup_logging()

    def __call__(self):
        try:
            return asyncio.run(self.run())
        except KeyboardInterrupt:
            self.log.error("Keyboard exit")
            return 1

    @cached_property
    def args(self) -> argparse.Namespace:
        """Parsed args."""
        return self.parser.parse_known_args(self._args)[0]

    @cached_property
    def extra_args(self) -> list:
        """Unparsed args."""
        return self.parser.parse_known_args(self._args)[1]

    @cached_property
    def log(self) -> verboselogs.VerboseLogger:
        """Instantiated logger."""
        app_logger = verboselogs.VerboseLogger(self.name)
        coloredlogs.install(
            field_styles=self.log_field_styles,
            level_styles=self.log_level_styles,
            fmt=self.log_fmt,
            level=self.verbosity,
            logger=app_logger,
            isatty=True)
        return app_logger

    @property
    def log_field_styles(self):
        return LOG_FIELD_STYLES

    @property
    def log_fmt(self):
        return LOG_FMT

    @cached_property
    def log_level(self) -> int:
        """Log level parsed from args."""
        return dict(LOG_LEVELS)[self.args.log_level]

    @property
    def log_level_styles(self):
        return LOG_LEVEL_STYLES

    @property
    def name(self) -> str:
        """Name of the runner."""
        return self.__class__.__name__

    @cached_property
    def parser(self) -> argparse.ArgumentParser:
        """Argparse parser."""
        parser = argparse.ArgumentParser(allow_abbrev=False)
        self.add_arguments(parser)
        return parser

    @cached_property
    def path(self) -> pathlib.Path:
        return pathlib.Path(".")

    @property
    def root_log_format(self) -> logging.Formatter:
        return logging.Formatter("%(name)s: %(levelname)s %(message)s")

    @cached_property
    def root_log_handler(self) -> logging.Handler:
        """Instantiated logger."""
        root_handler = logging.StreamHandler()
        root_handler.setLevel(self.log_level)
        root_handler.addFilter(RootLogFilter(self.log))
        root_handler.setFormatter(self.root_log_format)
        return root_handler

    @cached_property
    def root_logger(self) -> logging.Logger:
        """Instantiated logger."""
        root_logger = logging.getLogger()
        root_logger.handlers[0].addFilter(AppLogFilter(self.log))
        root_logger.addHandler(self.root_log_handler)
        return root_logger

    @cached_property
    def stdout(self) -> logging.Logger:
        """Log to stdout."""
        logger = logging.getLogger("stdout")
        logger.setLevel(self.log_level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        return logger

    @cached_property
    def tempdir(self) -> tempfile.TemporaryDirectory:
        """If you call this property, remember to call `.cleanup`

        For `run` methods this should be done by decorating the method
        with `@runner.cleansup`
        """
        if self._missing_cleanup:
            self.log.warning(
                "Tempdir created but instance has a `run` method which is not "
                "decorated with `@runner.cleansup`")
        return tempfile.TemporaryDirectory()

    @cached_property
    def verbosity(self) -> int:
        """Log level parsed from args."""
        return dict(LOG_LEVELS)[self.args.verbosity]

    @property
    def _missing_cleanup(self) -> bool:
        run_fun = getattr(self, "run", None)
        return bool(
            run_fun
            and not getattr(
                getattr(run_fun, "__wrapped__", object()),
                "__cleansup__", False))

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Override this method to add custom arguments to the arg parser."""
        parser.add_argument(
            "--verbosity",
            "-v",
            choices=[level[0] for level in LOG_LEVELS],
            default="info",
            help="Application log level")
        parser.add_argument(
            "--log-level",
            "-l",
            choices=[level[0] for level in LOG_LEVELS],
            default="warn",
            help="Log level for non-application logs")

    async def cleanup(self) -> None:
        self._cleanup_tempdir()

    def setup_logging(self):
        logging.basicConfig(level=self.log_level)
        self.root_logger.setLevel(self.log_level)
        self.log.setLevel(self.verbosity)

    def _cleanup_tempdir(self) -> None:
        if "tempdir" in self.__dict__:
            self.tempdir.cleanup()
            del self.__dict__["tempdir"]

    @cleansup
    async def run(self) -> Optional[int]:
        raise NotImplementedError
