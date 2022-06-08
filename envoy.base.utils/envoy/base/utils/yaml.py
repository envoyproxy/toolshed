
from functools import cached_property

import yaml as _yaml


class IgnoredKey(_yaml.YAMLObject):
    """Python support type for Envoy's config !ignore tag."""
    yaml_tag = '!ignore'

    @classmethod
    def from_yaml(cls, loader, node):
        return IgnoredKey(node.value)

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar(cls.yaml_tag, data.strval)

    def __init__(self, strval) -> None:
        self.strval = strval

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, IgnoredKey)
            and self.strval == other.strval)

    def __hash__(self) -> int:
        return hash((self.yaml_tag, self.strval))

    def __repr__(self) -> str:
        return f'IgnoredKey({str})'


class EnvoyYaml:

    @cached_property
    def yaml(self):
        _yaml.SafeLoader.add_constructor('!ignore', IgnoredKey.from_yaml)
        _yaml.SafeDumper.add_multi_representer(IgnoredKey, IgnoredKey.to_yaml)
        return _yaml


envoy_yaml = EnvoyYaml().yaml
