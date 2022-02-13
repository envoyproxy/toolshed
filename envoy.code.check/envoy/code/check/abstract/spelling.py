
import argparse
import pathlib
import re
import sys
from functools import cached_property
from typing import Dict, Iterator, List, Pattern, Set, Tuple

import abstracts

from envoy.code.check import abstract

from aio.api import aspell as _aspell
from aio.core.functional import async_property


class ASpellingCheck(abstract.ACodeCheck, metaclass=abstracts.Abstraction):

    @cached_property
    def aspell(self):
        return _aspell.AspellAPI()

    @property
    def config_file_path(self) -> pathlib.Path:
        """Path to a (temporary) build config."""
        return self.build_dir.joinpath("build.yaml")

    @property
    def aspell_args(self) -> List[str]:
        """Command args for aspell."""
        return ()

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)

    async def spellcheck(self, line):
        return await self.aspell.spellcheck(line)

    async def cleanup(self):
        await self.aspell.stop()

    @async_property
    async def checker_files(self) -> Set[str]:
        return set(f for f in await self.directory.files if f.endswith(".cc"))

    @async_property(cache=True)
    async def problem_files(self) -> Dict[str, List[str]]:
        return (
            dict(await self.errors)
            if await self.files
            else {})

    @async_property
    async def errors(self):
        errors = {}

        for file in await self.absolute_paths:
            print(f"Checking {self.directory.relative_path(file)}")
            try:
                file_errors = await self.check_spelling_for_file(file)
            except:
                file_errors = ["failed loading the file"]
                print(f"Failed to check {self.directory.relative_path(file)}")
            if file_errors:
                errors[file] = file_errors
        return errors

    async def check_spelling_for_file(self, file):
        errors = []
        with open(file, "r") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                if not line.strip():
                    continue
                response = await self.spellcheck(line.strip())
                if response:
                    errors.append(response)
        return errors


class ASpellingDictionaryCheck(abstract.ACodeCheck, metaclass=abstracts.Abstraction):

    @async_property
    async def checker_files(self) -> Set[str]:
        return set()

    @async_property(cache=True)
    async def problem_files(self) -> Dict[str, List[str]]:
        return (
            dict(await self.errors)
            if await self.files
            else {})

    @async_property
    async def errors(self):
        return {}
