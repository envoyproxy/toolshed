
import io
import pathlib
from functools import cached_property, partial
from typing import (
    AsyncIterator, Generator, Iterator)

import yaml
from yamllint import linter  # type:ignore
from yamllint.config import YamlLintConfig  # type:ignore

import abstracts

from aio.core.dev import debug
from aio.core import directory
from aio.core.functional import (
    async_property,
    AwaitableGenerator)
from aio.run import checker

from envoy.code.check import abstract, typing


YAMLLINT_CONFIG = '.yamllint'


@abstracts.implementer(directory.IDirectoryContext)
class YamllintFilesCheck(directory.ADirectoryContext):

    def __init__(
            self,
            path: str,
            config: YamlLintConfig,
            *args) -> None:
        directory.ADirectoryContext.__init__(self, path)
        self.config = config
        self.args = args

    @property
    def check_results(self) -> Iterator["typing.YamllintProblemTuple"]:
        """Iterate yamllint check results."""
        with self.in_directory:
            for path in self.args:
                if problems := self.run_check(path):
                    yield problems

    def handle_result(
            self,
            path: str,
            result: Generator) -> typing.YamllintProblemTuple | None:
        if problems := self._parse_problems(path, result):
            return (
                (path,
                 checker.Problems(
                     errors=problems.get("error"),
                     warnings=problems.get("warning"))))

    def run_check(
            self,
            path: str) -> typing.YamllintProblemTuple | None:
        with io.open(path, newline='') as f:
            try:
                return self.handle_result(
                    path,
                    linter.run(f, self.config, path))
            except (TypeError, yaml.error.YAMLError) as e:
                raise type(e)(f"{path}: {e.args[0]}", *e.args[1:])

    @debug.logging(
        log=__name__,
        show_cpu=True)
    def run_checks(self) -> tuple["typing.YamllintProblemTuple", ...]:
        """Run Yamllint checks."""
        return tuple(self.check_results)

    def _parse_problems(
            self,
            path: str,
            problems: Generator) -> dict[str, list[str]]:
        problem_dict: dict[str, list[str]] = {}
        for p in problems:
            problem_dict[p.level] = problem_dict.get(p.level, [])
            problem_dict[p.level].append(
                f"{path} ({p.rule} {p.line}:{p.column}): {p.desc}")
        return problem_dict


class AYamllintCheck(abstract.AFileCodeCheck, metaclass=abstracts.Abstraction):

    @classmethod
    def yamllint(
            cls,
            root_path: str,
            config: YamlLintConfig,
            *args) -> tuple["typing.YamllintProblemTuple", ...]:
        return YamllintFilesCheck(root_path, config, *args).run_checks()

    @async_property
    async def checker_files(self) -> set[str]:
        return set(
            path for path
            in await self.directory.files
            if (self.yamllint_config.is_yaml_file(path)
                and not self.yamllint_config.is_file_ignored(path)))

    @cached_property
    def yamllint_config(self) -> YamlLintConfig:
        return YamlLintConfig(file=self.config_path)

    @property
    def config_path(self) -> pathlib.Path:
        return self.directory.path.joinpath(YAMLLINT_CONFIG)

    @async_property(cache=True)
    async def problem_files(self) -> "typing.ProblemDict":
        return dict(await AwaitableGenerator(self._problem_files))

    @async_property
    async def _problem_files(self) -> AsyncIterator[
            "typing.YamllintProblemTuple"]:
        if not await self.files:
            return

        batches = self.execute_in_batches(
            partial(
                self.yamllint,
                str(self.directory.path),
                self.yamllint_config),
            *await self.files)

        async for batch in batches:
            for problems in batch:
                yield problems
