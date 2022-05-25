from typing import Callable

import pytest  # type:ignore


def _abstracts():
    # TODO: implemement plugin
    pass


@pytest.fixture
def abstracts() -> Callable:
    return _abstracts
