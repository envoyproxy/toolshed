
import abstracts

from aio.core.functional import async_property


class ADependatoolCheck(metaclass=abstracts.Abstraction):

    @async_property
    async def files(self):
        pass

    async def check(self, files=None):
        pass
