
from typing import Type

from aio.core import directory


class Directory(directory.ADirectory):

    @property
    def finder_class(self) -> Type[directory.ADirectoryFileFinder]:
        return DirectoryFileFinder


class DirectoryFileFinder(directory.ADirectoryFileFinder):
    pass


class GitDirectoryFileFinder(directory.AGitDirectoryFileFinder):
    pass


class GitDirectory(directory.AGitDirectory):

    @property
    def finder_class(self) -> Type[directory.AGitDirectoryFileFinder]:
        return GitDirectoryFileFinder
