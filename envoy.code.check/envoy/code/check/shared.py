
from functools import cached_property
from typing import Callable

from envoy.code.check import typing


class EnvoyFormatConfig:
    """Provides a format config object based on parsed YAML config."""

    def __init__(self, config: typing.YAMLConfigDict, source_path) -> None:
        self.config = config
        self.source_path = source_path

    def __getitem__(self, k):
        return self.config.__getitem__(k)

    @cached_property
    def paths(self) -> (
            dict[str, tuple[str, ...] | dict[str, tuple[str, ...]]]):
        """Mapping of named paths."""
        paths = self._normalize(
            "paths",
            cb=lambda paths: tuple(paths))
        return paths

    @cached_property
    def suffixes(self) -> (
            dict[str, tuple[str, ...] | dict[str, tuple[str, ...]]]):
        """Mapping of named file suffixes for target files."""
        return self._normalize("suffixes")

    def _normalize(
            self,
            config_type: str,
            cb: Callable[..., tuple[str, ...]] = tuple) -> dict:
        config: dict = {}
        for k, v in self[config_type].items():
            if isinstance(v, dict):
                config[k] = {}
                for key in ("include", "exclude"):
                    if key in v:
                        config[k][key] = cb(v[key])
            else:
                config[k] = cb(v)
        return config
