
import contextlib
import warnings as _warnings
from typing import Any, Iterable, Iterator


class Captured:
    result: Any = None
    warnings: Iterable[_warnings.WarningMessage] = ()

    def __str__(self) -> str:
        return f"{self._warning_str}\n{self.result or ''}".strip()

    @property
    def _warning_str(self) -> str:
        return "\n".join(
            str(warning.message)
            for warning
            in self.warnings).strip()


@contextlib.contextmanager
def captured_warnings() -> Iterator[Captured]:
    captured = Captured()
    with _warnings.catch_warnings(record=True) as w:
        yield captured
    captured.warnings = w
