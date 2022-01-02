
from datetime import datetime
from functools import cached_property

import abstracts

from aio.api.github import utils
from .base import GithubRepoEntity


class AGithubCommit(GithubRepoEntity, metaclass=abstracts.Abstraction):
    """A Github commit."""

    def __str__(self):
        return f"<{self.__class__.__name__} {self.repo.name}#{self.sha}>"

    @cached_property
    def timestamp(self) -> datetime:
        """Datetime of the commit."""
        return utils.dt_from_js_isoformat(
            self.data["commit"]["committer"]["date"])
