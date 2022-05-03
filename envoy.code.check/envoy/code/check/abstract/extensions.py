
import json
import pathlib
import re
from functools import cached_property
from typing import Dict, Iterator, List, Pattern, Set

import abstracts

from envoy.base import utils
from envoy.code.check import abstract, exceptions, typing


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
            set(self.configured_extensions.keys())
            | set(self.builtin_extensions))

    @property
    def all_fuzzed(self) -> bool:
        return (
            self.robust_to_downstream_count
            == self.fuzzed_count)

    @property
    def builtin_extensions(self) -> typing.ExtensionsSchemaBuiltinList:
        return self.extensions_schema["builtin"]

    @cached_property
    def configured_extensions(self) -> typing.ConfiguredExtensionsDict:
        return utils.typed(
            typing.ConfiguredExtensionsDict,
            json.loads(
                pathlib.Path(self.extensions_build_config).read_text()))

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
        return utils.typed(
            typing.ExtensionsSchemaDict,
            utils.from_yaml(self.extensions_schema_path))

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

    @cached_property
    def metadata(self) -> typing.ExtensionsMetadataDict:
        return dict(**self.metadata_core, **self.metadata_contrib)

    @cached_property
    def metadata_contrib(self) -> typing.ExtensionsMetadataDict:
        try:
            return utils.typed(
                typing.ExtensionsMetadataDict,
                utils.from_yaml(self.metadata_contrib_path))
        except utils.exceptions.TypeCastingError as e:
            raise exceptions.ExtensionsConfigurationError(
                "Failed to parse contrib metadata "
                f"({self.metadata_contrib_path}): {e}")

    @property
    def metadata_contrib_path(self) -> pathlib.Path:
        return self.directory.path.joinpath(CONTRIB_METADATA_PATH)

    @cached_property
    def metadata_core(self) -> typing.ExtensionsMetadataDict:
        try:
            return utils.typed(
                typing.ExtensionsMetadataDict,
                utils.from_yaml(self.metadata_core_path))
        except utils.exceptions.TypeCastingError as e:
            raise exceptions.ExtensionsConfigurationError(
                "Failed to parse core metadata "
                f"({self.metadata_core_path}): {e}")

    @property
    def metadata_core_path(self) -> pathlib.Path:
        return self.directory.path.joinpath(METADATA_PATH)

    @property
    def metadata_errors(self) -> Dict[str, List[str]]:
        return {
            extension: self.check_metadata(extension)
            for extension
            in self.metadata}

    @property
    def metadata_missing(self) -> Set[str]:
        return (
            self.all_extensions
            - set(self.metadata.keys()))

    @property
    def metadata_only(self) -> Set[str]:
        return (
            set(self.metadata.keys())
            - self.metadata_only_extensions
            - self.all_extensions)

    @property
    def metadata_only_extensions(self) -> Set[str]:
        return set(METADATA_ONLY_EXTENSIONS)

    @property
    def registration_errors(self) -> List[str]:
        return [
            *[f"Metadata for unused extension found: {extension}"
              for extension
              in sorted(self.metadata_only)],
            *[f"Metadata missing for extension: {extension}"
              for extension
              in sorted(self.metadata_missing)]]

    @property
    def robust_to_downstream_count(self) -> int:
        # Count number of network filters robust to untrusted downstreams.
        return len([
            ext
            for ext, data
            in self.metadata.items()
            if ("network" in ext
                and (data["security_posture"]
                     == "robust_to_untrusted_downstream"))])

    def check_metadata(self, extension: str) -> list:
        return (
            list(self._check_metadata_categories(extension))
            + list(self._check_metadata_security_posture(extension))
            + list(self._check_metadata_status(extension)))

    def _check_metadata_categories(self, extension: str) -> Iterator[str]:
        categories = self.metadata[extension].get("categories", ())
        for cat in categories:
            if cat not in self.extension_categories:
                yield (
                    f"Unknown extension category for {extension}: {cat}. "
                    "Please add it to tools/extensions/extensions_check.py")
        if not categories:
            yield (
                f"Missing extension category for {extension}. "
                "Please make sure the target is an envoy_cc_extension "
                "and category is set")

    def _check_metadata_security_posture(
            self, extension: str) -> Iterator[str]:
        security_posture = self.metadata[extension]["security_posture"]
        if not security_posture:
            yield (
                f"Missing security posture for {extension}. "
                "Please make sure the target is an "
                "envoy_cc_extension and security_posture is set")
        elif security_posture not in self.extension_security_postures:
            yield (
                "Unknown security posture for "
                f"{extension}: {security_posture}")

    def _check_metadata_status(self, extension: str) -> Iterator[str]:
        status = self.metadata[extension]["status"]
        if status not in self.extension_status_values:
            yield f"Unknown status for {extension}: {status}"
