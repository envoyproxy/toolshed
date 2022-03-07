
from typing import Type

import abstracts

from .abstract import AAspellAPI


@abstracts.implementer(AAspellAPI)
class AspellAPI:

    def __init__(self, *args, **kwargs) -> None:
        AAspellAPI.__init__(self, *args, **kwargs)
