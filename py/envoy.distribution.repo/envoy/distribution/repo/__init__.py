
import warnings

from .abstract import ARepoBuildingRunner, ARepoManager, ReleaseConfigDict
from .exceptions import RepoError
from .runner import RepoBuildingRunner
from .cmd import DEPRECATION_MESSAGE, cmd, main
from .deb import (
    AAptly, AptlyError,
    DebRepoError, DebRepoManager)

warnings.warn(
    DEPRECATION_MESSAGE,
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
