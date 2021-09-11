#!/usr/bin/env python3

import pathlib
from functools import cached_property

import abstracts


from .abstract import APythonChecker


@abstracts.implementer(APythonChecker)
class PythonChecker:

    @cached_property
    def path(self) -> pathlib.Path:
        return super().path
