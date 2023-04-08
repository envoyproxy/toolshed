
import os
import re
from functools import cached_property
from typing import Iterable, Pattern

import abstracts

from aio.core.functional import async_property

from dependatool import ADependatoolCheck


DOCKERFILE_FILENAME = "Dockerfile*"


@abstracts.implementer(ADependatoolCheck)
class ADependatoolDockerCheck(object):
    _dockerfile_filename = DOCKERFILE_FILENAME

    def __init__(self, checker):
        self.checker = checker

    @cached_property
    def config(self) -> set:
        """Set of configured docker dependabot directories."""
        return set(
            update['directory']
            for update in self.checker.config["updates"]
            if update["package-ecosystem"] == "docker")

    @async_property(cache=True)
    async def dockerfile_dirs(self) -> set[str]:
        """Set of found directories in the repo containing dockerfile.txt."""
        return set(
            os.path.dirname(f"/{f}")
            for f in await self.checker.directory.files
            if self.dir_matches(f))

    @property
    def dockerfile_filename(self) -> Pattern[str]:
        return re.compile(self._dockerfile_filename)

    async def check(self, files=None):
        """Check that dependabot config matches dockerfile.txt files found in
        repo."""
        missing_dirs = self.config.difference(
            await self.dockerfile_dirs)
        missing_config = (await self.dockerfile_dirs).difference(
            self.config)
        correct = (await self.dockerfile_dirs).intersection(
            self.config)
        if correct:
            self.success(correct)
        if missing_dirs:
            self.errors(
                missing_dirs,
                (f"No {self.dockerfile_filename.pattern} found for specified "
                 "dependabot config"))
        if missing_config:
            self.errors(
                missing_config,
                ("Missing dependabot config for "
                 f"{self.dockerfile_filename.pattern} in dir"))

    def dir_matches(self, path: str) -> bool:
        """For given file path, check if its a dockerfile file and whether its
        parent directory is excluded."""
        return (
            bool(self.dockerfile_filename.match(os.path.basename(path)))
            and not self.checker.ignored_dirs.match(
                os.path.dirname(f"/{path}")))

    def errors(self, missing: Iterable, msg: str) -> None:
        for dirname in sorted(missing):
            self.checker.error("docker", [f"{msg}: {dirname}"])

    def success(self, correct: Iterable) -> None:
        self.checker.succeed(
            "docker",
            ([f"{self.dockerfile_filename.pattern}: {dirname}"
              for dirname in sorted(correct)]))
