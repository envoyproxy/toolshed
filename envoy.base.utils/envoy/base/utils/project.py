
import abstracts

from aio.core import directory

from envoy.base.utils import abstract, interface


@abstracts.implementer(interface.IChangelogEntry)
class ChangelogEntry(abstract.AChangelogEntry):
    pass


@abstracts.implementer(interface.IChangelog)
class Changelog(abstract.AChangelog):

    @property
    def entry_class(self) -> type[interface.IChangelogEntry]:
        return ChangelogEntry


@abstracts.implementer(interface.IChangelogs)
class Changelogs(abstract.AChangelogs):

    @property
    def changelog_class(self) -> type[interface.IChangelog]:
        return Changelog


@abstracts.implementer(interface.IInventories)
class Inventories(abstract.AInventories):
    pass


@abstracts.implementer(interface.IProject)
class Project(abstract.AProject):

    @property
    def changelogs_class(self) -> type[interface.IChangelogs]:
        return Changelogs

    @property
    def directory_class(self) -> type[directory.ADirectory]:
        return directory.GitDirectory

    @property
    def inventories_class(self) -> type[interface.IInventories]:
        return Inventories
