
import pathlib
from functools import cached_property
from typing import Iterable

import abstracts

from dependatool import ADependatoolCheck


REQUIREMENTS_FILENAME = "requirements.txt"


@abstracts.implementer(ADependatoolCheck)
class ADependatoolPipCheck(object):
    _requirements_filename = REQUIREMENTS_FILENAME

    def __init__(self, checker):
        self.checker = checker

    @cached_property
    def config(self) -> set:
        """Set of configured pip dependabot directories."""
        return set(
            update['directory']
            for update in self.checker.config["updates"]
            if update["package-ecosystem"] == "pip")

    @cached_property
    def requirements_dirs(self) -> set[str]:
        """Set of found directories in the repo containing requirements.txt."""
        return set(
            f"/{f.parent.relative_to(self.checker.path)}"
            for f in self.checker.path.glob("**/*")
            if self.dir_matches(f))

    @property
    def requirements_filename(self) -> str:
        return self._requirements_filename

    async def check(self, files=None):
        """Check that dependabot config matches requirements.txt files found in
        repo."""
        missing_dirs = self.config.difference(
            self.requirements_dirs)
        missing_config = self.requirements_dirs.difference(
            self.config)
        correct = self.requirements_dirs.intersection(
            self.config)
        if correct:
            self.success(correct)
        if missing_dirs:
            self.errors(
                missing_dirs,
                (f"Missing {self.requirements_filename} dir, specified in "
                 "dependabot config"))
        if missing_config:
            self.errors(
                missing_config,
                (f"Missing dependabot config for {self.requirements_filename} "
                 "in dir"))

    def dir_matches(self, path: pathlib.Path) -> bool:
        """For given file path, check if its a requirements file and whether
        its parent directory is excluded."""
        return (
            path.name == self.requirements_filename
            and not self.checker.ignored_dirs.match(
                f"/{path.parent.relative_to(self.checker.path)}"))

    def errors(self, missing: Iterable, msg: str) -> None:
        for dirname in sorted(missing):
            self.checker.error("pip", [f"{msg}: {dirname}"])

    def success(self, correct: Iterable) -> None:
        self.checker.succeed(
            "pip",
            ([f"{self.requirements_filename}: {dirname}"
              for dirname in sorted(correct)]))
