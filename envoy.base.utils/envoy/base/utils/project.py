
from typing import Type

import abstracts

from envoy.base.utils import abstract, interface


@abstracts.implementer(interface.IChangelogEntry)
class ChangelogEntry(abstract.AChangelogEntry):
    pass


@abstracts.implementer(interface.IChangelog)
class Changelog(abstract.AChangelog):

    @property
    def entry_class(self) -> Type[interface.IChangelogEntry]:
        return ChangelogEntry


@abstracts.implementer(interface.IChangelogs)
class Changelogs(abstract.AChangelogs):

    @property
    def changelog_class(self) -> Type[interface.IChangelog]:
        return Changelog


@abstracts.implementer(interface.IInventories)
class Inventories(abstract.AInventories):
    pass


@abstracts.implementer(interface.IProject)
class Project(abstract.AProject):

    @property
    def changelogs_class(self) -> Type[interface.IChangelogs]:
        return Changelogs

    @property
    def inventories_class(self) -> Type[interface.IInventories]:
        return Inventories
