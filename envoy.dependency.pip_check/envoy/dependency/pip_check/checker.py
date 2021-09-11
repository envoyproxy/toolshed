#!/usr/bin/env python3

import pathlib
from functools import cached_property

import abstracts


from .abstract import APipChecker


@abstracts.implementer(APipChecker)
class PipChecker:

    @cached_property
    def path(self) -> pathlib.Path:
        return super().path
