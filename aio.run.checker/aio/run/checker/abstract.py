
import abstracts

from aio.run.checker import interface


@abstracts.implementer(interface.IProblems)
class AProblems(metaclass=abstracts.Abstraction):

    def __init__(
            self,
            errors: list[str] | None = None,
            warnings: list[str] | None = None) -> None:
        self._errors = errors
        self._warnings = warnings

    @property
    def errors(self) -> list[str]:
        return self._errors or []

    @property
    def warnings(self) -> list[str]:
        return self._warnings or []
