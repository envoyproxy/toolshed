
import itertools
from datetime import datetime
from functools import cached_property
from typing import Iterator, Optional, Tuple, Type

from packaging import version as _version

import abstracts

from aio.core.functional import async_property

from envoy.base import utils
from envoy.code.check import abstract, interface


MAX_VERSION_FOR_CHANGES_SECTION = "1.16"


@abstracts.implementer(interface.IChangelogChangesChecker)
class AChangelogChangesChecker(metaclass=abstracts.Abstraction):
    error_message = (
        "{version}/{section}/{entry[area]}: "
        "{error}\n{entry[change]}")

    def __init__(
            self,
            sections: utils.typing.ChangelogSectionsDict) -> None:
        self.sections = sections

    @property  # type:ignore
    @abstracts.interfacemethod
    def change_checkers(self) -> Tuple[interface.IRSTCheck, ...]:
        raise NotImplementedError

    @cached_property
    def max_version_for_changes_section(self) -> _version.Version:
        return _version.Version(MAX_VERSION_FOR_CHANGES_SECTION)

    def check_entry(
            self,
            version: _version.Version,
            section: str,
            entry: utils.typing.ChangeDict) -> Tuple[str, ...]:
        change = entry["change"].strip()
        errors = [
            checker(change)
            for checker
            in self.change_checkers]
        return tuple(
            self.error_message.format(
                version=version,
                section=section,
                entry=entry,
                error=error)
            for error
            in errors
            if error)

    def check_section(
            self,
            version: _version.Version,
            section: str,
            data: Optional[utils.typing.ChangeList]) -> Tuple[str, ...]:
        name_error = self.check_section_name(version, section)
        return (
            *((name_error, )
              if name_error
              else ()),
            *itertools.chain.from_iterable(
                self.check_entry(version, section, entry)
                for entry
                in data or []))

    def check_sections(
            self,
            version: _version.Version,
            sections: utils.typing.ChangelogChangeSectionsDict) -> (
                Tuple[str, ...]):
        return tuple(
            itertools.chain.from_iterable(
                self.check_section(version, section, data)  # type:ignore
                for section, data
                in sections.items()))

    def check_section_name(
            self,
            version: _version.Version,
            section: str) -> Optional[str]:
        invalid_changes = (
            section == "changes"
            and version > self.max_version_for_changes_section)
        if invalid_changes:
            return (
                f"{version}/changes: Invalid `changes` section "
                "(this is no longer used)")


@abstracts.implementer(interface.IChangelogStatus)
class AChangelogStatus(metaclass=abstracts.Abstraction):

    def __init__(
            self,
            check: interface.IChangelogCheck,
            changelog: utils.interface.IChangelog) -> None:
        self._check = check
        self.changelog = changelog

    @property
    def checker(self) -> interface.IChangelogChangesChecker:
        return self._check.changes_checker

    @async_property
    async def data(self) -> utils.typing.ChangelogDict:
        return await self.changelog.data

    @async_property
    async def date(self) -> str:
        return (await self.data)["date"]

    @cached_property
    def date_format(self) -> str:
        return self.project.changelogs.date_format.replace("-", "")

    @async_property
    async def dev_not_pending(self) -> bool:
        return (
            self.is_current
            and self.project.is_dev
            and not await self.is_pending)

    @property
    def duplicate_current(self) -> bool:
        return (
            self.is_current
            and self.project.changelogs.changelog_path(
                self.version).exists())

    @async_property(cache=True)
    async def errors(self) -> Tuple[str, ...]:
        try:
            return (
                *self.check_version(),
                *await self.check_date(),
                *await self.check_sections())
        except utils.exceptions.ChangelogParseError as e:
            return (f"{self.version}: {e}", )

    @async_property
    async def invalid_date(self) -> Optional[str]:
        if await self.is_pending:
            return None
        date = await self.date
        try:
            datetime.strptime(date, self.date_format)
        except ValueError:
            return date

    @cached_property
    def is_current(self) -> bool:
        return self.project.is_current(self.version)

    @async_property
    async def is_pending(self) -> bool:
        return (await self.date) == "Pending"

    @async_property
    async def pending_not_dev(self) -> bool:
        return (
            (not self.is_current
             or not self.project.is_dev)
            and await self.is_pending)

    @property
    def project(self) -> utils.interface.IProject:
        return self._check.project

    @async_property
    async def sections(self) -> utils.typing.ChangelogChangeSectionsDict:
        return utils.typed(
            utils.typing.ChangelogChangeSectionsDict,
            {k: v
             for k, v
             in (await self.data).items()
             if k != "date"})

    @property
    def version(self) -> _version.Version:
        return self.changelog.version

    @property
    def version_higher_than_current(self) -> bool:
        return (
            self.version
            > _version.Version(self.project.version.base_version))

    async def check_date(self) -> Tuple[str, ...]:
        errors = []
        if invalid_date := await self.invalid_date:
            errors.append(f"Format not recognized \"{invalid_date}\"")
        if await self.dev_not_pending:
            errors.append("Should be set to `Pending`")
        elif await self.pending_not_dev:
            errors.append("Should not be set to `Pending`")
        return tuple(
            f"{self.version}/date: {e}"
            for e
            in errors)

    async def check_sections(self) -> Tuple[str, ...]:
        # Runs checker in executor, uncomment following line for debugging
        # return self.checker.check_sections(self.version, await self.sections)
        return await self.project.execute(
            self.checker.check_sections,
            self.version,
            await self.sections)

    def check_version(self) -> Tuple[str, ...]:
        errors = []
        if self.duplicate_current:
            errors.append(
                "Duplicate current version file. "
                "Only `current.yaml` should exist for the current version "
                f"({self.project.version.base_version})")
        elif self.version_higher_than_current:
            errors.append(
                "Changelog version is higher than "
                f"the current version ({self.project.version.base_version})")
        return tuple(
            f"{self.version}: {e}"
            for e
            in errors)


@abstracts.implementer(interface.IChangelogCheck)
class AChangelogCheck(
        abstract.AProjectCodeCheck,
        metaclass=abstracts.Abstraction):
    """Changelog check."""

    def __iter__(self) -> Iterator[interface.IChangelogStatus]:
        for changelog in self.changelogs:
            yield changelog

    @property  # type:ignore
    @abstracts.interfacemethod
    def changes_checker_class(
            self) -> Type[interface.IChangelogChangesChecker]:
        raise NotImplementedError

    @cached_property
    def changes_checker(self) -> interface.IChangelogChangesChecker:
        return self.changes_checker_class(
            self.project.changelogs.sections)

    @property  # type:ignore
    @abstracts.interfacemethod
    def changelog_status_class(self) -> Type[interface.IChangelogStatus]:
        raise NotImplementedError

    @cached_property
    def changelogs(self) -> Tuple[interface.IChangelogStatus, ...]:
        return tuple(
            self.changelog_status_class(self, changelog)
            for changelog
            in self.project.changelogs.values())
