
import pathlib
from functools import cached_property
from typing import Tuple, Type

import abstracts

from aio.core import directory

from envoy.base.utils import IProject, Project
from envoy.code import check


@abstracts.implementer(check.AExtensionsCheck)
class ExtensionsCheck:
    pass


@abstracts.implementer(check.AFlake8Check)
class Flake8Check:
    pass


@abstracts.implementer(check.AGlintCheck)
class GlintCheck:
    pass


@abstracts.implementer(check.AShellcheckCheck)
class ShellcheckCheck:
    pass


@abstracts.implementer(check.AYapfCheck)
class YapfCheck:
    pass


@abstracts.implementer(check.interface.IRSTCheck)
class BackticksCheck(check.ABackticksCheck):
    pass


@abstracts.implementer(check.interface.IRSTCheck)
class PunctuationCheck(check.APunctuationCheck):
    pass


@abstracts.implementer(check.interface.IRSTCheck)
class ReflinksCheck(check.AReflinksCheck):
    pass


@abstracts.implementer(check.ARuntimeGuardsCheck)
class RuntimeGuardsCheck:
    pass


@abstracts.implementer(check.AChangelogChangesChecker)
class ChangelogChangesChecker:

    @cached_property
    def change_checkers(self) -> Tuple[check.interface.IRSTCheck, ...]:
        return (
            BackticksCheck(),
            PunctuationCheck(),
            ReflinksCheck())


@abstracts.implementer(check.AChangelogStatus)
class ChangelogStatus:
    pass


@abstracts.implementer(check.AChangelogCheck)
class ChangelogCheck:

    @property
    def changes_checker_class(self) -> Type[check.AChangelogChangesChecker]:
        return ChangelogChangesChecker

    @property
    def changelog_status_class(self) -> Type[check.AChangelogStatus]:
        return ChangelogStatus


@abstracts.implementer(check.ACodeChecker)
class CodeChecker:

    @property
    def extensions_class(self):
        return ExtensionsCheck

    @property
    def flake8_class(self):
        return Flake8Check

    @property
    def fs_directory_class(self):
        return directory.Directory

    @property
    def git_directory_class(self):
        return directory.GitDirectory

    @property
    def glint_class(self):
        return GlintCheck

    @cached_property
    def path(self) -> pathlib.Path:
        return super().path

    @property
    def project_class(self) -> Type[IProject]:
        return Project

    @property
    def runtime_guards_class(self):
        return RuntimeGuardsCheck

    @property
    def shellcheck_class(self):
        return ShellcheckCheck

    @property
    def changelog_class(self):
        return ChangelogCheck

    @property
    def yapf_class(self):
        return YapfCheck
