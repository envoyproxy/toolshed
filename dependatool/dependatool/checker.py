#!/usr/bin/env python3

import pathlib
from functools import cached_property
from typing import Type

import abstracts

from aio.core import directory

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

    @property
    def directory_class(self) -> Type[directory.ADirectory]:
        return directory.GitDirectory
