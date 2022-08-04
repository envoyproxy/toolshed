
import types
from unittest.mock import MagicMock, PropertyMock

import pytest

import abstracts

from aio.api import bazel

from envoy.base import utils


@abstracts.implementer(utils.interface.IProtobufValidator)
class DummyProtobufValidator(utils.abstract.AProtobufValidator):

    @property
    def protobuf_set_class(self):
        return super().protobuf_set_class


@abstracts.implementer(utils.interface.IProtocProtocol)
class DummyProtocProtocol(utils.abstract.AProtocProtocol):

    @property
    def proto_set_class(self):
        return super().proto_set_class


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


def test_protobufset_dunder_getitem(patches):
    proto_set = utils.abstract.AProtobufSet("DESCRIPTOR_PATH")
    patched = patches(
        ("AProtobufSet.source_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.protobuf")
    name = MagicMock()

    with patched as (m_files, ):
        assert (
            proto_set[name]
            == m_files.return_value.__getitem__.return_value)

    assert (
        m_files.return_value.__getitem__.call_args
        == [(name, ), {}])


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
        ("AProtobufSet.source_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.protobuf")
    items = iters()

    with patched as (m_pool, m_files):
        m_files.return_value.values.return_value = items
        assert (
            proto_set.descriptor_pool
            == m_pool.DescriptorPool.return_value)

    assert (
        m_pool.DescriptorPool.call_args
        == [(), {}])
    assert (
        m_files.return_value.values.call_args
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


def test_protobufset_source_files(iters, patches):
    proto_set = utils.abstract.AProtobufSet("DESCRIPTOR_PATH")
    patched = patches(
        ("AProtobufSet.descriptor_set",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.protobuf")
    files = iters(cb=lambda i: MagicMock())

    with patched as (m_desc, ):
        m_desc.return_value.file = files
        assert (
            proto_set.source_files
            == {f.name: f
                for f
                in files})

    assert "source_files" in proto_set.__dict__


def test_protobufset_find_file(patches):
    proto_set = utils.abstract.AProtobufSet("DESCRIPTOR_PATH")
    patched = patches(
        ("AProtobufSet.descriptor_pool",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.protobuf")
    type_name = MagicMock()

    with patched as (m_pool, ):
        assert (
            proto_set.find_file(type_name)
            == m_pool.return_value.FindFileByName.return_value)

    assert (
        m_pool.return_value.FindFileByName.call_args
        == [(type_name, ), {}])


def test_protobufset_find_message(patches):
    proto_set = utils.abstract.AProtobufSet("DESCRIPTOR_PATH")
    patched = patches(
        ("AProtobufSet.descriptor_pool",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.protobuf")
    type_name = MagicMock()

    with patched as (m_pool, ):
        assert (
            proto_set.find_message(type_name)
            == m_pool.return_value.FindMessageTypeByName.return_value)

    assert (
        m_pool.return_value.FindMessageTypeByName.call_args
        == [(type_name, ), {}])


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
        ("AProtobufValidator.protobuf_set",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.protobuf")
    type_name = MagicMock()

    with patched as (m_factory, m_set):
        assert (
            proto_validator.message_prototype(type_name)
            == m_factory.return_value.GetPrototype.return_value)

    assert (
        m_factory.return_value.GetPrototype.call_args
        == [(m_set.return_value.find_message.return_value, ), {}])
    assert (
        m_set.return_value.find_message.call_args
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


def test_protocprotocol_constructor():
    with pytest.raises(TypeError):
        utils.AProtocProtocol("PROCESSOR", "ARGS")

    protoc = DummyProtocProtocol("PROCESSOR", "ARGS")
    assert isinstance(protoc, bazel.IBazelProcessProtocol)

    with pytest.raises(NotImplementedError):
        protoc.proto_set_class


def test_protocprotocol_add_protocol_arguments():
    parser = MagicMock()
    assert not utils.AProtocProtocol.add_protocol_arguments(parser)
    assert (
        parser.add_argument.call_args_list
        == [[("descriptor_set", ), {}],
            [("traverser", ), {}],
            [("plugin", ), {}]])


def test_protocprotocol_descriptor_set():
    args = MagicMock()
    protoc = DummyProtocProtocol("PROCESSOR", args)
    assert (
        protoc.descriptor_set
        == args.descriptor_set)
    assert "descriptor_set" not in protoc.__dict__


def test_protocprotocol_proto_set(patches):
    protoc = DummyProtocProtocol("PROCESSOR", "ARGS")
    patched = patches(
        "pathlib",
        ("AProtocProtocol.descriptor_set",
         dict(new_callable=PropertyMock)),
        ("AProtocProtocol.proto_set_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.protobuf")

    with patched as (m_plib, m_desc, m_set):
        assert (
            protoc.proto_set
            == m_set.return_value.return_value)

    assert (
        m_set.return_value.call_args
        == [(m_plib.Path.return_value.absolute.return_value, ), {}])
    assert (
        m_plib.Path.call_args
        == [(m_desc.return_value, ), {}])
    assert (
        m_plib.Path.return_value.absolute.call_args
        == [(), {}])
    assert "proto_set" in protoc.__dict__


def test_protocprotocol_parse_request(iters, patches):
    protoc = DummyProtocProtocol("PROCESSOR", "ARGS")
    patched = patches(
        "dict",
        "vars",
        "zip",
        "pathlib",
        prefix="envoy.base.utils.abstract.protobuf")
    paths = iters()
    request = MagicMock()
    request.out.split.return_value = paths

    with patched as (m_dict, m_vars, m_zip, m_plib):
        assert (
            protoc.parse_request(request)
            == m_dict.return_value)
        resultgen = m_zip.call_args[0][1]
        assert (
            list(resultgen)
            == [m_plib.Path.return_value
                for p
                in paths])

    assert isinstance(resultgen, types.GeneratorType)
    assert (
        m_dict.call_args
        == [(m_zip.return_value, ), {}])
    assert (
        m_zip.call_args
        == [(m_vars.return_value.__getitem__.return_value.split.return_value,
            resultgen), {}])
    assert (
        m_vars.call_args
        == [(request, ), {}])
    assert (
        m_vars.return_value.__getitem__.call_args
        == [("in", ), {}])
    assert (
        m_vars.return_value.__getitem__.return_value.split.call_args
        == [(",", ), {}])
    assert (
        request.out.split.call_args
        == [(",", ), {}])
    assert (
        m_plib.Path.call_args_list
        == [[(p, ), {}]
            for p
            in paths])


async def test_protocprotocol_process(iters, patches):
    protoc = DummyProtocProtocol("PROCESSOR", "ARGS")
    patched = patches(
        "AProtocProtocol.parse_request",
        "AProtocProtocol._process_item",
        prefix="envoy.base.utils.abstract.protobuf")
    paths = iters(dict)
    request = MagicMock()

    with patched as (m_parse, m_item):
        m_parse.return_value = paths
        assert not await protoc.process(request)

    assert (
        m_parse.call_args
        == [(request, ), {}])
    assert (
        m_item.call_args_list
        == [[(k, v), {}]
            for k, v
            in paths.items()])


def test_protocprotocol__process_item(iters, patches):
    protoc = DummyProtocProtocol("PROCESSOR", "ARGS")
    patched = patches(
        "AProtocProtocol._output",
        prefix="envoy.base.utils.abstract.protobuf")
    infile = MagicMock()
    outfile = MagicMock()

    with patched as (m_out, ):
        assert not protoc._process_item(infile, outfile)

    assert (
        outfile.parent.mkdir.call_args
        == [(), dict(exist_ok=True, parents=True)])
    assert (
        outfile.write_text.call_args
        == [(m_out.return_value, ), {}])
    assert (
        m_out.call_args
        == [(infile, ), {}])
