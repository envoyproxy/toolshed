
import asyncio
import logging
import pathlib
import re
import shutil
import types
from collections.abc import ItemsView, Iterator, KeysView, ValuesView
from datetime import datetime, timezone
from functools import cached_property
from typing import cast

from frozendict import frozendict
import jinja2
from packaging import version as _version
import yaml as _yaml

import abstracts

from aio.core.functional import async_property

from envoy.base import utils
from envoy.base.utils import exceptions, interface, typing


logger = logging.getLogger(__name__)


CHANGELOG_PATH_GLOB = "changelogs/*.*.*.yaml"
CHANGELOG_PATH_FMT = "changelogs/{version}.yaml"
CHANGELOG_CURRENT_PATH = "changelogs/current.yaml"
CHANGELOG_CURRENT_DIR_PATH = "changelogs/current"
CHANGELOG_ENTRY_GLOB = "*/*.rst"
CHANGELOG_CONFIG_PATH = "changelogs/changelogs.yaml"
ENTRY_SEPARATOR = "__"
CHANGELOG_SUMMARY_PATH = "changelogs/summary.md"
CHANGELOG_ENTRY_URL_TPL = (
    "https://raw.githubusercontent.com/envoyproxy/envoy/"
    f"v{{version}}/{CHANGELOG_CURRENT_DIR_PATH}/{{path}}")
CHANGELOG_CURRENT_TPL = """
date: Pending
{% for section, description in sections.items() %}
{{ section }}:
{% if description %}# {{ description }}{% endif -%}
{% endfor %}
"""
DATE_FORMAT = "%B %-d, %Y"

# These are for parsing pre 1.23 rst changelogs and can be removed when that is
# no longer required
RST_CHANGELOG_URL_TPL = (
    "https://raw.githubusercontent.com/envoyproxy/envoy/"
    "v{version}/docs/root/version_history/current.rst")
OLD_CHANGELOG_SECTIONS = frozendict({
    "Incompatible Behavior Changes": "behavior_changes",
    "Minor Behavior Changes": "minor_behavior_changes",
    "Bug Fixes": "bug_fixes",
    "Removed Config or Runtime": "removed_config_or_runtime",
    "New Features": "new_features",
    "Deprecated": "deprecated"})
YAML_CHANGELOGS_VERSION = "1.23"


class LegacyChangelog:
    # Parser for changelogs < 1.23.0

    def __init__(self, content: str) -> None:
        self.content = content

    @property
    def changelog(self) -> dict[str, typing.ChangeList]:
        changelog: dict[str, typing.ChangeList] = {}
        current_section = None
        for line in self.lines[1:]:
            if line in OLD_CHANGELOG_SECTIONS:
                current_section = OLD_CHANGELOG_SECTIONS[line]
                changelog[current_section] = []
                continue
            if not current_section:
                continue
            if line.startswith("* "):
                changelog[current_section].append(self._parse_line(line))
            elif line.startswith(" "):
                changelog[current_section][-1]["change"] += f"\n{line[2:]}"
        return changelog

    @property
    def data(self) -> typing.ChangelogDict:
        return utils.typed(
            typing.ChangelogDict,
            dict(date=self.date, **self.changelog))

    @property
    def date(self) -> str:
        return self.lines[0].split("(")[1].strip(")")

    @cached_property
    def lines(self) -> list[str]:
        return self.content.split("\n")

    def _parse_line(self, line: str) -> typing.ChangeDict:
        area, change = line[2:].split(":", 1)
        return dict(
            area=area,
            change=typing.Change(change.lstrip(" ")))


@abstracts.implementer(interface.IChangelogEntry)
class AChangelogEntry(metaclass=abstracts.Abstraction):

    def __init__(self, section: str, entry: typing.ChangeDict) -> None:
        self.section = section
        self.entry = entry

    def __gt__(self, other: interface.IChangelogEntry) -> bool:
        if self.area > other.area:
            return True
        if self.change > other.change:
            return True
        return False

    def __lt__(self, other: interface.IChangelogEntry) -> bool:
        return not self.__gt__(other)

    @property
    def area(self) -> str:
        return self.entry["area"]

    @property
    def change(self) -> str:
        return self.entry["change"]


