
from typing import Type

import abstracts

from envoy.base.utils import abstract, interface


@abstracts.implementer(interface.IProtobufSet)
class ProtobufSet(abstract.AProtobufSet):
    pass


@abstracts.implementer(interface.IProtobufValidator)
class ProtobufValidator(abstract.AProtobufValidator):

    @property
    def protobuf_set_class(self) -> Type[interface.IProtobufSet]:
        return ProtobufSet
