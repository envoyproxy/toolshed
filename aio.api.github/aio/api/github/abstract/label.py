
import abstracts

from .base import GithubRepoEntity


class AGithubLabel(GithubRepoEntity, metaclass=abstracts.Abstraction):
    """A Github label."""
    pass
