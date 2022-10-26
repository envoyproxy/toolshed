
import pathlib
from functools import cached_property
from typing import Tuple, Type

import abstracts

from aio.core import directory

from envoy.base.utils import IProject, Project
from envoy.code.check import abstract, interface


@abstracts.implementer(interface.IExtensionsCheck)
class ExtensionsCheck(abstract.AExtensionsCheck):
    pass


@abstracts.implementer(interface.IFlake8Check)
class Flake8Check(abstract.AFlake8Check):
    pass


@abstracts.implementer(interface.IGlintCheck)
class GlintCheck(abstract.AGlintCheck):
    pass


@abstracts.implementer(interface.IShellcheckCheck)
class ShellcheckCheck(abstract.AShellcheckCheck):
    pass


@abstracts.implementer(interface.IYapfCheck)
class YapfCheck(abstract.AYapfCheck):
    pass


@abstracts.implementer(abstract.AYamllintCheck)
class YamllintCheck:
    pass


@abstracts.implementer(interface.IRSTCheck)
class BackticksCheck(abstract.ABackticksCheck):
    pass


@abstracts.implementer(interface.IRSTCheck)
class PunctuationCheck(abstract.APunctuationCheck):
    pass


@abstracts.implementer(interface.IRSTCheck)
class ReflinksCheck(abstract.AReflinksCheck):
    pass


@abstracts.implementer(interface.IRuntimeGuardsCheck)
class RuntimeGuardsCheck(abstract.ARuntimeGuardsCheck):
    pass


@abstracts.implementer(interface.IChangelogChangesChecker)
class ChangelogChangesChecker(abstract.AChangelogChangesChecker):

    @cached_property
    def change_checkers(self) -> Tuple[interface.IRSTCheck, ...]:
        return (
            BackticksCheck(),
            PunctuationCheck(),
            ReflinksCheck())


@abstracts.implementer(interface.IChangelogStatus)
class ChangelogStatus(abstract.AChangelogStatus):
    pass


@abstracts.implementer(interface.IChangelogCheck)
class ChangelogCheck(abstract.AChangelogCheck):

    @property
    def changes_checker_class(
            self) -> Type[interface.IChangelogChangesChecker]:
        return ChangelogChangesChecker

    @property
    def changelog_status_class(self) -> Type[interface.IChangelogStatus]:
        return ChangelogStatus


@abstracts.implementer(interface.ICodeChecker)
class CodeChecker(abstract.ACodeChecker):

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

    @property
    def yamllint_class(self):
        return YamllintCheck