@abstracts.implementer(interface.IChangelog)
class AChangelog(metaclass=abstracts.Abstraction):

    @classmethod
    def data_from_entry_map(
            cls,
            entries: dict[str, str]) -> "typing.ChangelogDict":
        sections: dict[str, list[typing.ChangeDict]] = {}
        for entry_path, text in sorted(entries.items()):
            path = pathlib.Path(entry_path)
            if path.stem.count(ENTRY_SEPARATOR) != 1:
                raise exceptions.ChangelogParseError(
                    f"Invalid entry filename "
                    f"(expected exactly one '{ENTRY_SEPARATOR}'): "
                    f"{entry_path}")
            area, _slug = path.stem.split(ENTRY_SEPARATOR, 1)
            change = typing.Change(text)
            entry: typing.ChangeDict = dict(area=area, change=change)
            sections.setdefault(path.parent.name, []).append(entry)
        return cast(
            typing.ChangelogDict,
            dict(date="Pending", **sections))

    @classmethod
    def get_data(cls, path) -> typing.ChangelogDict:
        try:
            data = utils.from_yaml(path, typing.ChangelogSourceDict)
        except (_yaml.reader.ReaderError, utils.TypeCastingError) as e:
            raise exceptions.ChangelogParseError(
                f"Failed to parse: {path}\n{e}")
        return cast(
            typing.ChangelogDict,
            {k: (v
                 if k == "date"
                 else [dict(area=c["area"],
                            change=typing.Change(c["change"]))
                       for c
                       in v])
             for k, v
             in data.items()
             if v})

    @classmethod
    def get_data_from_entries(
            cls,
            entry_dir: pathlib.Path) -> "typing.ChangelogDict":
        return cls.data_from_entry_map({
            f"{path.parent.name}/{path.name}": path.read_text()
            for path
            in sorted(entry_dir.glob(CHANGELOG_ENTRY_GLOB))})

    def __init__(
            self,
            project,
            version: _version.Version,
            path: pathlib.Path) -> None:
        self.project = project
        self._version = version
        self._path = path

    @property
    def base_version(self) -> str:
        return self.version.base_version

    @async_property(cache=True)
    async def data(self) -> typing.ChangelogDict:
        changelogs = self.project.changelogs
        if changelogs.entries_layout and self._is_current:
            parsed = await self.project.execute(
                self.get_data_from_entries,
                changelogs.current_dir_path)
        else:
            parsed = await self.project.execute(self.get_data, self.path)
        return changelogs.validate_sections(parsed, self.path)

    @property
    @abstracts.interfacemethod
    def entry_class(self) -> type[interface.IChangelogEntry]:
        raise NotImplementedError

    @property
    def path(self) -> pathlib.Path:
        return self._path

    @async_property
    async def release_date(self) -> str:
        return cast(str, (await self.data)["date"])

    @property
    def version(self) -> _version.Version:
        return self._version

    @property
    def _is_current(self) -> bool:
        return self.version == self.project.changelogs.current

    async def entries(self, section: str) -> list[interface.IChangelogEntry]:
        return sorted(
            self.entry_class(section, entry)
            for entry
            in (await self.data)[section])  # type:ignore


