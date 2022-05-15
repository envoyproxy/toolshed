
import pytest

import abstracts

from envoy.base.utils import interface


@abstracts.implementer(interface.IProject)
class DummyProject:

    @property
    def archived_versions(self):
        return interface.IProject.archived_versions.fget(self)

    @property
    def changelogs(self):
        return interface.IProject.changelogs.fget(self)

    @property
    def changelogs_class(self):
        return interface.IProject.changelogs_class.fget(self)

    @property
    def dev_version(self):
        return interface.IProject.dev_version.fget(self)

    @property
    def inventories(self):
        return interface.IProject.inventories.fget(self)

    @property
    def inventories_class(self):
        return interface.IProject.inventories_class.fget(self)

    @property
    def is_dev(self):
        return interface.IProject.is_dev.fget(self)

    @property
    def is_main_dev(self):
        return interface.IProject.is_main_dev.fget(self)

    @property
    def minor_version(self):
        return interface.IProject.minor_version.fget(self)

    @property
    def minor_versions(self):
        return interface.IProject.minor_versions.fget(self)

    @property
    def path(self):
        return interface.IProject.path.fget(self)

    @property
    def rel_version_path(self):
        return interface.IProject.rel_version_path.fget(self)

    @property
    def repo(self):
        return interface.IProject.repo.fget(self)

    @property
    def session(self):
        return interface.IProject.session.fget(self)

    @property
    def stable_versions(self):
        return interface.IProject.stable_versions.fget(self)

    @property
    def version(self):
        return interface.IProject.version.fget(self)

    async def commit(self):
        return await interface.IProject.commit(self)

    async def dev(self):
        return await interface.IProject.dev(self)

    def is_current(self, version):
        return interface.IProject.is_current(self, version)

    async def release(self):
        return await interface.IProject.release(self)

    async def sync(self):
        return await interface.IProject.sync(self)


async def test_iface_project_constructor():
    with pytest.raises(TypeError):
        interface.IProject()

    project = DummyProject()

    iface_props = [
        "archived_versions", "changelogs", "changelogs_class",
        "dev_version", "is_dev", "is_main_dev",
        "inventories", "inventories_class",
        "minor_version", "minor_versions", "path",
        "rel_version_path", "repo",
        "session", "stable_versions", "version"]

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(project, prop)

    iface_async_methods = [
        "commit", "dev",
        "sync", "release"]

    for method in iface_async_methods:
        with pytest.raises(NotImplementedError):
            await getattr(project, method)()


async def test_iface_project_is_current():
    project = DummyProject()

    with pytest.raises(NotImplementedError):
        project.is_current("VERSION")


@abstracts.implementer(interface.IInventories)
class DummyInventories:

    def __iter__(self):
        return interface.IInventories.__iter__(self)

    def __getitem__(self, k):
        return interface.IInventories.__getitem__(self, k)

    @property
    def inventories(self):
        return interface.IInventories.inventories.fget(self)

    @property
    def paths(self):
        return interface.IInventories.paths.fget(self)

    @property
    def versions(self):
        return interface.IInventories.versions.fget(self)

    @property
    def versions_path(self):
        return interface.IInventories.versions_path.fget(self)

    def changes_for_commit(self, update):
        return interface.IInventories.changes_for_commit(self, update)

    async def sync(self):
        return await interface.IInventories.sync(self)


async def test_iface_inventories_constructor():
    with pytest.raises(TypeError):
        interface.IInventories()

    inventories = DummyInventories()

    iface_props = [
        "inventories", "paths", "versions", "versions_path"]

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(inventories, prop)

    iface_methods = [
        "__iter__"]

    for method in iface_methods:
        with pytest.raises(NotImplementedError):
            getattr(inventories, method)()

    iface_async_methods = ["sync"]

    for method in iface_async_methods:
        with pytest.raises(NotImplementedError):
            await getattr(inventories, method)()


async def test_iface_inventories_dunder_getitem():
    inventories = DummyInventories()

    with pytest.raises(NotImplementedError):
        inventories.__getitem__("K")


async def test_iface_inventories_changes_for_commit():
    inventories = DummyInventories()

    with pytest.raises(NotImplementedError):
        inventories.changes_for_commit("CHANGE")


