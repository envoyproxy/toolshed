import pathlib
import re
import sys
from functools import cached_property
from typing import Dict, Iterator, List, Pattern, Set, Tuple

import abstracts

from envoy.code.check import abstract

from aio.core.functional import async_property


class ASpellingCheck(abstract.ACodeCheck, metaclass=abstracts.Abstraction):

    @async_property
    async def checker_files(self) -> Set[str]:
        return set()

    @async_property(cache=True)
    async def problem_files(self) -> Dict[str, List[str]]:
        return (
            dict(await self.errors)
            if await self.files
            else {})

    @async_property
    async def errors(self):
        return {}
