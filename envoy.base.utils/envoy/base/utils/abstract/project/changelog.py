
import pathlib
import re
import types
from functools import cached_property
from typing import (
    Dict, ItemsView, Iterator, KeysView,
    List, Pattern, Set, Tuple, Type, ValuesView)

from frozendict import frozendict
import jinja2
from packaging import version as _version
import yaml as _yaml

import abstracts

from envoy.base import utils
from envoy.base.utils import exceptions, interface, typing


CHANGELOG_PATH_GLOB = "changelogs/*.*.*.yaml"
CHANGELOG_PATH_FMT = "changelogs/{version}.yaml"
CHANGELOG_CURRENT_PATH = "changelogs/current.yaml"
CHANGELOG_SECTIONS_PATH = "changelogs/sections.yaml"
CHANGELOG_URL_TPL = (
    "https://raw.githubusercontent.com/envoyproxy/envoy/"
    "v{version}/changelogs/current.yaml")
CHANGELOG_CURRENT_TPL = """
date: Pending
{% for section, description in sections.items() %}
{{ section }}:
{% if description %}# {{ description }}{% endif -%}
{% endfor %}
"""

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
    def changelog(self) -> Dict[str, typing.ChangeList]:
        changelog: Dict[str, typing.ChangeList] = {}
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
    def lines(self) -> List[str]:
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

    def __init__(self, version: _version.Version, path: pathlib.Path) -> None:
        self._version = version
        self._path = path

    @property
    def base_version(self) -> str:
        return self.version.base_version

    @cached_property
    def data(self) -> typing.ChangelogDict:
        try:
            data = utils.from_yaml(self.path, typing.ChangelogSourceDict)
        except (_yaml.reader.ReaderError, utils.TypeCastingError) as e:
            raise exceptions.ChangelogError(
                f"Failed to parse changelog ({self.path}): {e}")
        return utils.typed(
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

    @property  # type:ignore
    @abstracts.interfacemethod
    def entry_class(self) -> Type[interface.IChangelogEntry]:
        raise NotImplementedError

    @property
    def path(self) -> pathlib.Path:
        return self._path

    @property
    def release_date(self) -> str:
        return self.data["date"]

    @property
    def version(self) -> _version.Version:
        return self._version

    def entries(self, section: str) -> List[interface.IChangelogEntry]:
        return sorted(
            self.entry_class(section, entry)
            for entry
            in self.data[section])  # type:ignore


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

    @property  # type:ignore
    @abstracts.interfacemethod
    def changelog_class(self) -> Type[interface.IChangelog]:
        raise NotImplementedError

    @cached_property
    def changelog_paths(self) -> typing.ChangelogPathsDict:
        return {
            self._version_from_path(path): path
            for path
            in self.paths}

    @cached_property
    def changelogs(self) -> typing.ChangelogsDict:
        return {
            k: self.changelog_class(k, self.changelog_paths[k])
            for k
            in reversed(sorted(self.changelog_paths.keys()))}

    @cached_property
    def current(self) -> _version.Version:
        return next(iter(self.changelogs))

    @property
    def current_path(self) -> pathlib.Path:
        return self.project.path.joinpath(self.rel_current_path)

    @cached_property
    def current_tpl(self) -> jinja2.Template:
        return jinja2.Template(CHANGELOG_CURRENT_TPL)

    @property
    def is_pending(self) -> bool:
        return (
            self[self.current].release_date
            == "Pending")

    @property
    def paths(self) -> Tuple[pathlib.Path, ...]:
        return (
            *self.project.path.glob(CHANGELOG_PATH_GLOB),
            self.current_path)

    @property
    def rel_current_path(self) -> pathlib.Path:
        return pathlib.Path(CHANGELOG_CURRENT_PATH)

    @cached_property
    def section_re(self) -> Pattern:
        return re.compile(r"\n[a-z_]*:")

    @cached_property
    def sections(self) -> typing.ChangelogSectionsDict:
        try:
            return utils.from_yaml(
                self.sections_path,
                typing.ChangelogSectionsDict)
        except (_yaml.reader.ReaderError, utils.TypeCastingError) as e:
            raise exceptions.ChangelogError(
                "Failed to parse changelog sections "
                f"({self.sections_path}): {e}")

    @property
    def sections_path(self) -> pathlib.Path:
        return self.project.path.joinpath(CHANGELOG_SECTIONS_PATH)

    @cached_property
    def yaml(self) -> types.ModuleType:
        _yaml.add_representer(typing.Change, self.yaml_change_presenter)
        return _yaml

    def changelog_path(self, version: _version.Version) -> pathlib.Path:
        return self.project.path.joinpath(self.rel_changelog_path(version))

    def changelog_url(self, version: _version.Version) -> str:
        return (
            RST_CHANGELOG_URL_TPL
            if self._is_rst_changelog(version)
            else CHANGELOG_URL_TPL).format(version=version.base_version)

    def changes_for_commit(self, change: typing.ProjectChangeDict) -> Set[str]:
        changed = set()
        if any(k in change for k in ["release", "dev"]):
            changed.add(CHANGELOG_CURRENT_PATH)
        if "dev" in change:
            changed.add(self.rel_changelog_path(change["dev"]["old_version"]))
        changelog = change.get("sync", {}).get("changelog", {})
        for version, sync in changelog.items():
            if sync:
                changed.add(self.rel_changelog_path(version))
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
        return f"{output}\n"

    async def fetch(self, version: _version.Version) -> str:
        return await (
            await self.project.session.get(self.changelog_url(version))).text()

    def items(self) -> ItemsView[_version.Version, interface.IChangelog]:
        return self.changelogs.items()

    def keys(self) -> KeysView[_version.Version]:
        return self.changelogs.keys()

    def normalize_changelog(
            self,
            version: _version.Version,
            changelog: str) -> str:
        return (
            self.dump_yaml(LegacyChangelog(changelog).data)
            if self._is_rst_changelog(version)
            else changelog)

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
                    await self.fetch(release.version))
                change[release.version] = True
        return change

    def values(self) -> ValuesView[interface.IChangelog]:
        return self.changelogs.values()

    def write_changelog(self, version: _version.Version, text: str) -> None:
        self.changelog_path(version).write_text(
            self.normalize_changelog(version, text))

    def write_current(self) -> None:
        sections = {
            k: v.get("description")
            for k, v
            in self.sections.items()
            if k != "changes"}
        self.current_path.write_text(
            self.current_tpl.render(sections=sections).lstrip())

    def write_date(self, date: str) -> None:
        if not self.is_pending:
            raise exceptions.ReleaseError(
                "Current changelog date is not set to `Pending`")
        data = self[self.current].data.copy()
        data["date"] = date
        self.current_path.write_text(self.dump_yaml(data))

    def write_version(self, version: _version.Version) -> None:
        version_file = self.changelog_path(version)
        if version_file.exists():
            raise exceptions.DevError(
                f"Version file ({version_file}) already exists")
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

    def _is_rst_changelog(self, version: _version.Version) -> bool:
        return version < self._yaml_changelogs_version

    def _version_from_path(self, path: pathlib.Path) -> _version.Version:
        return _version.Version(
            path.stem
            if path.stem != "current"
            else self.project.version.base_version)
