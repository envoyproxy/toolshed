
import pytest

import abstracts

from envoy.docs import abstract


@abstracts.implementer(abstract.AProtobufRSTFormatter)
class DummyProtobufRSTFormatter:

    @property
    def annotations(self):
        return super().annotations

    @property
    def api_namespace(self):
        return super().api_namespace

    @property
    def extra_field_type_names(self):
        return super().extra_field_type_names

    @property
    def field_type_names(self):
        return super().field_type_names

    @property
    def json_format(self):
        return super().json_format

    @property
    def namespace(self):
        return super().namespace

    @property
    def protodoc_manifest(self):
        return super().protodoc_manifest

    @property
    def status_pb2(self):
        return super().status_pb2

    @property
    def security_pb2(self):
        return super().security_pb2

    @property
    def validate_pb2(self):
        return super().validate_pb2


@abstracts.implementer(abstract.ARSTFormatter)
class DummyRSTFormatter:

    @property
    def contrib_note(self):
        return super().contrib_note

    @property
    def contrib_extensions_categories(self):
        return super().contrib_extensions_categories

    @property
    def validate_fragment(self):
        return super().validate_fragment

    @property
    def v2_mapping(self):
        return super().v2_mapping

    @property
    def v2_link_template(self):
        return super().v2_link_template

    @property
    def pb(self):
        return super().pb

    @property
    def extensions_categories(self):
        return super().extensions_categories

    @property
    def envoy_last_v2_version(self):
        return super().envoy_last_v2_version

    @property
    def extension_category_template(self):
        return super().extension_category_template

    @property
    def extensions_metadata(self):
        return super().extensions_metadata

    @property
    def extension_security_postures(self):
        return super().extension_security_postures

    @property
    def extension_status_categories(self):
        return super().extension_status_categories

    @property
    def extension_status_types(self):
        return super().extension_status_types

    @property
    def extension_template(self):
        return super().extension_template


def test_utils_formatter_constructor():
    with pytest.raises(TypeError):
        abstract.ARSTFormatter()

    format = DummyRSTFormatter()

    iface_props = (
        "contrib_extensions_categories", "envoy_last_v2_version",
        "extensions_categories", "extensions_metadata",
        "extension_security_postures", "extension_status_types", "pb",
        "validate_fragment", "v2_mapping")

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(format, prop)


@pytest.mark.parametrize(
    "constant",
    ("contrib_note", "extension_template"))
def test_utils_formatter_abstract_methods(constant):
    assert (
        getattr(DummyRSTFormatter(), constant)
        == getattr(abstract.formatter, constant.upper()))


@pytest.mark.parametrize("text", ("ABC", "", "ABCDXYZ"))
@pytest.mark.parametrize("url", ("URL1", "URL2"))
@pytest.mark.parametrize("suffix", (None, "_", "__"))
def test_utils_formatter_external_link(text, url, suffix):
    args = (text, url, suffix) if suffix else (text, url)
    suffix = suffix or "__"
    assert (
        DummyRSTFormatter().external_link(*args)
        == f"`{text} <{url}>`{suffix}")


@pytest.mark.parametrize("text", ("ABC", "", "ABCDXYZ"))
@pytest.mark.parametrize("ref", ("REF1", "REF2"))
def test_utils_formatter_internal_link(text, ref):
    assert (
        DummyRSTFormatter().internal_link(text, ref)
        == f":ref:`{text} <{ref}>`")


@pytest.mark.parametrize("text", ("ABC", "", "ABCDXYZ"))
@pytest.mark.parametrize("underline", (None, "*", "-", "~"))
def test_utils_formatter_header(text, underline):
    args = (text, underline) if underline else (text, )
    underline = underline or "~"
    assert (
        DummyRSTFormatter().header(*args)
        == f'\n{text}\n{underline * len(text)}\n\n')


def test_utils_pb_formatter_constructor():
    with pytest.raises(TypeError):
        abstract.AProtobufRSTFormatter("FORMATTER")

    proto_format = DummyProtobufRSTFormatter("FORMATTER")

    iface_props = (
        "annotations", "json_format", "protodoc_manifest",
        "security_pb2", "status_pb2", "validate_pb2")

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(proto_format, prop)
