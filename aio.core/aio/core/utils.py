
import contextlib
import warnings as _warnings
from typing import Any, Iterable, Iterator, Optional


def dottedname_resolve(name, module=None):
    """Resolve ``name`` to a Python object via imports / attribute lookups.

    Lifted from `zope.dottedname.resolve`.

    If ``module`` is None, ``name`` must be "absolute" (no leading dots).

    If ``module`` is not None, and ``name`` is "relative" (has leading dots),
    the object will be found by navigating relative to ``module``.

    Returns the object, if found.  If not, propagates the error.
    """
    name = name.split('.')
    if not name[0]:
        if module is None:
            raise ValueError("relative name without base module")
        module = module.split('.')
        name.pop(0)
        while not name[0]:
            module.pop()
            name.pop(0)
        name = module + name

    used = name.pop(0)
    found = __import__(used)
    for n in name:
        used += '.' + n
        try:
            found = getattr(found, n)
        except AttributeError:
            __import__(used)
            found = getattr(found, n)

    return found


class Captured:
    result: Optional[Any] = None
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
