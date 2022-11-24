
import io
import pathlib
import re
from functools import cached_property, partial
from typing import (
    AsyncIterator, Dict, Generator, Iterator, List, Optional,
    Pattern, Set, Tuple)

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
YAMLLINT_MATCH_RE = (
    r"[\w/\.]*\.yml$",
    r"[\w/\.]*\.yaml$", )
YAMLLINT_NOMATCH_RE = (
    r"[\w/\.]*\.template\.yaml$",
    r"[\w/\.]*/server_xds\.cds\.with_unknown_field\.*\.yaml$")


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
            result: Generator) -> Optional[
                "typing.YamllintProblemTuple"]:
        if problems := self._parse_problems(path, result):
            return (
                (path,
                 checker.Problems(
                     errors=problems.get("error"),
                     warnings=problems.get("warning"))))

    def run_check(
            self,
            path: str) -> Optional[
                "typing.YamllintProblemTuple"]:
        with io.open(path, newline='') as f:
            return self.handle_result(
                path,
                linter.run(f, self.config, path))

    @debug.logging(
        log=__name__,
        show_cpu=True)
    def run_checks(self) -> Tuple["typing.YamllintProblemTuple", ...]:
        """Run Yamllint checks."""
        return tuple(self.check_results)

    def _parse_problems(
            self,
            path: str,
            problems: Generator) -> Dict[str, List[str]]:
        problem_dict: Dict[str, List[str]] = {}
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
            *args) -> Tuple["typing.YamllintProblemTuple", ...]:
        return YamllintFilesCheck(root_path, config, *args).run_checks()

    @async_property
    async def checker_files(self) -> Set[str]:
        """Files with a `.yaml` suffix, but that are not excluded."""
        return set(
            path
            for path
            in await self.directory.files
            if (self.path_match_re.match(path)
                and not self.path_match_exclude_re.match(path)))

    @cached_property
    def config(self) -> YamlLintConfig:
        return YamlLintConfig(file=self.config_path)

    @property
    def config_path(self) -> pathlib.Path:
        return self.directory.path.joinpath(YAMLLINT_CONFIG)

    @cached_property
    def path_match_re(self) -> Pattern[str]:
        """Regex to match files to check."""
        return re.compile("|".join(YAMLLINT_MATCH_RE))

    @cached_property
    def path_match_exclude_re(self) -> Pattern[str]:
        """Regex to match files not to check."""
        return re.compile("|".join(YAMLLINT_NOMATCH_RE))

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
                self.config),
            *await self.files)

        async for batch in batches:
            for problems in batch:
                yield problems
