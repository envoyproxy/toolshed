#!/usr/bin/env python3

import pathlib
from functools import cached_property

import abstracts

from .abstract import ADependatoolChecker
from .pip import DependatoolPipCheck


@abstracts.implementer(ADependatoolChecker)
class DependatoolChecker:

    @cached_property
    def path(self) -> pathlib.Path:
        return super().path

    @cached_property
    def check_tools(self):
        return dict(pip=DependatoolPipCheck(self))
