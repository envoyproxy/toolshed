
import pathlib
from functools import cached_property

import abstracts

from aio.core import directory

from envoy.code import check


@abstracts.implementer(check.AFlake8Check)
class Flake8Check:
    pass


@abstracts.implementer(check.AShellcheckCheck)
class ShellcheckCheck:
    pass


@abstracts.implementer(check.AYapfCheck)
class YapfCheck:
    pass


@abstracts.implementer(check.ACodeChecker)
class CodeChecker:

    @property
    def flake8_class(self):
        return Flake8Check

    @property
    def fs_directory_class(self):
        return directory.Directory

    @property
    def git_directory_class(self):
        return directory.GitDirectory

    @cached_property
    def path(self) -> pathlib.Path:
        return super().path

    @property
    def shellcheck_class(self):
        return ShellcheckCheck

    @property
    def yapf_class(self):
        return YapfCheck
