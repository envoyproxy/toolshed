
import pathlib
from functools import cached_property

import abstracts

from .abstract import ABazel, ABazelEnv, ABazelQuery, ABazelRun


@abstracts.implementer(ABazel)
class Bazel:

    @cached_property
    def bazel_path(self) -> pathlib.Path:
        return super().bazel_path

    @cached_property
    def path(self) -> pathlib.Path:
        return super().path


@abstracts.implementer(ABazelEnv)
class BazelEnv(Bazel):

    @property
    def bazel_query_class(self) -> type["ABazelQuery"]:
        return BazelQuery

    @property
    def bazel_run_class(self) -> type["ABazelRun"]:
        return BazelRun


@abstracts.implementer(ABazelQuery)
class BazelQuery(Bazel):
    pass


@abstracts.implementer(ABazelRun)
class BazelRun(Bazel):
    pass
