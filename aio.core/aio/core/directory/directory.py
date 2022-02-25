
from typing import Type

import abstracts

from aio.core import directory


@abstracts.implementer(directory.ADirectory)
class Directory:

    @property
    def directory_grepper_class(self) -> Type[directory.ADirectoryGrepper]:
        return DirectoryGrepper


@abstracts.implementer(directory.ADirectoryGrepper)
class DirectoryGrepper:
    pass


@abstracts.implementer(directory.AGitDirectory)
class GitDirectory:

    @property
    def directory_grepper_class(self) -> Type[directory.ADirectoryGrepper]:
        return DirectoryGrepper
