"""Abstract code checker."""

import abc
import argparse
import pathlib
import re
from functools import cached_property
from typing import Mapping, Pattern

import yaml

from yamllint.config import YamlLintConfigError  # type:ignore

import abstracts

from aio.core import directory as _directory, event, subprocess
from aio.core.tasks import inflate
from aio.run import checker

from envoy.base import utils
from envoy.base.utils import IProject
from envoy.code.check import exceptions, interface, typing


# TODO: Add a README in envoy repo with info on how to fix and maybe use
#   a template
GLINT_ADVICE = (
    "Glint check failed\n"
    "\n"
    "  Please fix your editor to ensure:\n"
    "\n"
    "      - no trailing whitespace\n"
    "      - no preceding mixed tabs/spaces\n"
    "      - all files end with a newline")

NO_EXTENSIONS_ERROR_MSG = (
    "`--extensions_build_config` not provided, disabling extensions checks")
NO_EXTENSIONS_FUZZ_ERROR_MSG = (
    "`--extensions_fuzzed_count` not provided, "
    "disabling extensions fuzz checks")


class CodeCheckerSummary(checker.CheckerSummary):

    def print_summary(self) -> None:
        """Write summary to stderr."""
        super().print_summary()
        if "glint" in self.checker.errors:
            self.writer_for("error")(GLINT_ADVICE)


