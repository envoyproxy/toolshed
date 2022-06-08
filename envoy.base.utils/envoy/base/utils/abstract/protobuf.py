
import importlib
import json
import pathlib
from functools import cached_property, lru_cache
from typing import Callable, Type

from google.protobuf import descriptor, descriptor_pb2
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import json_format
from google.protobuf import (
    message as _message,
    message_factory as _message_factory)

import abstracts

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


class AProtobufSet(metaclass=abstracts.Abstraction):

    def __init__(self, descriptor_path: str | pathlib.Path) -> None:
        self._descriptor_path = descriptor_path

    @cached_property
    def descriptor_path(self) -> pathlib.Path:
        return pathlib.Path(self._descriptor_path)

    @cached_property
    def descriptor_pool(self) -> _descriptor_pool.DescriptorPool:
        pool = _descriptor_pool.DescriptorPool()
        for f in self.descriptor_set.file:
            pool.Add(f)
        return pool

    @cached_property
    def descriptor_set(self) -> descriptor_pb2.FileDescriptorSet:
        descriptor = descriptor_pb2.FileDescriptorSet()
        descriptor.ParseFromString(self.descriptor_path.read_bytes())
        return descriptor


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

    def find_message(self, type_name: str) -> descriptor.Descriptor:
        return self.descriptor_pool.FindMessageTypeByName(type_name)

    @lru_cache
    def message(self, type_name: str) -> _message.Message:
        return self.message_prototype(type_name)()

    def message_prototype(
            self,
            type_name: str) -> Callable[[], _message.Message]:
        return self.message_factory.GetPrototype(self.find_message(type_name))

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
