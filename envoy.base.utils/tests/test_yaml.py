
from unittest.mock import MagicMock

import pytest

import yaml as base_yaml

from envoy.base.utils import yaml as _yaml


def test_yaml_envoy_yaml():
    assert _yaml.envoy_yaml == base_yaml


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


def test_yaml_envoyyaml_constructor():
    assert _yaml.EnvoyYaml()


def test_yaml_envoyyaml_yaml(patches):
    envoy_yaml = _yaml.EnvoyYaml()
    patched = patches(
        "IgnoredKey",
        "_yaml",
        prefix="envoy.base.utils.yaml")

    with patched as (m_ignore, m_yaml):
        assert (
            envoy_yaml.yaml
            == m_yaml)

    assert (
        m_yaml.SafeLoader.add_constructor.call_args
        == [('!ignore', m_ignore.from_yaml), {}])
    assert (
        m_yaml.SafeDumper.add_multi_representer.call_args
        == [(m_ignore, m_ignore.to_yaml), {}])
    assert "yaml" in envoy_yaml.__dict__


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
