
from unittest.mock import MagicMock, PropertyMock

import pytest

import abstracts

from envoy.base import utils


@abstracts.implementer(utils.interface.IProtobufValidator)
class DummyProtobufValidator(utils.abstract.AProtobufValidator):

    @property
    def protobuf_set_class(self):
        return super().protobuf_set_class


def test_protobuf__yaml(patches):
    patched = patches(
        "importlib",
        prefix="envoy.base.utils.abstract.protobuf")

    with patched as (m_import, ):
        assert (
            utils.abstract.protobuf._yaml()
            == m_import.import_module.return_value.envoy_yaml)

    assert (
        utils.abstract.protobuf._envoy_yaml
        == m_import.import_module.return_value.envoy_yaml)
    assert (
        m_import.import_module.call_args
        == [("envoy.base.utils.yaml", ), {}])


def test_protobufset_constructor():
    proto_set = utils.abstract.AProtobufSet("DESCRIPTOR_PATH")
    assert proto_set._descriptor_path == "DESCRIPTOR_PATH"


def test_protobufset_descriptor_path(patches):
    proto_set = utils.abstract.AProtobufSet("DESCRIPTOR_PATH")
    patched = patches(
        "pathlib",
        prefix="envoy.base.utils.abstract.protobuf")

    with patched as (m_plib, ):
        assert (
            proto_set.descriptor_path
            == m_plib.Path.return_value)

    assert (
        m_plib.Path.call_args
        == [("DESCRIPTOR_PATH", ), {}])
    assert "descriptor_path" in proto_set.__dict__


