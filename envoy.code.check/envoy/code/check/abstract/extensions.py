
import asyncio
import itertools
import json
import logging
import pathlib
from functools import cached_property
from typing import (
    Any, cast, Dict, List,
    Optional, Set, Tuple, Type, Union)

import yaml as _yaml

import abstracts

from aio.core import functional, utils
from aio.core.functional import async_property

from envoy.code.check import abstract, exceptions, interface, typing


logger = logging.getLogger(__name__)

FUZZ_TEST_PATH = (
    "test/extensions/filters/network/common/fuzz/config.bzl")
METADATA_PATH = "source/extensions/extensions_metadata.yaml"
METADATA_ONLY_EXTENSIONS = (
    "envoy.filters.network.envoy_mobile_http_connection_manager", )
CONTRIB_METADATA_PATH = "contrib/extensions_metadata.yaml"
EXTENSIONS_SCHEMA = "tools/extensions/extensions_schema.yaml"

# TODO(phlax): remove this workaround if/when per-category status is added
UPSTREAM_EXTENSION_CATEGORY = "http.upstream"


@abstracts.implementer(interface.IExtensionsCheck)
class AExtensionsCheck(abstract.ACodeCheck, metaclass=abstracts.Abstraction):
    """Extensions check."""

    def __init__(
            self,
            *args,
            **kwargs) -> None:
        self.extensions_build_config = kwargs.pop("extensions_build_config")
        self._fuzzed_count = kwargs.pop("extensions_fuzzed_count", None)
        super().__init__(*args, **kwargs)

    @cached_property
    def all_extensions(self) -> Set[str]:
        return (
            set(self.configured_extensions)
            | set(self.builtin_extensions))

    @async_property
    async def all_fuzzed(self) -> bool:
        if self.fuzzed_count is None:
            logger.warning("Fuzz check called but fuzz count not set.")
            return True
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
        return [
            posture["name"]
            for posture
            in self.extensions_schema["security_postures"]]

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
    def extension_status_values(
            self) -> typing.ExtensionsSchemaStatusValuesList:
        return [
            posture["name"]
            for posture
            in self.extensions_schema["status_values"]]

    @property
    def fuzz_test_path(self) -> pathlib.Path:
        return self.directory.path.joinpath(FUZZ_TEST_PATH)

    @property
    def fuzzed_count(self) -> Optional[int]:
        # TODO: shift this to the arg parse
        return (
            int(self._fuzzed_count)
            if self._fuzzed_count is not None
            else None)

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
                    self._check_metadata_status(extension),
                    self._check_metadata_status_upstream(extension))))

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

    async def _check_metadata_status_upstream(
            self, extension: str) -> Tuple[str, ...]:
        metadata = (await self.metadata)[extension]
        status = metadata.get("status_upstream")
        categories = metadata.get("categories", ())
        if status and (UPSTREAM_EXTENSION_CATEGORY not in categories):
            return (
                f"Do not set ({extension}) `status_upstream` for extensions "
                f"that are not part of `{UPSTREAM_EXTENSION_CATEGORY}`", )
        if not status and UPSTREAM_EXTENSION_CATEGORY in categories:
            return (
                f"You must set ({extension}) `status_upstream` for extensions "
                f"that are part of `{UPSTREAM_EXTENSION_CATEGORY}`", )
        if status and status not in self.extension_status_values:
            return (f"Unknown `status_upstream` for {extension}: {status}", )
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
        except functional.exceptions.TypeCastingError as e:
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
        except functional.exceptions.TypeCastingError as e:
            logger.warning(warn_message.format(path=path, e=e))
            return e.value

    async def _metadata(self, path) -> typing.ExtensionsMetadataDict:
        errors = (functional.exceptions.TypeCastingError, FileNotFoundError)
        try:
            return await self.execute(
                utils.from_yaml,
                path,
                typing.ExtensionsMetadataDict)
        except errors as e:
            raise exceptions.ExtensionsConfigurationError(
                "Failed to parse extensions metadata "
                f"({path}): {e}")
