
import abstracts

from aio.functional import async_property

from aio.api.github import abstract
from .base import GithubRepoEntity


class AGithubTag(GithubRepoEntity, metaclass=abstracts.Abstraction):

    def __str__(self):
        return f"<{self.__class__.__name__} {self.repo.name}@{self.tag}>"

    @async_property(cache=True)
    async def commit(self) -> "abstract.AGithubCommit":
        """Related commit for this tag."""
        return await self.repo.commit(self.object["sha"])