def test_protobufset_descriptor_pool(iters, patches):
    proto_set = utils.abstract.AProtobufSet("DESCRIPTOR_PATH")
    patched = patches(
        "_descriptor_pool",
        ("AProtobufSet.descriptor_set",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.protobuf")
    items = iters()

    with patched as (m_pool, m_set):
        m_set.return_value.file = items
        assert (
            proto_set.descriptor_pool
            == m_pool.DescriptorPool.return_value)

    assert (
        m_pool.DescriptorPool.call_args
        == [(), {}])
    assert (
        m_pool.DescriptorPool.return_value.Add.call_args_list
        == [[(item, ), {}]
            for item in items])
    assert "descriptor_pool" in proto_set.__dict__


def test_protobufset_descriptor_set(patches):
    proto_set = utils.abstract.AProtobufSet("DESCRIPTOR_PATH")
    patched = patches(
        "descriptor_pb2",
        ("AProtobufSet.descriptor_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.protobuf")

    with patched as (m_desc, m_path):
        assert (
            proto_set.descriptor_set
            == m_desc.FileDescriptorSet.return_value)

    assert (
        m_desc.FileDescriptorSet.call_args
        == [(), {}])
    assert (
        m_desc.FileDescriptorSet.return_value.ParseFromString.call_args
        == [(m_path.return_value.read_bytes.return_value, ), {}])
    assert (
        m_path.return_value.read_bytes.call_args
        == [(), {}])


def test_protobufvalidator_constructor():
    with pytest.raises(TypeError):
        utils.abstract.AProtobufValidator("DESCRIPTOR_PATH")

    proto_validator = DummyProtobufValidator("DESCRIPTOR_PATH")
    assert proto_validator.descriptor_path == "DESCRIPTOR_PATH"

    with pytest.raises(NotImplementedError):
        proto_validator.protobuf_set_class


def test_protobufvalidator_descriptor_pool(patches):
    proto_validator = DummyProtobufValidator("DESCRIPTOR_PATH")
    patched = patches(
        ("AProtobufValidator.protobuf_set",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.protobuf")

    with patched as (m_proto, ):
        assert (
            proto_validator.descriptor_pool
            == m_proto.return_value.descriptor_pool)

    assert "descriptor_pool" not in proto_validator.__dict__


def test_protobufvalidator_message_factory(patches):
    proto_validator = DummyProtobufValidator("DESCRIPTOR_PATH")
    patched = patches(
        "_message_factory",
        ("AProtobufValidator.descriptor_pool",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.protobuf")

    with patched as (m_factory, m_pool):
        assert (
            proto_validator.message_factory
            == m_factory.MessageFactory.return_value)

    assert (
        m_factory.MessageFactory.call_args
        == [(), dict(pool=m_pool.return_value)])
    assert "message_factory" in proto_validator.__dict__


def test_protobufvalidator_protobuf_set(patches):
    proto_validator = DummyProtobufValidator("DESCRIPTOR_PATH")
    patched = patches(
        ("AProtobufValidator.protobuf_set_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.protobuf")

    with patched as (m_class, ):
        assert (
            proto_validator.protobuf_set
            == m_class.return_value.return_value)

    assert (
        m_class.return_value.call_args
        == [("DESCRIPTOR_PATH", ), {}])
    assert "protobuf_set" in proto_validator.__dict__


def test_protobufvalidator_yaml(patches):
    proto_validator = DummyProtobufValidator("DESCRIPTOR_PATH")
    patched = patches(
        "_yaml",
        prefix="envoy.base.utils.abstract.protobuf")

    with patched as (m_yaml, ):
        assert (
            proto_validator.yaml
            == m_yaml.return_value)

    assert (
        m_yaml.call_args
        == [(), {}])
    assert "yaml" in proto_validator.__dict__


def test_protobufvalidator_find_message(patches):
    proto_validator = DummyProtobufValidator("DESCRIPTOR_PATH")
    patched = patches(
        ("AProtobufValidator.descriptor_pool",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.protobuf")
    type_name = MagicMock()

    with patched as (m_pool, ):
        assert (
            proto_validator.find_message(type_name)
            == m_pool.return_value.FindMessageTypeByName.return_value)

    assert (
        m_pool.return_value.FindMessageTypeByName.call_args
        == [(type_name, ), {}])


def test_protobufvalidator_message(patches):
    proto_validator = DummyProtobufValidator("DESCRIPTOR_PATH")
    patched = patches(
        "AProtobufValidator.message_prototype",
        prefix="envoy.base.utils.abstract.protobuf")
    type_name = MagicMock()

    with patched as (m_proto, ):
        assert (
            proto_validator.message(type_name)
            == m_proto.return_value.return_value)

    assert (
        m_proto.call_args
        == [(type_name, ), {}])
    assert (
        m_proto.return_value.call_args
        == [(), {}])


def test_protobufvalidator_message_prototype(patches):
    proto_validator = DummyProtobufValidator("DESCRIPTOR_PATH")
    patched = patches(
        ("AProtobufValidator.message_factory",
         dict(new_callable=PropertyMock)),
        "AProtobufValidator.find_message",
        prefix="envoy.base.utils.abstract.protobuf")
    type_name = MagicMock()

    with patched as (m_factory, m_find):
        assert (
            proto_validator.message_prototype(type_name)
            == m_factory.return_value.GetPrototype.return_value)

    assert (
        m_factory.return_value.GetPrototype.call_args
        == [(m_find.return_value, ), {}])
    assert (
        m_find.call_args
        == [(type_name, ), {}])


@pytest.mark.parametrize("type_name", [True, False])
def test_protobufvalidator_validate_fragment(patches, type_name):
    proto_validator = DummyProtobufValidator("DESCRIPTOR_PATH")
    patched = patches(
        "json",
        "json_format",
        ("AProtobufValidator.descriptor_pool",
         dict(new_callable=PropertyMock)),
        "AProtobufValidator.message",
        prefix="envoy.base.utils.abstract.protobuf")
    fragment = MagicMock()
    _type_name = MagicMock()
    args = (
        (_type_name, )
        if type_name
        else ())

    with patched as (m_json, m_fmt, m_pool, m_msg):
        assert not proto_validator.validate_fragment(fragment, *args)

    assert (
        m_fmt.Parse.call_args
        == [(m_json.dumps.return_value,
             m_msg.return_value),
            dict(descriptor_pool=m_pool.return_value)])
    assert (
        m_json.dumps.call_args
        == [(fragment, ), dict(skipkeys=True)])
    assert (
        m_msg.call_args
        == [(_type_name
             if type_name
             else utils.abstract.protobuf.BOOTSTRAP_PROTO, ),
            {}])


@pytest.mark.parametrize("type_name", [True, False])
def test_protobufvalidator_validate_yaml(patches, type_name):
    proto_validator = DummyProtobufValidator("DESCRIPTOR_PATH")
    patched = patches(
        ("AProtobufValidator.yaml",
         dict(new_callable=PropertyMock)),
        "AProtobufValidator.validate_fragment",
        prefix="envoy.base.utils.abstract.protobuf")
    fragment = MagicMock()
    _type_name = MagicMock()
    args = (
        (_type_name, )
        if type_name
        else ())

    with patched as (m_yaml, m_valid):
        assert not proto_validator.validate_yaml(fragment, *args)

    assert (
        m_valid.call_args
        == [(m_yaml.return_value.safe_load.return_value,
             _type_name
             if type_name
             else utils.abstract.protobuf.BOOTSTRAP_PROTO), {}])
    assert (
        m_yaml.return_value.safe_load.call_args
        == [(fragment, ), {}])
