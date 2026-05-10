
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


class EnvoyLoader(_yaml.SafeLoader):
    """SafeLoader subclass with envoy-specific YAML extensions registered.

    Registrations happen on this subclass only, leaving
    `yaml.SafeLoader` unmodified. This avoids polluting global PyYAML
    registries and is thread-safe by construction.
    """


class EnvoyDumper(_yaml.SafeDumper):
    """SafeDumper subclass with envoy-specific YAML extensions registered.

    Registrations happen on this subclass only, leaving
    `yaml.SafeDumper` unmodified. This avoids polluting global PyYAML
    registries and is thread-safe by construction.
    """


EnvoyLoader.add_constructor(IgnoredKey.yaml_tag, IgnoredKey.from_yaml)
EnvoyDumper.add_multi_representer(IgnoredKey, IgnoredKey.to_yaml)


class _EnvoyYamlShim:
    """Back-compat shim around PyYAML with Envoy loader/dumper defaults.

    Prefer using `EnvoyLoader`/`EnvoyDumper` directly with `yaml.load`
    and `yaml.dump`.
    """

    def safe_load(self, stream):
        return _yaml.load(stream, Loader=EnvoyLoader)

    def safe_load_all(self, stream):
        return _yaml.load_all(stream, Loader=EnvoyLoader)

    def safe_dump(self, data, stream=None, **kwargs):
        return _yaml.dump(data, stream, Dumper=EnvoyDumper, **kwargs)

    def safe_dump_all(self, documents, stream=None, **kwargs):
        return _yaml.dump_all(documents, stream, Dumper=EnvoyDumper, **kwargs)

    def __getattr__(self, name):
        return getattr(_yaml, name)


envoy_yaml = _EnvoyYamlShim()