@abstracts.implementer(interface.IChangelogs)
class DummyChangelogs:

    def __iter__(self):
        return interface.IChangelogs.__iter__(self)

    def __getitem__(self, k):
        return interface.IChangelogs.__getitem__(self, k)

    @property
    def changelog_class(self):
        return interface.IChangelogs.changelog_class.fget(self)

    @property
    def changelog_paths(self):
        return interface.IChangelogs.changelog_paths.fget(self)

    @property
    def changelogs(self):
        return interface.IChangelogs.changelogs.fget(self)

    @property
    def current(self):
        return interface.IChangelogs.current.fget(self)

    @property
    def date_format(self):
        return interface.IChangelogs.date_format.fget(self)

    @property
    def datestamp(self):
        return interface.IChangelogs.datestamp.fget(self)

    @property
    def is_pending(self):
        return interface.IChangelogs.is_pending.fget(self)

    @property
    def sections(self):
        return interface.IChangelogs.sections.fget(self)

    def changes_for_commit(self, update):
        return interface.IChangelogs.changes_for_commit(self, update)

    def items(self):
        return interface.IChangelogs.items(self)

    def keys(self):
        return interface.IChangelogs.keys(self)

    async def sync(self):
        return await interface.IChangelogs.sync(self)

    def values(self):
        return interface.IChangelogs.values(self)

    def write_current(self) -> None:
        return interface.IChangelogs.write_current(self)

    def write_date(self):
        return interface.IChangelogs.write_date(self)

    def write_version(self, version):
        return interface.IChangelogs.write_date(self, version)


async def test_iface_changelogs_constructor():
    with pytest.raises(TypeError):
        interface.IChangelogs()

    changelogs = DummyChangelogs()

    iface_props = [
        "changelog_class", "changelog_paths", "changelogs",
        "current", "date_format", "datestamp", "is_pending", "sections"]

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(changelogs, prop)

    iface_methods = [
        "__iter__", "items", "keys", "values",
        "write_current", "write_date"]

    for method in iface_methods:
        with pytest.raises(NotImplementedError):
            getattr(changelogs, method)()

    iface_async_methods = ["sync"]

    for method in iface_async_methods:
        with pytest.raises(NotImplementedError):
            await getattr(changelogs, method)()


async def test_iface_changelogs_dunder_getitem():
    changelogs = DummyChangelogs()

    with pytest.raises(NotImplementedError):
        changelogs.__getitem__("K")


async def test_iface_changelogs_changes_for_commit():
    changelogs = DummyChangelogs()

    with pytest.raises(NotImplementedError):
        changelogs.changes_for_commit("CHANGE")


async def test_iface_changelogs_write_version():
    changelogs = DummyChangelogs()

    with pytest.raises(NotImplementedError):
        changelogs.write_version("VERSION")


@abstracts.implementer(interface.IChangelog)
class DummyChangelog:

    @property
    def data(self):
        return interface.IChangelog.data.fget(self)

    @property
    def entry_class(self):
        return interface.IChangelog.entry_class.fget(self)

    @property
    def path(self):
        return interface.IChangelog.path.fget(self)

    @property
    def release_date(self):
        return interface.IChangelog.release_date.fget(self)

    @property
    def version(self):
        return interface.IChangelog.version.fget(self)

    def entries(self, section):
        return interface.IChangelog.entries(self, section)


def test_iface_changelog_constructor():
    with pytest.raises(TypeError):
        interface.IChangelog()

    changelog = DummyChangelog()

    iface_props = [
        "data", "entry_class", "path", "release_date", "version"]

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(changelog, prop)


async def test_iface_changelog_entries():
    changelog = DummyChangelog()

    with pytest.raises(NotImplementedError):
        changelog.entries("SECTION")


@abstracts.implementer(interface.IChangelogEntry)
class DummyChangelogEntry:

    def __gt__(self, other):
        return interface.IChangelogEntry.__gt__(self, other)

    def __lt__(self, other):
        return interface.IChangelogEntry.__lt__(self, other)

    @property
    def area(self):
        return interface.IChangelogEntry.area.fget(self)

    @property
    def change(self):
        return interface.IChangelogEntry.change.fget(self)


def test_iface_changelogentry_constructor():
    with pytest.raises(TypeError):
        interface.IChangelogEntry()

    changelog = DummyChangelogEntry()

    iface_props = [
        "area", "change"]

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(changelog, prop)


def test_iface_changelogentry_dunder_ltgt():
    changelog = DummyChangelogEntry()

    for method in ["__lt__", "__gt__"]:
        with pytest.raises(NotImplementedError):
            getattr(changelog, method)(changelog)
