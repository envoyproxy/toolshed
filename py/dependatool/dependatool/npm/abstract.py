
import os
import re
from functools import cached_property
from typing import Iterable, Pattern

import abstracts

from aio.core.functional import async_property

from dependatool import ADependatoolCheck


NPMFILE_FILENAME = "package.json"


@abstracts.implementer(ADependatoolCheck)
class ADependatoolNPMCheck(object):
    _npmfile_filename = NPMFILE_FILENAME

    def __init__(self, checker):
        self.checker = checker

    @cached_property
    def config(self) -> set:
        """Set of configured NPM dependabot directories."""
        return set(
            update['directory']
            for update in self.checker.config["updates"]
            if update["package-ecosystem"] == "npm")

    @async_property(cache=True)
    async def npmfile_dirs(self) -> set[str]:
        """Set of found directories in the repo containing package.json."""
        return set(
            os.path.dirname(f"/{f}")
            for f in await self.checker.directory.files
            if self.dir_matches(f))

    @property
    def npmfile_filename(self) -> Pattern[str]:
        return re.compile(self._npmfile_filename)

    async def check(self, files=None):
        """Check that dependabot config matches package.json files found in
        repo."""
        missing_dirs = self.config.difference(
            await self.npmfile_dirs)
        missing_config = (await self.npmfile_dirs).difference(
            self.config)
        correct = (await self.npmfile_dirs).intersection(
            self.config)
        if correct:
            self.success(correct)
        if missing_dirs:
            self.errors(
                missing_dirs,
                (f"No {self.npmfile_filename.pattern} found for specified "
                 "dependabot config"))
        if missing_config:
            self.errors(
                missing_config,
                ("Missing dependabot config for "
                 f"{self.npmfile_filename.pattern} in dir"))

    def dir_matches(self, path: str) -> bool:
        """For given file path, check if its a package.json file and whether
        its parent directory is excluded."""
        return (
            bool(self.npmfile_filename.match(os.path.basename(path)))
            and not self.checker.ignored_dirs.match(
                os.path.dirname(f"/{path}")))

    def errors(self, missing: Iterable, msg: str) -> None:
        for dirname in sorted(missing):
            self.checker.error("npm", [f"{msg}: {dirname}"])

    def success(self, correct: Iterable) -> None:
        self.checker.succeed(
            "npm",
            ([f"{self.npmfile_filename.pattern}: {dirname}"
              for dirname in sorted(correct)]))
