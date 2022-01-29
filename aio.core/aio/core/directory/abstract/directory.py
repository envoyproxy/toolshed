
import shutil
from functools import cached_property

import abstracts

from aio.core import subprocess
from aio.core.functional import async_property


class ADirectory(metaclass=abstracts.Abstraction):

    def __init__(
            self,
            path,
            exclude=None,
            exclude_dirs=None,
            path_matcher=None,
            exclude_matcher=None,
            text_only=True):
        self.path = path
        self.path_matcher = path_matcher
        self.exclude_matcher = exclude_matcher
        self.text_only = text_only
        self.exclude = exclude
        self.exclude_dirs = exclude_dirs

    @async_property(cache=True)
    async def files(self):
        files = set()
        async for path in self.grep(["-lE", r""]):
            files.add(path)
        return files

    @cached_property
    def grep_command(self):
        return shutil.which("grep")

    @property
    def grep_exclusions(self):
        return (
            tuple(
                f"--exclude={exclusion}"
                for exclusion
                in self.exclude)
            + tuple(
                f"--exclude-dir={directory}"
                for directory
                in self.exclude_dirs))

    @cached_property
    def grep_args(self):
        return [self.grep_command, "-Ir", *self.grep_exclusions]

    @cached_property
    def subproc_run(self):
        return subprocess.AsyncSubprocessRunner(
            cwd=self.path,
            encoding="utf-8")

    def parse_grep_args(self, args, target):
        args = [*self.grep_args, *args]
        if target is not None:
            args.append(target)
        return args

    async def grep(
            self,
            args,
            target=None,
            exclude_matcher=None):
        command = self.subproc_run(self.parse_grep_args(args, target))
        for path in (await command).stdout.split("\n"):
            if path:
                if not exclude_matcher or not exclude_matcher.match(path):
                    yield path

    async def name_match(
            self,
            path_matcher=None,
            exclude_matcher=None,
            git=False,
            regex=False):
        for path in await self.files:
            if path_matcher.match(path):
                if not exclude_matcher or not exclude_matcher.match(path):
                    yield path


class AGitDirectory(ADirectory):

    def __init__(self, path, changed=None, **kwargs):
        self.changed = changed
        super().__init__(path, **kwargs)

    @cached_property
    def git_command(self):
        return shutil.which("git")

    @cached_property
    def grep_args(self):
        return [self.git_command, "grep", "-I", "--cached"]

    @async_property(cache=True)
    async def files(self):
        files = set()
        async for path in self.grep(["-l", ""]):
            files.add(path)
        return files
