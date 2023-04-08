from .resolve import dottedname
from .context import Captured, captured_warnings


dottedname_resolve = dottedname


__all__ = (
    "Captured",
    "captured_warnings",
    "dottedname",
    "dottedname_resolve")
