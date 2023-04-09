
import os
import re
from functools import cached_property
from typing import Iterable, Pattern

import abstracts

from aio.core.functional import async_property

from dependatool import ADependatoolCheck


GOMODFILE_FILENAME = "go.mod"


@abstracts.implementer(ADependatoolCheck)
class ADependatoolGomodCheck(object):
    _gomodfile_filename = GOMODFILE_FILENAME

    def __init__(self, checker):
        self.checker = checker

    @cached_property
    def config(self) -> set:
        """Set of configured gomod dependabot directories."""
        return set(
            update['directory']
            for update in self.checker.config["updates"]
            if update["package-ecosystem"] == "gomod")

    @async_property(cache=True)
    async def gomodfile_dirs(self) -> set[str]:
        """Set of found directories in the repo containing a go.mod file."""
        return set(
            os.path.dirname(f"/{f}")
            for f in await self.checker.directory.files
            if self.dir_matches(f))

    @property
    def gomodfile_filename(self) -> Pattern[str]:
        return re.compile(self._gomodfile_filename)

    async def check(self, files=None):
        """Check that dependabot config matches gomodfile.txt files found in
        repo."""
        missing_dirs = self.config.difference(
            await self.gomodfile_dirs)
        missing_config = (await self.gomodfile_dirs).difference(
            self.config)
        correct = (await self.gomodfile_dirs).intersection(
            self.config)
        if correct:
            self.success(correct)
        if missing_dirs:
            self.errors(
                missing_dirs,
                (f"No {self.gomodfile_filename.pattern} found for specified "
                 "dependabot config"))
        if missing_config:
            self.errors(
                missing_config,
                ("Missing dependabot config for "
                 f"{self.gomodfile_filename.pattern} in dir"))

    def dir_matches(self, path: str) -> bool:
        """For given file path, check if its a gomodfile file and whether its
        parent directory is excluded."""
        return (
            bool(self.gomodfile_filename.match(os.path.basename(path)))
            and os.stat(path).st_size > 1
            and not self.checker.ignored_dirs.match(
                os.path.dirname(f"/{path}")))

    def errors(self, missing: Iterable, msg: str) -> None:
        for dirname in sorted(missing):
            self.checker.error("gomod", [f"{msg}: {dirname}"])

    def success(self, correct: Iterable) -> None:
        self.checker.succeed(
            "gomod",
            ([f"{self.gomodfile_filename.pattern}: {dirname}"
              for dirname in sorted(correct)]))
