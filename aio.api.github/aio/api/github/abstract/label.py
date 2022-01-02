
import abstracts

from .base import GithubRepoEntity


class AGithubLabel(GithubRepoEntity, metaclass=abstracts.Abstraction):
    """A Github label."""

    def __str__(self):
        return f"<{self.__class__.__name__} {self.name}>"