@abstracts.implementer(interface.IChangelogs)
class AChangelogs(metaclass=abstracts.Abstraction):

    def __init__(self, project: interface.IProject) -> None:
        self.project = project

    def __contains__(self, version: _version.Version) -> bool:
        return self.changelogs.__contains__(version)

    def __getitem__(self, k: _version.Version) -> interface.IChangelog:
        return self.changelogs.__getitem__(k)

    def __iter__(self) -> Iterator[_version.Version]:
        for k in self.changelogs:
            yield k

    @property
    @abstracts.interfacemethod
    def changelog_class(self) -> type[interface.IChangelog]:
        raise NotImplementedError

    @cached_property
    def changelog_paths(self) -> typing.ChangelogPathsDict:
        if self.entries_layout:
            historical_paths = self.project.path.glob(CHANGELOG_PATH_GLOB)
            current_version = _version.Version(
                self.project.version.base_version)
            return {
                **{
                    self._version_from_path(path): path
                    for path
                    in historical_paths},
                current_version: self.current_dir_path}
        return {
            self._version_from_path(path): path
            for path
            in self.paths}

    @cached_property
    def changelogs(self) -> typing.ChangelogsDict:
        return {
            k: self.changelog_class(
                self.project,
                k,
                (self.current_path
                 if self.entries_layout and self.project.is_current(k)
                 else self.changelog_paths[k]),)
            for k
            in reversed(sorted(self.changelog_paths.keys()))}

    @cached_property
    def current(self) -> _version.Version:
        return next(iter(self.changelogs))

    @property
    def current_path(self) -> pathlib.Path:
        return self.project.path.joinpath(self.rel_current_path)

    @property
    def current_dir_path(self) -> pathlib.Path:
        return self.project.path.joinpath(self.rel_current_dir_path)

    @cached_property
    def current_tpl(self) -> jinja2.Template:
        return jinja2.Template(CHANGELOG_CURRENT_TPL)

    @property
    def date_format(self) -> str:
        return DATE_FORMAT

    @property
    def datestamp(self) -> str:
        return datetime.now(tz=timezone.utc).date().strftime(self.date_format)

    @async_property
    async def is_pending(self) -> bool:
        if self.entries_layout:
            return self.project.is_dev
        return (
            await self[self.current].release_date
            == "Pending")

    @property
    def paths(self) -> tuple[pathlib.Path, ...]:
        paths = self.project.path.glob(CHANGELOG_PATH_GLOB)
        return (
            (*paths, self.current_dir_path)
            if self.entries_layout
            else (*paths, self.current_path))

    @property
    def rel_current_path(self) -> pathlib.Path:
        return pathlib.Path(CHANGELOG_CURRENT_PATH)

    @property
    def rel_current_dir_path(self) -> pathlib.Path:
        return pathlib.Path(CHANGELOG_CURRENT_DIR_PATH)

    @cached_property
    def section_re(self) -> re.Pattern[str]:
        return re.compile(r"\n[a-z_]*:")

    @cached_property
    def config(self) -> typing.ChangelogConfigDict:
        try:
            return utils.from_yaml(
                self.config_path,
                typing.ChangelogConfigDict)
        except _yaml.reader.ReaderError as e:
            raise exceptions.ChangelogError(
                "Failed to parse changelog config "
                f"({self.config_path}): {e}")
        except utils.TypeCastingError as e:
            logger.warning(
                "Changelog config parsing error: "
                f"({self.config_path})\n{e}")
            return cast(typing.ChangelogConfigDict, e.value)

    @cached_property
    def sections(self) -> typing.ChangelogSectionsDict:
        return self.config["sections"]

    @cached_property
    def areas(self) -> typing.ChangelogAreasDict:
        return self.config["areas"]

    def validate_sections(
            self,
            data: typing.ChangelogDict,
            path: pathlib.Path | None = None) -> typing.ChangelogDict:
        """Validate changelog sections loaded from any parse source.

        This should be called for every parsed `ChangelogDict`, whether
        parsed from a YAML changelog file or assembled from per-entry
        changelog data.

        :param data: Parsed changelog data to validate.
        :param path: Optional source path for error context.
        :returns: The input data, unchanged.
        :raises ChangelogParseError: If any section key is unknown.
        """
        allowed = set(self.sections) | {"date"}
        unknown = sorted(k for k in data if k not in allowed)
        if unknown:
            where = f" ({path})" if path is not None else ""
            raise exceptions.ChangelogParseError(
                f"Unknown changelog section(s){where}: "
                f"{', '.join(unknown)}. "
                f"Valid sections come from {CHANGELOG_CONFIG_PATH}.")
        return data

    @property
    def config_path(self) -> pathlib.Path:
        return self.project.path.joinpath(CHANGELOG_CONFIG_PATH)

    @property
    def summary_path(self) -> pathlib.Path:
        return self.project.path.joinpath(CHANGELOG_SUMMARY_PATH)

    @cached_property
    def yaml(self) -> types.ModuleType:
        _yaml.add_representer(typing.Change, self.yaml_change_presenter)
        return _yaml

    def blank_summary(self) -> None:
        self.summary_path.write_text("")

    def changelog_path(self, version: _version.Version) -> pathlib.Path:
        return self.project.path.joinpath(self.rel_changelog_path(version))

    def changes_for_commit(self, change: typing.ProjectChangeDict) -> set[str]:
        changed = set()
        if any(k in change for k in ["release", "dev"]):
            if not self.entries_layout:
                changed.add(CHANGELOG_CURRENT_PATH)
        if "dev" in change:
            changed.add(self.rel_changelog_path(change["dev"]["old_version"]))
            changed.add(str(self.summary_path))
        changelog = change.get("sync", {}).get("changelog", {})
        for version, sync in changelog.items():
            if sync:
                changed.add(self.rel_changelog_path(version))
        if self.entries_layout:
            changed.add(CHANGELOG_CURRENT_DIR_PATH)
        return changed

    def dump_yaml(self, data: typing.ChangelogDict) -> str:
        output = self.yaml.dump(
            {k: v
             for k, v
             in data.items()
             if v},
            default_flow_style=False,
            default_style=None,
            sort_keys=False)
        for section in self.section_re.findall(output):
            output = output.replace(section, f"\n{section}")
        return (
            f"{output}\n"
            if not output.endswith("\n")
            else output)

    async def fetch(self, release) -> str:
        version = release.version
        if self._is_rst_changelog(version):
            return self.dump_yaml(LegacyChangelog(
                await (
                    await self.project.session.get(
                        RST_CHANGELOG_URL_TPL.format(
                            version=version.base_version))).text()).data)
        data = self.changelog_class.data_from_entry_map(
            await self._fetch_entries(version))
        data["date"] = release.published_at.date().strftime(self.date_format)
        return self.dump_yaml(data)

    def items(self) -> ItemsView[_version.Version, interface.IChangelog]:
        return self.changelogs.items()

    def keys(self) -> KeysView[_version.Version]:
        return self.changelogs.keys()

    def rel_changelog_path(self, version) -> str:
        return CHANGELOG_PATH_FMT.format(version=version.base_version)

    def should_sync(self, version: _version.Version) -> bool:
        return (
            version < self.project.version
            and version >= self.project.stable_versions[-1]
            and version not in self)

    async def sync(self) -> typing.SyncResultDict:
        change: typing.SyncResultDict = {}
        async for release in self.project.repo.releases():
            if self.should_sync(release.version):
                self.write_changelog(
                    release.version,
                    await self.fetch(release))
                change[release.version] = True
        return change

    def values(self) -> ValuesView[interface.IChangelog]:
        return self.changelogs.values()

    def write_changelog(self, version: _version.Version, text: str) -> None:
        self.changelog_path(version).write_text(text)

    def write_current(self) -> None:
        if self.entries_layout:
            self.current_dir_path.mkdir(parents=True, exist_ok=True)
        else:
            sections = {
                k: v.get("description")
                for k, v
                in self.sections.items()
                if k != "changes"}
            self.current_path.write_text(
                self.current_tpl.render(sections=sections).lstrip())

    async def write_date(self, date: str) -> None:
        if not await self.is_pending:
            raise exceptions.ReleaseError(
                "Current changelog date is not set to `Pending`")
        if self.entries_layout:
            return
        else:
            data = (await self[self.current].data).copy()
            data["date"] = date
            self.current_path.write_text(self.dump_yaml(data))

    def write_version(self, version: _version.Version) -> None:
        if (version_file := self.changelog_path(version)).exists():
            raise exceptions.DevError(
                f"Version file ({version_file}) already exists")
        if self.entries_layout:
            data = self.changelog_class.get_data_from_entries(
                self.current_dir_path)
            data["date"] = self.datestamp
            version_file.write_text(self.dump_yaml(data))
            shutil.rmtree(self.current_dir_path)
            self.current_dir_path.mkdir()
        else:
            version_file.write_text(
                self.current_path.read_text())

    def yaml_change_presenter(
            self,
            dumper: _yaml.Dumper,
            data: typing.Change) -> _yaml.ScalarNode:
        normal = data.rstrip("\n")
        return dumper.represent_scalar(
            'tag:yaml.org,2002:str',
            f"{normal}\n",
            style='|')

    @cached_property
    def _yaml_changelogs_version(self) -> _version.Version:
        return _version.Version(YAML_CHANGELOGS_VERSION)

    @property
    def entries_layout(self) -> bool:
        return (
            self.project.path.joinpath(CHANGELOG_CURRENT_DIR_PATH).is_dir())

    def _is_rst_changelog(self, version: _version.Version) -> bool:
        return version < self._yaml_changelogs_version

    async def _fetch_entries(
            self,
            version: _version.Version) -> dict[str, str]:
        tree = await self.project.repo.getitem(
            f"git/trees/v{version.base_version}:{CHANGELOG_CURRENT_DIR_PATH}"
            "?recursive=1")
        entry_paths = [
            item["path"]
            for item
            in tree.get("tree", [])
            if item["type"] == "blob" and item["path"].endswith(".rst")]

        async def _fetch_entry(path: str) -> tuple[str, str]:
            return (
                path,
                await (
                    await self.project.session.get(
                        CHANGELOG_ENTRY_URL_TPL.format(
                            version=version.base_version,
                            path=path))).text())

        return dict(
            await asyncio.gather(
                *(_fetch_entry(path)
                  for path
                  in entry_paths)))

    def _version_from_path(self, path: pathlib.Path) -> _version.Version:
        return _version.Version(
            path.stem
            if path.stem != "current"
            else self.project.version.base_version)
