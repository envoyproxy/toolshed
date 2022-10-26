
from typing import List, Optional

import abstracts

from aio.run.checker import interface


@abstracts.implementer(interface.IProblems)
class AProblems(metaclass=abstracts.Abstraction):

    def __init__(
            self,
            errors: Optional[List[str]] = None,
            warnings: Optional[List[str]] = None) -> None:
        self._errors = errors
        self._warnings = warnings

    @property
    def errors(self) -> List[str]:
        return self._errors or []

    @property
    def warnings(self) -> List[str]:
        return self._warnings or []
