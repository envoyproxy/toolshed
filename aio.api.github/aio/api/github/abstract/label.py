
import abstracts

from aio.api.github import interface
from .base import GithubRepoEntity


@abstracts.implementer(interface.IGithubLabel)
class AGithubLabel(GithubRepoEntity, metaclass=abstracts.Abstraction):
    """A Github label."""

    def __str__(self):
        return f"<{self.__class__.__name__} {self.name}>"
