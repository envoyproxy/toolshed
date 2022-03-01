
from typing import Type

import abstracts

from aio.core import directory


@abstracts.implementer(directory.ADirectory)
class Directory:

    @property
    def finder_class(self) -> Type[directory.ADirectoryFileFinder]:
        return DirectoryFileFinder


@abstracts.implementer(directory.ADirectoryFileFinder)
class DirectoryFileFinder:
    pass


@abstracts.implementer(directory.AGitDirectory)
class GitDirectory:

    @property
    def finder_class(self) -> Type[directory.ADirectoryFileFinder]:
        return DirectoryFileFinder
