from collections.abc import Callable, Iterable
from typing import Any

import pytest  # type:ignore


def _dict_item(x: int) -> tuple[str, str]:
    return f"K{x}", f"V{x}"


def _iters_mapping(
        sequence: type[dict],
        count: int,
        start: int,
        cb: Callable[[int], Any] | None = None) -> Iterable:
    return sequence(
        (cb or _dict_item)(x)
        for x
        in range(start, start + count))


def _item(x: int) -> str:
    return f"I{x}"


def _iters(
        sequence: type[dict | list | tuple | set] = list,
        count: int = 5,
        start: int = 0,
        cb: Callable[[int], Any] | None = None) -> Iterable:
    if issubclass(sequence, dict):
        return _iters_mapping(sequence, count, start, cb)
    return sequence(
        (cb or _item)(x)
        for x
        in range(start, start + count))


@pytest.fixture
def iters() -> Callable[..., Iterable]:
    return _iters
