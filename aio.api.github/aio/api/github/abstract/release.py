
from functools import cached_property
from typing import Callable, Dict, Union

from packaging import version

import abstracts

from aio.api.github import interface, utils
from .base import GithubRepoEntity


@abstracts.implementer(interface.IGithubRelease)
class AGithubRelease(GithubRepoEntity, metaclass=abstracts.Abstraction):
    """A Github release."""

    def __str__(self):
        return f"<{self.__class__.__name__} {self.repo.name}@{self.tag_name}>"

    @cached_property
    def __data__(self) -> Dict[str, Callable]:
        return dict(
            created_at=utils.dt_from_js_isoformat,
            published_at=utils.dt_from_js_isoformat)

    @cached_property
    def version(self) -> Union[version.LegacyVersion, version.Version]:
        return version.parse(self.tag_name)

    @property
    def tag_name(self):
        return self.data["tag_name"]
