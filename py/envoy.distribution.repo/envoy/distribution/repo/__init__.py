
import warnings

from .abstract import ARepoBuildingRunner, ARepoManager, ReleaseConfigDict
from .exceptions import RepoError
from .runner import RepoBuildingRunner
from .cmd import cmd, main
from .deb import (
    AAptly, AptlyError,
    DebRepoError, DebRepoManager)

warnings.warn(
    ("envoy.distribution.repo is deprecated and no longer maintained. "
     "Do not use."),
    DeprecationWarning,
    stacklevel=2)


__all__ = (
    "AAptly",
    "AptlyError",
    "ARepoBuildingRunner",
    "ARepoManager",
    "cmd",
    "DebRepoError",
    "DebRepoManager",
    "main",
    "ReleaseConfigDict",
    "RepoBuildingRunner",
    "RepoError")
