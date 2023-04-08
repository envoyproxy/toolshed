#!/usr/bin/env python3

import pathlib
from functools import cached_property

import abstracts


from .abstract import ADependatool


@abstracts.implementer(ADependatool)
class Dependatool:

    @cached_property
    def path(self) -> pathlib.Path:
        return super().path
