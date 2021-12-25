
import abstracts

from aio.functional import async_property

from .base import GithubRepoEntity


class AGithubTag(GithubRepoEntity, metaclass=abstracts.Abstraction):

    @property
    def commit_url(self):
        """URL to retrieve related commit for this tag."""
        # this is messy 8/
        try:
            url = self.data["object"]["url"]
        except KeyError:
            url = self.data["url"]
        return url.replace("git/commits", "commits")

    @async_property(cache=True)
    async def commit(self):
        """Related commit for this tag."""
        return self.github.commit_class(
            self.github,
            await self.github.getitem(self.commit_url))
