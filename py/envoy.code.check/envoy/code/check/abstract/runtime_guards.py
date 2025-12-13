#
import re
from functools import cached_property
from typing import (
    AsyncIterator, Awaitable, Iterable, Pattern)

import abstracts

from aio.core.functional import async_property

from envoy.code.check import abstract, interface


EXPECTED_MISSING_GUARDS = (
    "envoy_reloadable_features_admin_stats_filter_use_re2",
    "envoy_reloadable_features_allow_multiple_dns_addresses",
    "envoy_reloadable_features_get_route_config_factory_by_type",
    "envoy_reloadable_features_internal_address",
    "envoy_reloadable_features_local_ratelimit_match_all_descriptors",
    "envoy_reloadable_features_postpone_h3_client_connect_to_next_loop",
    "envoy_reloadable_features_test_feature_true")
RELOADABLE_GUARD_GREP_RE = r"^RUNTIME_GUARD\(envoy_reloadable"
RELOADABLE_MATCH_RE = r"``envoy.reloadable[._][a-z0-9_.]+``"
RUNTIME_GUARDS_CONFIG_PATH = "source/common/runtime/runtime_features.cc"


@abstracts.implementer(interface.IRuntimeGuardsCheck)
class ARuntimeGuardsCheck(
        abstract.AProjectCodeCheck,
        metaclass=abstracts.Abstraction):
    """Runtime guards check."""

    @async_property(cache=True)
    async def configured(self) -> set[str]:
        return set(
            line.split(":")[1][14:-2]
            for line
            in await self._grepped)

    @cached_property
    def expected_missing(self) -> set[str]:
        return set(EXPECTED_MISSING_GUARDS)

    @async_property
    async def mentioned(self) -> set[str]:
        mentioned = set()
        async for change in self._changes:
            mentioned |= self._find_mention(change)
        return mentioned

    @async_property(cache=True)
    async def missing(self) -> set[str]:
        return set(
            await self.configured
            - await self.mentioned
            - self.expected_missing)

    @cached_property
    def reloadable_match_re(self) -> Pattern:
        return re.compile(RELOADABLE_MATCH_RE)

    @async_property
    async def status(self) -> AsyncIterator[tuple[str, bool | None]]:
        for guard in sorted(await self.configured):
            if guard in await self.missing:
                yield guard, False
            elif guard in self.expected_missing:
                yield guard, None
            else:
                yield guard, True

    @async_property
    async def _changes(self) -> AsyncIterator[str]:
        for changelog in self.project.changelogs.values():
            for section, data in (await changelog.data).items():
                if section == "date":
                    continue
                for change in data:
                    yield change["change"]

    @property
    def _grepped(self) -> Awaitable[Iterable[str]]:
        return self.directory.grep(
            ["-E", RELOADABLE_GUARD_GREP_RE],
            RUNTIME_GUARDS_CONFIG_PATH)

    def _find_mention(self, change: str) -> set[str]:
        return set(
            m.strip("`").replace(".", "_")
            for m
            in self.reloadable_match_re.findall(change))
