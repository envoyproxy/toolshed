from typing import (
    Any, Callable, Dict, Iterable, List,
    Optional, Set, Tuple, Type, Union)

import pytest  # type:ignore


def _dict_item(x: int) -> Tuple[str, str]:
    return f"K{x}", f"V{x}"


def _iters_mapping(
        sequence: Type[Dict],
        count: int,
        start: int,
        cb: Optional[Callable[[int], Any]] = None) -> Iterable:
    return sequence(
        (cb or _dict_item)(x)
        for x
        in range(start, start + count))


def _item(x: int) -> str:
    return f"I{x}"


def _iters(
        sequence: Type[Union[Dict, List, Tuple, Set]] = list,
        count: int = 5,
        start: int = 0,
        cb: Optional[Callable[[int], Any]] = None) -> Iterable:
    if issubclass(sequence, Dict):
        return _iters_mapping(sequence, count, start, cb)
    return sequence(
        (cb or _item)(x)
        for x
        in range(start, start + count))


@pytest.fixture
def iters() -> Callable[..., Iterable]:
    return _iters
