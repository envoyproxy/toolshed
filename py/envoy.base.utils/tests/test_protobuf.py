
from envoy.base import utils


def test_protobufset_constructor(iters, patches):
    args = iters(tuple, count=3)
    kwargs = iters(dict, count=3)
    patched = patches(
        "abstract.AProtobufSet.__init__",
        prefix="envoy.base.utils.protobuf")

    with patched as (m_super, ):
        m_super.return_value = None
        protobuf = utils.ProtobufSet(*args, **kwargs)

    assert isinstance(protobuf, utils.interface.IProtobufSet)
    assert (
        m_super.call_args
        == [args, kwargs])


def test_protobufvalidator_constructor(iters, patches):
    args = iters(tuple, count=3)
    kwargs = iters(dict, count=3)
    patched = patches(
        "abstract.AProtobufValidator.__init__",
        prefix="envoy.base.utils.protobuf")

    with patched as (m_super, ):
        m_super.return_value = None
        protobuf = utils.ProtobufValidator(*args, **kwargs)

    assert isinstance(protobuf, utils.interface.IProtobufValidator)
    assert (
        m_super.call_args
        == [args, kwargs])
    assert protobuf.protobuf_set_class == utils.protobuf.ProtobufSet
