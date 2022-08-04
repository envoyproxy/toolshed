
import argparse
import importlib
import json
import pathlib
from functools import cached_property, lru_cache
from typing import Callable, Dict, Type

from google.protobuf import descriptor, descriptor_pb2
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import json_format, text_format
from google.protobuf import (
    message as _message,
    message_factory as _message_factory)
from google.protobuf.compiler import plugin_pb2

import abstracts

from aio.api import bazel
from aio.core.utils import dottedname_resolve

from envoy.base.utils import interface


BOOTSTRAP_PROTO = "envoy.config.bootstrap.v3.Bootstrap"

_envoy_yaml = None


def _yaml():
    # Load this lazily so we dont change the environment unless necessary.
    global _envoy_yaml

    if not _envoy_yaml:
        _envoy_yaml = importlib.import_module(
            "envoy.base.utils.yaml").envoy_yaml
    return _envoy_yaml


@abstracts.implementer(interface.IProtobufSet)
class AProtobufSet(metaclass=abstracts.Abstraction):

    def __init__(self, descriptor_path: str | pathlib.Path) -> None:
        self._descriptor_path = descriptor_path

    def __getitem__(self, name: str) -> descriptor_pb2.FileDescriptorProto:
        return self.source_files[name]

    @cached_property
    def descriptor_path(self) -> pathlib.Path:
        return pathlib.Path(self._descriptor_path)

    @cached_property
    def descriptor_pool(self) -> _descriptor_pool.DescriptorPool:
        pool = _descriptor_pool.DescriptorPool()
        for f in self.source_files.values():
            pool.Add(f)
        return pool

    @cached_property
    def descriptor_set(self) -> descriptor_pb2.FileDescriptorSet:
        # from tools.protoxform.utils import load_protos

        # load_protos()

        descriptor = descriptor_pb2.FileDescriptorSet()

        # text_format.Parse(
        #    self.descriptor_path.read_text(),
        #    descriptor)
            # allow_unknown_extension=True)

        descriptor.ParseFromString(self.descriptor_path.read_bytes())
        return descriptor

    @cached_property
    def source_files(self) -> Dict[str, descriptor_pb2.FileDescriptorProto]:
        return {
            f.name: f
            for f
            in self.descriptor_set.file}

    def find_file(self, type_name: str) -> descriptor.Descriptor:
        return self.descriptor_pool.FindFileByName(type_name)

    def find_message(self, type_name: str) -> descriptor.Descriptor:
        return self.descriptor_pool.FindMessageTypeByName(type_name)


@abstracts.implementer(interface.IProtobufValidator)
class AProtobufValidator(metaclass=abstracts.Abstraction):

    def __init__(self, descriptor_path: str | pathlib.Path) -> None:
        self.descriptor_path = descriptor_path

    @property
    def descriptor_pool(self) -> _descriptor_pool.DescriptorPool:
        return self.protobuf_set.descriptor_pool

    @cached_property
    def message_factory(self) -> _message_factory.MessageFactory:
        return _message_factory.MessageFactory(pool=self.descriptor_pool)

    @cached_property
    def protobuf_set(self) -> interface.IProtobufSet:
        return self.protobuf_set_class(self.descriptor_path)

    @property  # type:ignore
    @abstracts.interfacemethod
    def protobuf_set_class(self) -> Type[interface.IProtobufSet]:
        raise NotImplementedError

    @cached_property
    def yaml(self):
        return _yaml()

    @lru_cache
    def message(self, type_name: str) -> _message.Message:
        return self.message_prototype(type_name)()

    def message_prototype(
            self,
            type_name: str) -> Callable[[], _message.Message]:
        return self.message_factory.GetPrototype(
            self.protobuf_set.find_message(type_name))

    def validate_fragment(
            self,
            fragment: str,
            type_name: str = BOOTSTRAP_PROTO) -> None:
        """Validate a dictionary representing a JSON/YAML fragment against an
        Envoy API proto3 type.

        Throws Protobuf errors on parsing exceptions, successful
        validations produce no result.
        """
        json_format.Parse(
            json.dumps(fragment, skipkeys=True),
            self.message(type_name),
            descriptor_pool=self.descriptor_pool)

    def validate_yaml(
            self,
            fragment: str,
            type_name: str = BOOTSTRAP_PROTO) -> None:
        self.validate_fragment(self.yaml.safe_load(fragment), type_name)


@abstracts.implementer(bazel.IBazelProcessProtocol)
class AProtocProtocol(
        bazel.ABazelProcessProtocol,
        metaclass=abstracts.Abstraction):

    @classmethod
    def add_protocol_arguments(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("descriptor_set")
        parser.add_argument("plugin")

    @property
    def descriptor_set(self) -> str:
        return self.args.descriptor_set

    @cached_property
    def plugin(self) -> Callable:
        return dottedname_resolve(f"{self.args.plugin}.main")

    @cached_property
    def proto_set(self) -> interface.IProtobufSet:
        return self.proto_set_class(
            pathlib.Path(self.descriptor_set).absolute())

    @property  # type:ignore
    @abstracts.interfacemethod
    def proto_set_class(self) -> Type[interface.IProtobufSet]:
        raise NotImplementedError

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--in")
        parser.add_argument("--out")
        parser.add_argument("--suffixes")
        parser.add_argument("--type_db_path")
        parser.add_argument("--extra_args")

    def parse_request_files(
            self,
            request: argparse.Namespace) -> Dict[str, pathlib.Path]:
        return dict(
            zip(vars(request)["in"].split(","),
                (pathlib.Path(p)
                 for p
                 in request.out.split(","))))

    async def process(self, request: argparse.Namespace) -> None:
        for infile, outfile in self.parse_request_files(request).items():
            self._process_item(self._generate_request(request, infile), outfile)

    def _generate_request(self, request, infile):
        proto_file = self.proto_set[infile]
        code_request = plugin_pb2.CodeGeneratorRequest(
            file_to_generate=[proto_file.name],
            parameter=f"type_db_path={request.type_db_path}")
        code_request.proto_file.append(proto_file)
        return code_request

    def _output(self, request) -> str:
        return self.plugin(request).file[0].content

    def _process_item(self, request, outfile: pathlib.Path) -> None:
        outfile.parent.mkdir(exist_ok=True, parents=True)
        outfile.write_text(self._output(request))
