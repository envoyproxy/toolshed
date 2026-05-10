
from unittest.mock import MagicMock

import pytest

import yaml as base_yaml

from envoy.base.utils import yaml as _yaml


def test_yaml_envoyloader_subclass():
    assert issubclass(_yaml.EnvoyLoader, base_yaml.SafeLoader)


def test_yaml_envoydumper_subclass():
    assert issubclass(_yaml.EnvoyDumper, base_yaml.SafeDumper)


def test_yaml_envoyloader_roundtrip():
    assert base_yaml.load("a: 1", Loader=_yaml.EnvoyLoader) == {"a": 1}
    assert (
        base_yaml.load("k: !ignore foo", Loader=_yaml.EnvoyLoader)["k"]
        == _yaml.IgnoredKey("foo"))


def test_yaml_envoydumper_roundtrip():
    dumped = base_yaml.dump(
        {"k": _yaml.IgnoredKey("foo")}, Dumper=_yaml.EnvoyDumper)
    assert (
        base_yaml.load(dumped, Loader=_yaml.EnvoyLoader)
        == {"k": _yaml.IgnoredKey("foo")})


def test_yaml_ignoredkey_from_yaml():
    loader = MagicMock()
    node = MagicMock()
    ignored = _yaml.IgnoredKey.from_yaml(loader, node)
    assert isinstance(ignored, _yaml.IgnoredKey)
    assert ignored.strval == node.value


def test_yaml_ignoredkey_to_yaml():
    dumper = MagicMock()
    data = MagicMock()
    assert (
        _yaml.IgnoredKey.to_yaml(dumper, data)
        == dumper.represent_scalar.return_value)
    assert (
        dumper.represent_scalar.call_args
        == [(_yaml.IgnoredKey.yaml_tag, data.strval), {}])


def test_yaml_envoyloader_constructor_registration():
    assert (
        _yaml.EnvoyLoader.yaml_constructors[_yaml.IgnoredKey.yaml_tag]
        == _yaml.IgnoredKey.from_yaml)
    assert (
        _yaml.EnvoyLoader.yaml_constructors
        is not base_yaml.SafeLoader.yaml_constructors)
    assert (
        _yaml.IgnoredKey.yaml_tag
        not in base_yaml.SafeLoader.yaml_constructors)


def test_yaml_envoydumper_representer_registration():
    assert (
        _yaml.EnvoyDumper.yaml_multi_representers[_yaml.IgnoredKey]
        == _yaml.IgnoredKey.to_yaml)
    assert (
        _yaml.EnvoyDumper.yaml_multi_representers
        is not base_yaml.SafeDumper.yaml_multi_representers)
    assert _yaml.IgnoredKey not in base_yaml.SafeDumper.yaml_multi_representers


def test_yaml_ignoredkey_constructor():
    ignored = _yaml.IgnoredKey("STRVALUE")
    assert isinstance(ignored, base_yaml.YAMLObject)
    assert ignored.strval == "STRVALUE"


@pytest.mark.parametrize("isinst", [True, False])
@pytest.mark.parametrize("same", [True, False])
def test_yaml_ignoredkey_dunder_eq(patches, isinst, same):
    ignored = _yaml.IgnoredKey("STRVALUE")
    patched = patches(
        "isinstance",
        prefix="envoy.base.utils.yaml")
    other = MagicMock()
    if same:
        other.strval = "STRVALUE"

    with patched as (m_isinst, ):
        m_isinst.return_value = isinst
        assert (
            ignored.__eq__(other)
            == (isinst and same))

    assert (
        m_isinst.call_args
        == [(other, _yaml.IgnoredKey), {}])


def test_yaml_ignoredkey_dunder_hash(patches):
    ignored = _yaml.IgnoredKey("STRVALUE")
    patched = patches(
        "hash",
        prefix="envoy.base.utils.yaml")
    ignored.yaml_tag = MagicMock()

    with patched as (m_hash, ):
        assert (
            ignored.__hash__()
            == m_hash.return_value)

    assert (
        m_hash.call_args
        == [((ignored.yaml_tag, "STRVALUE"), ), {}])


def test_yaml_ignoredkey_dunder_repr():
    ignored = _yaml.IgnoredKey("STRVALUE")
    assert repr(ignored) == f"IgnoredKey({str})"
    assert ignored.yaml_tag == "!ignore"
