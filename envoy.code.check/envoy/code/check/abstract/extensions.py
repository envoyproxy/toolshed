
import asyncio
import itertools
import json
import logging
import pathlib
import re
from functools import cached_property
from typing import Any, cast, Dict, List, Pattern, Set, Tuple, Type, Union

import yaml as _yaml

import abstracts

from aio.core.functional import async_property

from envoy.base import utils
from envoy.code.check import abstract, exceptions, typing


logger = logging.getLogger(__name__)


FILTER_NAMES_PATTERN = "NetworkFilterNames::get()"
FUZZ_TEST_PATH = (
    "test/extensions/filters/network/common/fuzz/uber_per_readfilter.cc")
METADATA_PATH = "source/extensions/extensions_metadata.yaml"
METADATA_ONLY_EXTENSIONS = (
    "envoy.filters.network.envoy_mobile_http_connection_manager", )
CONTRIB_METADATA_PATH = "contrib/extensions_metadata.yaml"
EXTENSIONS_SCHEMA = "tools/extensions/extensions_schema.yaml"


class AExtensionsCheck(abstract.ACodeCheck, metaclass=abstracts.Abstraction):
    """Extensions check."""

    def __init__(
            self,
            *args,
            **kwargs) -> None:
        self.extensions_build_config = kwargs.pop("extensions_build_config")
        super().__init__(*args, **kwargs)

    @cached_property
    def all_extensions(self) -> Set[str]:
        return (
            set(self.configured_extensions)
            | set(self.builtin_extensions))

    @async_property
    async def all_fuzzed(self) -> bool:
        return (
            await self.robust_to_downstream_count
            == self.fuzzed_count)

    @property
    def builtin_extensions(self) -> typing.ExtensionsSchemaBuiltinList:
        return self.extensions_schema["builtin"]

    @cached_property
    def configured_extensions(self) -> typing.ConfiguredExtensionsDict:
        return cast(
            typing.ConfiguredExtensionsDict,
            self._from_json(
                self.extensions_build_config,
                typing.ConfiguredExtensionsDict,
                "Failed to parse extensions {path}:\n{e}",
                "Extensions parsing error: {path}:\n{e}"))

    @property
    def extension_categories(self) -> typing.ExtensionsSchemaCategoriesList:
        return self.extensions_schema["categories"]

    @property
    def extension_security_postures(
            self) -> typing.ExtensionsSchemaSecurityPosturesList:
        return self.extensions_schema["security_postures"]

    @property
    def extension_status_values(
            self) -> typing.ExtensionsSchemaStatusValuesList:
        return self.extensions_schema["status_values"]

    @cached_property
    def extensions_schema(self) -> typing.ExtensionsSchemaDict:
        return cast(
            typing.ExtensionsSchemaDict,
            self._from_yaml(
                self.extensions_schema_path,
                typing.ExtensionsSchemaDict,
                "Failed to parse extensions schema {path}:\n{e}",
                "Extensions schema parsing error: {path}:\n{e}"))

    @property
    def extensions_schema_path(self) -> pathlib.Path:
        return self.directory.path.joinpath(EXTENSIONS_SCHEMA)

    @property
    def fuzz_test_path(self) -> pathlib.Path:
        return self.directory.path.joinpath(FUZZ_TEST_PATH)

    @property
    def fuzzed_count(self) -> int:
        # Hack-ish! We only search the first 50 lines to capture the filters
        # in `filterNames()`.
        return len(
            self.fuzzed_filter_names_re.findall(
                "".join(self.fuzz_test_path.read_text().splitlines()[:50])))

    @cached_property
    def fuzzed_filter_names_re(self) -> Pattern:
        return re.compile(FILTER_NAMES_PATTERN)

    @async_property(cache=True)
    async def metadata(self) -> typing.ExtensionsMetadataDict:
        return dict(**await self.metadata_core, **await self.metadata_contrib)

    @async_property
    async def metadata_contrib(self) -> typing.ExtensionsMetadataDict:
        return await self._metadata(self.metadata_contrib_path)

    @property
    def metadata_contrib_path(self) -> pathlib.Path:
        return self.directory.path.joinpath(CONTRIB_METADATA_PATH)

    @async_property
    async def metadata_core(self) -> typing.ExtensionsMetadataDict:
        return await self._metadata(self.metadata_core_path)

    @property
    def metadata_core_path(self) -> pathlib.Path:
        return self.directory.path.joinpath(METADATA_PATH)

    @async_property
    async def metadata_errors(self) -> Dict[str, Tuple[str, ...]]:
        return {
            extension: await self.check_metadata(extension)
            for extension
            in await self.metadata}

    @async_property
    async def metadata_missing(self) -> Set[str]:
        return (
            self.all_extensions
            - set(await self.metadata))

    @async_property
    async def metadata_only(self) -> Set[str]:
        return (
            set(await self.metadata)
            - self.metadata_only_extensions
            - self.all_extensions)

    @property
    def metadata_only_extensions(self) -> Set[str]:
        return set(METADATA_ONLY_EXTENSIONS)

    @async_property
    async def registration_errors(self) -> List[str]:
        return [
            *[f"Metadata for unused extension found: {extension}"
              for extension
              in sorted(await self.metadata_only)],
            *[f"Metadata missing for extension: {extension}"
              for extension
              in sorted(await self.metadata_missing)]]

    @async_property
    async def robust_to_downstream_count(self) -> int:
        # Count number of network filters robust to untrusted downstreams.
        return len([
            ext
            for ext, data
            in (await self.metadata).items()
            if ("network" in ext
                and (data["security_posture"]
                     == "robust_to_untrusted_downstream"))])

    async def check_metadata(self, extension: str) -> Tuple[str, ...]:
        return tuple(
            itertools.chain.from_iterable(
                await asyncio.gather(
                    self._check_metadata_categories(extension),
                    self._check_metadata_security_posture(extension),
                    self._check_metadata_status(extension))))

    async def _check_metadata_categories(
            self, extension: str) -> Tuple[str, ...]:
        categories = (await self.metadata)[extension].get("categories", ())
        if not categories:
            return (
                f"Missing extension category for {extension}. "
                "Please make sure the target is an envoy_cc_extension "
                "and category is set", )
        return tuple(
            (f"Unknown extension category for {extension}: {cat}. "
             "Please add it to tools/extensions/extensions_check.py")
            for cat
            in categories
            if cat not in self.extension_categories)

    async def _check_metadata_security_posture(
            self, extension: str) -> Tuple[str, ...]:
        security_posture = (await self.metadata)[extension]["security_posture"]
        if not security_posture:
            return (
                f"Missing security posture for {extension}. "
                "Please make sure the target is an "
                "envoy_cc_extension and security_posture is set", )
        elif security_posture not in self.extension_security_postures:
            return (
                "Unknown security posture for "
                f"{extension}: {security_posture}", )
        return ()

    async def _check_metadata_status(
            self, extension: str) -> Tuple[str, ...]:
        status = (await self.metadata)[extension]["status"]
        if status not in self.extension_status_values:
            return (f"Unknown status for {extension}: {status}", )
        return ()

    def _from_json(
            self,
            path: Union[str, pathlib.Path],
            type: Type,
            err_message: str,
            warn_message: str) -> Any:
        # Parse JSON, handling errors
        try:
            return utils.from_json(path, type)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise exceptions.ExtensionsConfigurationError(
                err_message.format(path=path, e=e))
        except utils.TypeCastingError as e:
            logger.warning(warn_message.format(path=path, e=e))
            return e.value

    def _from_yaml(
            self,
            path: Union[str, pathlib.Path],
            type: Type,
            err_message: str,
            warn_message: str) -> Any:
        # Parse YAML, handling errors
        try:
            return utils.from_yaml(path, type)
        except (_yaml.reader.ReaderError, FileNotFoundError) as e:
            raise exceptions.ExtensionsConfigurationError(
                err_message.format(path=path, e=e))
        except utils.TypeCastingError as e:
            logger.warning(warn_message.format(path=path, e=e))
            return e.value

    async def _metadata(self, path) -> typing.ExtensionsMetadataDict:
        try:
            return await self.execute(
                utils.from_yaml,
                path,
                typing.ExtensionsMetadataDict)
        except (utils.exceptions.TypeCastingError, FileNotFoundError) as e:
            raise exceptions.ExtensionsConfigurationError(
                "Failed to parse extensions metadata "
                f"({path}): {e}")
