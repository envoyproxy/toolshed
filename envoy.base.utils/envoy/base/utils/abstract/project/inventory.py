
import pathlib
import types
from functools import cached_property
from typing import Iterator, Optional, Set

from packaging import version as _version
import yaml as _yaml

import abstracts

from aio.core.functional import async_property

from envoy.base import utils
from envoy.base.utils import interface, typing


INVENTORY_PATH_GLOB = "docs/inventories/v*.*/objects.inv"
INVENTORY_PATH_FMT = "docs/inventories/v{minor_version}/objects.inv"
INVENTORY_VERSIONS_PATH = "docs/versions.yaml"
INVENTORY_URL_FMT = (
    "https://www.envoyproxy.io/docs/envoy/v{version}/objects.inv")


@abstracts.implementer(interface.IInventories)
class AInventories(metaclass=abstracts.Abstraction):

    def __init__(self, project: interface.IProject) -> None:
        self.project = project

    def __contains__(self, version: _version.Version) -> bool:
        return self.inventories.__contains__(version)

    def __getitem__(self, version: _version.Version) -> pathlib.Path:
        return self.inventories.__getitem__(version)

    def __iter__(self) -> Iterator[_version.Version]:
        for k in self.inventories:
            yield k

    @cached_property
    def inventories(self) -> typing.InventoryDict:
        return {
            _version.Version(path.parent.name[1:]): path
            for path
            in self.paths}

    @property
    def paths(self) -> Iterator[pathlib.Path]:
        return self.project.path.glob(INVENTORY_PATH_GLOB)

    @async_property
    async def syncable(self) -> typing.VersionDict:
        syncable: typing.VersionDict = dict()
        async for release in self.project.repo.releases():
            minor_version = utils.minor_version_for(release.version)
            if self.should_sync(minor_version, release.version):
                syncable[minor_version] = max(
                    release.version,
                    syncable.get(
                        minor_version,
                        _version.Version("0.0")))
        return syncable

    @cached_property
    def versions(self) -> typing.VersionDict:
        return {
            _version.Version(k): _version.Version(v)
            for k, v
            in utils.from_yaml(
                self.versions_path,
                typing.VersionConfigDict).items()}

    @property
    def versions_path(self) -> pathlib.Path:
        return self.project.path.joinpath(INVENTORY_VERSIONS_PATH)

    @cached_property
    def yaml(self) -> types.ModuleType:
        _yaml.add_representer(_version.Version, self.yaml_version_presenter)
        return _yaml

    def changes_for_commit(self, change: typing.ProjectChangeDict) -> Set[str]:
        changed: Set[str] = set()
        if "sync" not in change:
            return changed
        inventory = change["sync"].get("inventory", {})
        for version, sync in inventory.items():
            if sync:
                changed.add(self.rel_inventory_path(version))
        if inventory:
            changed.add(INVENTORY_VERSIONS_PATH)
        return changed

    async def fetch(self, version: _version.Version) -> Optional[bytes]:
        response = await self.project.session.get(self.inventory_url(version))
        return (
            await response.read()
            if response.status != 404
            else None)

    def inventory_path(self, version: _version.Version) -> pathlib.Path:
        return self.project.path.joinpath(self.rel_inventory_path(version))

    def inventory_url(self, version: _version.Version) -> str:
        return INVENTORY_URL_FMT.format(version=version.base_version)

    def rel_inventory_path(self, version: _version.Version) -> str:
        return INVENTORY_PATH_FMT.format(
            minor_version=utils.minor_version_for(version))

    def should_sync(
            self,
            minor_version: _version.Version,
            version: _version.Version) -> bool:
        return (
            version < self.project.version
            and version >= self.project.stable_versions[-1]
            and (self.versions.get(minor_version, _version.Version("0.0"))
                 < version))

    async def sync(self) -> typing.SyncResultDict:
        versions = {}
        syncable = (await self.syncable).items()
        for minor, version in syncable:
            if content := await self.fetch(version):
                self.write_inventory(version, content)
                versions[minor] = version
        if versions:
            self.write_versions(versions)
        return {
            version: minor in versions
            for minor, version
            in syncable}

    def write_inventory(
            self,
            version: _version.Version,
            content: bytes) -> None:
        output_path = self.inventory_path(version)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        output_path.write_bytes(content)

    def write_versions(self, versions: typing.VersionDict) -> None:
        _versions = self.versions.copy()
        _versions.update(versions)
        self.versions_path.write_text(
            self.yaml.dump(
                _versions,
                default_flow_style=False,
                default_style=None,
                sort_keys=False))

    def yaml_version_presenter(
            self,
            dumper: _yaml.Dumper,
            data: _version.Version) -> _yaml.ScalarNode:
        _data = str(data)
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str",
            _data,
            style=('"'
                   if _data.count(".") == 1
                   else None))
