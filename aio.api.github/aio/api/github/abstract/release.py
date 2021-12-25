
from functools import cached_property
from typing import Callable, Dict, Union

from packaging import version

import abstracts

from aio.api.github import utils
from .base import GithubRepoEntity


class AGithubRelease(GithubRepoEntity, metaclass=abstracts.Abstraction):
    """A Github release."""

    @cached_property
    def __data__(self) -> Dict[str, Callable]:
        return dict(
            created_at=utils.dt_from_js_isoformat,
            published_at=utils.dt_from_js_isoformat)

    @cached_property
    def version(self) -> Union[version.LegacyVersion, version.Version]:
        return version.parse(self.tag_name)
