
import sys
from typing import Type

import abstracts

from envoy.base.utils import abstract, interface


sys.path = [p for p in sys.path if not p.endswith('bazel_tools')]


@abstracts.implementer(interface.IProtobufSet)
class ProtobufSet(abstract.AProtobufSet):
    pass


@abstracts.implementer(interface.IProtobufValidator)
class ProtobufValidator(abstract.AProtobufValidator):

    @property
    def protobuf_set_class(self) -> Type[interface.IProtobufSet]:
        return ProtobufSet


@abstracts.implementer(interface.IProtocProtocol)
class ProtocProtocol(abstract.AProtocProtocol):

    @property
    def proto_set_class(self):
        return ProtobufSet
