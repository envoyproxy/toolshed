from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, ExitStack
from unittest.mock import patch

import pytest  # type:ignore


@contextmanager
def nested(*contexts) -> Iterator[tuple]:
    with ExitStack() as stack:
        yield tuple(stack.enter_context(context) for context in contexts)


def _patches(*args: str, prefix: str = "") -> AbstractContextManager[tuple]:
    """Takes a list of module/class paths to patch and an optional prefix.

    The prefix is used to prefix all of the paths

    The patches are applied in a nested set of context managers.

    The yields (mocks) are yielded as a tuple.
    """
    patched = []
    prefix = f"{prefix}." if prefix else ""
    for arg in args:
        if isinstance(arg, (list, tuple)):
            path, kwargs = arg
            patched.append(patch(f"{prefix}{path}", **kwargs))
        else:
            patched.append(patch(f"{prefix}{arg}"))
    return nested(*patched)


@pytest.fixture
def patches() -> Callable[..., AbstractContextManager[tuple]]:
    return _patches