@abstracts.implementer(interface.ICodeChecker)
class ACodeChecker(
        checker.Checker,
        event.AReactive,
        metaclass=abstracts.Abstraction):
    """Code checker."""

    checks = (
        "changelog",
        "extensions_fuzzed",
        "extensions_metadata",
        "extensions_owners",
        "extensions_registered",
        "glint",
        "gofmt",
        "python_yapf",
        "python_flake8",
        "runtime_guards",
        "shellcheck",
        "yamllint")

    @property
    def all_files(self) -> bool:
        return self.args.all_files

    @cached_property
    def binaries(self) -> dict[str, str]:
        return dict(
            binary.split(":")
            for binary
            in self.args.binary or [])

    @cached_property
    def disabled_checks(self):
        disabled = {}
        if not self.args.extensions_build_config:
            disabled["extensions_fuzzed"] = NO_EXTENSIONS_ERROR_MSG
            disabled["extensions_metadata"] = NO_EXTENSIONS_ERROR_MSG
            disabled["extensions_registered"] = NO_EXTENSIONS_ERROR_MSG
        elif self.args.extensions_fuzzed_count is None:
            disabled["extensions_fuzzed"] = NO_EXTENSIONS_FUZZ_ERROR_MSG
        return disabled

    @property
    def changed_since(self) -> str | None:
        return self.args.since

    @cached_property
    def changelog(self) -> "interface.IChangelogCheck":
        """Changelog checker."""
        return self.changelog_class(
            self.project,
            **self.check_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def changelog_class(self) -> type["interface.IChangelogCheck"]:
        raise NotImplementedError

    @cached_property
    def check_kwargs(self) -> Mapping:
        return dict(
            fix=self.fix,
            binaries=self.binaries,
            loop=self.loop,
            pool=self.pool)

    @cached_property
    def config(self) -> typing.YAMLConfigDict:
        return (
            yaml.safe_load(self.config_path.read_text())
            if self.config_path
            else {})

    @property
    def config_path(self) -> pathlib.Path | None:
        if not self.args.config:
            return None
        path = pathlib.Path(self.args.config)
        if not path.exists():
            raise exceptions.ConfigurationError(
                f"Config specified but not found: {path}")
        return path

    @cached_property
    def directory(self) -> "_directory.ADirectory":
        """Greppable directory - optionally in a git repo, depending on whether
        we want to look at all files.
        """
        return self.project.directory.filtered(**self.directory_kwargs)

    @property
    def directory_kwargs(self) -> dict:
        kwargs: dict = dict(
            exclude_matcher=self.grep_excluding_re,
            path_matcher=self.grep_matching_re,
            untracked=self.all_files)
        if not self.all_files:
            kwargs["changed"] = self.changed_since
        return kwargs

    @cached_property
    def extensions(self) -> "interface.IExtensionsCheck":
        """Extensions checker."""
        return self.extensions_class(
            self.directory,
            owners=self.args.owners,
            codeowners=self.args.codeowners,
            extensions_build_config=self.args.extensions_build_config,
            extensions_fuzzed_count=self.args.extensions_fuzzed_count,
            **self.check_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def extensions_class(self) -> type["interface.IExtensionsCheck"]:
        raise NotImplementedError

    @cached_property
    def flake8(self) -> "interface.IFlake8Check":
        """Flake8 checker."""
        return self.flake8_class(self.directory, **self.check_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def flake8_class(self) -> type["interface.IFlake8Check"]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def fs_directory_class(self) -> type["_directory.ADirectory"]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def git_directory_class(self) -> type["_directory.AGitDirectory"]:
        raise NotImplementedError

    @cached_property
    def glint(self) -> "interface.IGlintCheck":
        """Glint checker."""
        return self.glint_class(self.directory, **self.check_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def glint_class(self) -> type["interface.IGlintCheck"]:
        raise NotImplementedError

    @cached_property
    def gofmt(self) -> "interface.IGofmtCheck":
        """Gofmt checker."""
        return self.gofmt_class(self.directory, **self.check_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def gofmt_class(self) -> type["interface.IGofmtCheck"]:
        raise NotImplementedError

    @property
    def grep_excluding_re(self) -> Pattern[str] | None:
        return self._grep_re(self.args.excluding)

    @property
    def grep_matching_re(self) -> Pattern[str] | None:
        return self._grep_re(self.args.matching)

    @property
    @abc.abstractmethod
    def path(self) -> pathlib.Path:
        return super().path

    @cached_property
    def project(self) -> IProject:
        return self.project_class(self.path)

    @property  # type:ignore
    @abstracts.interfacemethod
    def project_class(self) -> type[IProject]:
        raise NotImplementedError

    @cached_property
    def runtime_guards(self) -> "interface.IRuntimeGuardsCheck":
        """Shellcheck checker."""
        return self.runtime_guards_class(
            self.project,
            **self.check_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def runtime_guards_class(self) -> type["interface.IRuntimeGuardsCheck"]:
        raise NotImplementedError

    @cached_property
    def shellcheck(self) -> "interface.IShellcheckCheck":
        """Shellcheck checker."""
        return self.shellcheck_class(self.directory, **self.check_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def shellcheck_class(self) -> type["interface.IShellcheckCheck"]:
        raise NotImplementedError

    @property
    def summary_class(self) -> type[CodeCheckerSummary]:
        """CodeChecker's summary class."""
        return CodeCheckerSummary

    @cached_property
    def yamllint(self) -> interface.IYamllintCheck:
        """Yamllint checker."""
        return self.yamllint_class(self.directory, **self.check_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def yamllint_class(self) -> type[interface.IYamllintCheck]:
        raise NotImplementedError

    @cached_property
    def yapf(self) -> interface.IYapfCheck:
        """YAPF checker."""
        return self.yapf_class(self.directory, **self.check_kwargs)

    @property  # type:ignore
    @abstracts.interfacemethod
    def yapf_class(self) -> type[interface.IYapfCheck]:
        raise NotImplementedError

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("-a", "--all_files", action="store_true")
        parser.add_argument("-m", "--matching", action="append")
        parser.add_argument("-x", "--excluding", action="append")
        parser.add_argument("-b", "--binary", action="append")
        parser.add_argument("-s", "--since")
        parser.add_argument(
            "--config",
            default="./tools/code/config.yaml",
            help=("specify the config path. "
                  "Default './tools/code/config.yaml'."))
        parser.add_argument("--codeowners")
        parser.add_argument("--owners")
        parser.add_argument("--extensions_build_config")
        parser.add_argument("--extensions_fuzzed_count")

    async def check_changelog(self):
        for changelog in self.changelog:
            if errors := await changelog.errors:
                self.error("changelog", errors)
            else:
                self.succeed(
                    "changelog",
                    [f"{changelog.version}"])

    async def check_extensions_fuzzed(self) -> None:
        """Check for glint issues."""
        if await self.extensions.all_fuzzed:
            self.succeed(
                "extensions_fuzzed",
                ["All network filters are fuzzed"])
        else:
            self.error(
                "extensions_fuzzed",
                ["Check that all network filters robust against untrusted "
                 "downstreams are fuzzed by adding them to filterNames() "
                 f"in {self.extensions.fuzz_test_path}"])

    async def check_extensions_metadata(self) -> None:
        """Check for glint issues."""
        errors = await self.extensions.metadata_errors
        for extension, errors in errors.items():
            if errors:
                self.error("extensions_metadata", errors)
            else:
                self.succeed("extensions_metadata", [f"{extension}"])

    async def check_extensions_owners(self) -> None:
        """Check for glint issues."""
        checks = await self.extensions.owners_errors
        for extension, errors in sorted(checks.items()):
            if errors:
                self.error("extensions_owners", errors)
            else:
                self.succeed("extensions_owners", [f"{extension}"])

    async def check_extensions_registered(self) -> None:
        """Check for glint issues."""
        if errors := await self.extensions.registration_errors:
            self.error("extensions_registered", errors)
        else:
            self.succeed(
                "extensions_registered",
                ["Registered metadata matches found extensions"])

    async def check_glint(self) -> None:
        """Check for glint issues."""
        await self._code_check(self.glint)

    async def check_gofmt(self) -> None:
        """Check for gofmt issues."""
        await self._code_check(self.gofmt)

    # TODO: catch errors in checkers as well as preloaders
    async def check_python_flake8(self) -> None:
        """Check for flake8 issues."""
        await self._code_check(self.flake8)

    async def check_python_yapf(self) -> None:
        """Check for yapf issues."""
        await self._code_check(self.yapf)

    async def check_runtime_guards(self) -> None:
        """Check for shellcheck issues."""
        async for guard, status in self.runtime_guards.status:
            if status is None:
                self.log.info(f"Ignoring runtime guard: {guard}")
            elif not status:
                self.error(
                    "runtime_guards",
                    [f"Missing from changelogs: {guard}"])
            else:
                self.succeed(
                    "runtime_guards",
                    [f"In changelogs: {guard}"])

    async def check_shellcheck(self) -> None:
        """Check for shellcheck issues."""
        await self._code_check(self.shellcheck)

    async def check_yamllint(self) -> None:
        """Check for yamllint issues."""
        await self._code_check(self.yamllint)

    @checker.preload(
        when=["changelog"],
        catches=[utils.exceptions.ChangelogParseError])
    async def preload_changelog(self) -> None:
        preloader = inflate(
            self.changelog,
            lambda c: (c.errors, ))
        async for changelog in preloader:
            self.log.debug(f"Preloaded changelog: {changelog.version}")

    @checker.preload(
        when=["extensions_fuzzed",
              "extensions_metadata",
              "extensions_registered"],
        catches=[exceptions.ExtensionsConfigurationError])
    async def preload_extensions(self) -> None:
        metadata = await self.extensions.metadata
        self.extensions.extensions_schema
        self.log.debug(f"Preloaded extensions ({len(metadata)})")

    @checker.preload(when=["extensions_owners"])
    async def preload_extensions_owners(self) -> None:
        await self.extensions.owners_errors
        self.log.debug("Preloaded extensions owners")

    @checker.preload(
        when=["python_flake8"],
        catches=[subprocess.exceptions.OSCommandError])
    async def preload_flake8(self) -> None:
        await self.flake8.problem_files

    @checker.preload(
        when=["glint"],
        catches=[subprocess.exceptions.OSCommandError])
    async def preload_glint(self) -> None:
        await self.glint.problem_files

    @checker.preload(
        when=["gofmt"],
        catches=[subprocess.exceptions.OSCommandError])
    async def preload_gofmt(self) -> None:
        await self.gofmt.problem_files

    @checker.preload(
        when=["shellcheck"],
        catches=[subprocess.exceptions.OSCommandError])
    async def preload_shellcheck(self) -> None:
        await self.shellcheck.problem_files

    @checker.preload(
        when=["runtime_guards"],
        catches=[subprocess.exceptions.OSCommandError])
    async def preload_runtime_guards(self) -> None:
        await self.runtime_guards.missing

    @checker.preload(
        when=["yamllint"],
        catches=[
            subprocess.exceptions.OSCommandError,
            YamlLintConfigError])
    async def preload_yamllint(self) -> None:
        await self.yamllint.problem_files

    @checker.preload(
        when=["python_yapf"],
        catches=[subprocess.exceptions.OSCommandError])
    async def preload_yapf(self) -> None:
        await self.yapf.problem_files

    def _check_output(
            self,
            check_files: set[str],
            problem_files: typing.ProblemDict) -> None:
        # This can be slow/blocking for large result sets, run
        # in a separate thread
        for path in sorted(check_files):
            if path not in problem_files:
                self.succeed(
                    self.active_check,
                    [path])
                continue
            if problem_files[path].errors:
                self.error(
                    self.active_check,
                    problem_files[path].errors)
            if problem_files[path].warnings:
                self.warn(
                    self.active_check,
                    problem_files[path].warnings)

    async def _code_check(self, check: "interface.IFileCodeCheck") -> None:
        await self.loop.run_in_executor(
            None,
            self._check_output,
            await check.files,
            await check.problem_files)

    def _grep_re(self, arg: str | None) -> Pattern[str] | None:
        # When using system `grep` we want to filter out at least some
        # of the files that .gitignore would.
        # TODO: use globs on cli and covert to re here
        return (
            re.compile("|".join(arg))
            if arg
            else None)
