import abc
from collections import defaultdict
import functools
import sys
from typing import Callable, Dict, Iterable, List, Tuple

import yaml

from frozendict import frozendict

from jinja2 import Template

from google.protobuf import descriptor_pb2

import abstracts

from .exceptions import RSTFormatterError


CONTRIB_NOTE = """

.. note::
  This extension is only available in :ref:`contrib <install_contrib>` images.

"""

# Template for formating an extension category.
EXTENSION_CATEGORY_TEMPLATE = Template(
    """
.. _extension_category_{{category}}:

.. tip::
{% if extensions %}
  This extension category has the following known extensions:

{% for ext in extensions %}
  - :ref:`{{ext}} <extension_{{ext}}>`
{% endfor %}

{% endif %}
{% if contrib_extensions %}
  The following extensions are available in :ref:`contrib <install_contrib>`
  images only:

{% for ext in contrib_extensions %}
  - :ref:`{{ext}} <extension_{{ext}}>`
{% endfor %}
{% endif %}

""")

# Template for formating extension descriptions.
EXTENSION_TEMPLATE = Template(
    """
.. _extension_{{extension}}:

This extension may be referenced by the qualified name ``{{extension}}``
{{contrib}}
.. note::
  {{status}}

  {{security_posture}}

.. tip::
  This extension extends and can be used with the following extension
  {% if categories|length > 1 %}categories{% else %}category{% endif %}:

{% for cat in categories %}
  - :ref:`{{cat}} <extension_category_{{cat}}>`
{% endfor %}

""")

V2_LINK_TEMPLATE = Template(
    """
This documentation is for the Envoy v3 API.

As of Envoy v1.18 the v2 API has been removed and is no longer supported.

If you are upgrading from v2 API config you may wish to view the v2 API
documentation:

    :ref:`{{v2_text}} <{{v2_url}}>`

""")

# Namespace prefix for WKTs.
WKT_NAMESPACE_PREFIX = '.google.protobuf.'

# Namespace prefix for RPCs.
RPC_NAMESPACE_PREFIX = '.google.rpc.'

# Namespace prefix for Envoy core APIs.
ENVOY_API_NAMESPACE_PREFIX = '.envoy.api.v2.'

# Namespace prefix for Envoy top-level APIs.
ENVOY_PREFIX = '.envoy.'

# http://www.fileformat.info/info/unicode/char/2063/index.htm
UNICODE_INVISIBLE_SEPARATOR = u'\u2063'

PROTOBUF_SCALAR_URL = (
    'https://developers.google.com/protocol-buffers/docs/proto#scalar')
GOOGLE_RPC_URL_TPL = (
    "https://cloud.google.com/natural-language/docs/reference/rpc/"
    "google.rpc#{rpc}")
PROTOBUF_URL_TPL = (
    "https://developers.google.com/protocol-buffers/docs/reference/"
    "google.protobuf#{wkt}")
FIELD_TYPE_NAMES = frozendict({
    descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE: 'double',
    descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT: 'float',
    descriptor_pb2.FieldDescriptorProto.TYPE_INT32: 'int32',
    descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED32: 'int32',
    descriptor_pb2.FieldDescriptorProto.TYPE_SINT32: 'int32',
    descriptor_pb2.FieldDescriptorProto.TYPE_FIXED32: 'uint32',
    descriptor_pb2.FieldDescriptorProto.TYPE_UINT32: 'uint32',
    descriptor_pb2.FieldDescriptorProto.TYPE_INT64: 'int64',
    descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED64: 'int64',
    descriptor_pb2.FieldDescriptorProto.TYPE_SINT64: 'int64',
    descriptor_pb2.FieldDescriptorProto.TYPE_FIXED64: 'uint64',
    descriptor_pb2.FieldDescriptorProto.TYPE_UINT64: 'uint64',
    descriptor_pb2.FieldDescriptorProto.TYPE_BOOL: 'bool',
    descriptor_pb2.FieldDescriptorProto.TYPE_STRING: 'string',
    descriptor_pb2.FieldDescriptorProto.TYPE_BYTES: 'bytes'})
EXTRA_FIELD_TYPE_NAMES = frozendict({
    descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL: '',
    descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED: '**repeated** '})


class ARSTFormatter(metaclass=abstracts.Abstraction):

    @property
    @abc.abstractmethod
    def contrib_extensions_categories(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def contrib_note(self) -> str:
        return CONTRIB_NOTE

    @property
    @abc.abstractmethod
    def envoy_last_v2_version(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def extension_category_template(self) -> Template:
        return EXTENSION_CATEGORY_TEMPLATE

    @property
    @abc.abstractmethod
    def extension_template(self) -> Template:
        return EXTENSION_TEMPLATE

    @property
    @abc.abstractmethod
    def extensions_categories(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def extensions_metadata(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def extension_security_postures(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def extension_status_types(self):
        raise NotImplementedError

    @property
    def invisible_separator(self):
        return UNICODE_INVISIBLE_SEPARATOR

    @property
    @abc.abstractmethod
    def pb(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def validate_fragment(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def v2_link_template(self) -> Template:
        return V2_LINK_TEMPLATE

    @property
    @abc.abstractmethod
    def v2_mapping(self):
        raise NotImplementedError

    def anchor(self, label) -> str:
        """Format a label as an Envoy API RST anchor."""
        return f".. _{label}:\n\n"

    def extension_category(self, category: str) -> str:
        """Format extension metadata as RST."""
        extensions, contrib_extensions = self._get_extensions(category)
        if not (extensions or contrib_extensions):
            raise RSTFormatterError(
                "\n\nUnable to find extension category: "
                f"{category}\n\n")
        return self.extension_category_template.render(
            category=category,
            extensions=extensions,
            contrib_extensions=contrib_extensions)

    def extension(self, extension: str) -> str:
        """Format extension metadata as RST."""
        try:
            extension_metadata = self.extensions_metadata.get(extension, None)
            contrib = (
                self.contrib_note
                if extension_metadata and extension_metadata.get("contrib")
                else "")
            status = self.extension_status_types.get(
                extension_metadata.get('status'), '')
            security_posture = self.extension_security_postures[
                extension_metadata['security_posture']]
            categories = extension_metadata["categories"]
        except KeyError:
            sys.stderr.write(
                f"\n\nDid you forget to add '{extension}' to "
                "extensions_build_config.bzl, extensions_metadata.yaml, "
                "contrib_build_config.bzl, or "
                "contrib/extensions_metadata.yaml?\n\n")
            # Raising the error buries the above message in tracebacks.
            exit(1)

        return self.extension_template.render(
            extension=extension,
            contrib=contrib,
            status=status,
            security_posture=security_posture,
            categories=categories)

    def extension_list_item(self, extension: str, metadata: Dict) -> str:
        item = (
            f"* {extension}"
            if metadata.get("undocumented")
            else f"* :ref:`{extension} <extension_{extension}>`")
        if metadata.get("status") == "alpha":
            item += " (alpha)"
        if metadata.get("contrib"):
            item += " (:ref:`contrib builds <install_contrib>` only)"
        return item

    def external_link(self, text: str, url: str, suffix: str = "__") -> str:
        return f"`{text} <{url}>`{suffix}"

    def header(self, title: str, underline: str = "~") -> str:
        return f'\n{title}\n{underline * len(title)}\n\n'

    def indent(self, spaces: int, line: str) -> str:
        """Indent a string."""
        return f"{' ' * spaces}{line}"

    def indent_lines(self, spaces: int, lines: Iterable) -> map:
        """Indent a list of strings."""
        return map(functools.partial(self.indent, spaces), lines)

    def internal_link(self, text: str, ref: str) -> str:
        return f":ref:`{text} <{ref}>`"

    def map_lines(self, f: Callable, s: str) -> str:
        """Apply a function across each line in a flat string."""
        return '\n'.join(f(line) for line in s.split('\n'))

    def strip_leading_space(self, lines) -> str:
        """Remove leading space in flat comment strings."""
        return self.map_lines(lambda s: s[1:], lines)

    def v2_link(self, name: str) -> str:
        if name not in self.v2_mapping:
            return ""
        v2_filepath = f"envoy_api_file_{self.v2_mapping[name]}"
        return self.v2_link_template.render(
            v2_url=f"v{self.envoy_last_v2_version}:{v2_filepath}",
            v2_text=v2_filepath.split('/', 1)[1])

    def version(self, version):
        # Render version strings human readable.
        # Heuristic, almost certainly a git SHA
        if len(version) == 40:
            # Abbreviate git SHA
            return version[:7]
        return version

    def _get_extensions(self, category: str) -> Tuple[List, List]:
        return (
            sorted(self.extensions_categories.get(category, [])),
            sorted(self.contrib_extensions_categories.get(category, [])))


class AProtobufRSTFormatter(metaclass=abstracts.Abstraction):

    def __init__(self, rst: ARSTFormatter):
        self.rst = rst

    @property
    @abc.abstractmethod
    def annotations(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def api_namespace(self) -> str:
        return ENVOY_API_NAMESPACE_PREFIX

    @property
    @abc.abstractmethod
    def extra_field_type_names(self):
        return EXTRA_FIELD_TYPE_NAMES

    @property
    @abc.abstractmethod
    def field_type_names(self):
        return FIELD_TYPE_NAMES

    @property
    @abc.abstractmethod
    def json_format(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def namespace(self) -> str:
        return ENVOY_PREFIX

    @property
    @abc.abstractmethod
    def protodoc_manifest(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def security_pb2(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def status_pb2(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def validate_pb2(self):
        raise NotImplementedError

    def comment_with_annotations(self, comment, type_name: str = '') -> str:
        """Format a comment string with additional RST for annotations."""
        alpha_warning = ''
        # if self.annotations.ALPHA_ANNOTATION in comment.annotations:
        #     experimental_warning = (
        #        '.. warning::\n   This API is alpha and is not covered '
        #        'by the :ref:`threat model <arch_overview_threat_model>`.\n\n'
        #    )
        extension = comment.annotations.get(
            self.annotations.EXTENSION_ANNOTATION)
        formatted_extension = (
            self.rst.extension(extension)
            if extension
            else "")
        category_annotations = comment.annotations.get(
            self.annotations.EXTENSION_CATEGORY_ANNOTATION,
            "").split(",")
        formatted_category = "".join(
            self.rst.extension_category(category)
            for category
            in category_annotations
            if category)
        comment = self.annotations.without_annotations(
            f"{self.rst.strip_leading_space(comment.raw)}\n")
        return (
            f"{alpha_warning}{comment}{formatted_extension}"
            f"{formatted_category}")

    def enum_as_dl(self, type_context, enum) -> str:
        """Format a EnumDescriptorProto as RST definition list."""
        out = []
        for index, value in enumerate(enum.value):
            ctx = type_context.extend_enum_value(index, value.name)
            out.append(
                self.enum_value_as_dl_item(
                    ctx.name, ctx.leading_comment, value))
        return "%s\n" % '\n'.join(out)

    def enum_value_as_dl_item(
            self,
            name: str,
            comment: str,
            enum_value) -> str:
        """Format a EnumValueDescriptorProto as RST definition list item."""
        if self.hide_not_implemented(comment):
            return ''
        anchor = self.rst.anchor(
            self.cross_ref_label(
                self.normalize_field_type_name(f".{name}"),
                "enum_value"))
        default_comment = (
            "*(DEFAULT)* "
            if enum_value.number == 0
            else "")
        leading_comment = self.comment_with_annotations(comment)
        comment = (
            f"{default_comment}{self.rst.invisible_separator}"
            f"{leading_comment}")
        lines = self.rst.map_lines(
            functools.partial(self.rst.indent, 2),
            comment)
        return (
            f"{anchor}{enum_value.name}\n"
            f"{lines}")

    def field_as_dl_item(
            self,
            outer_type_context,
            type_context,
            field: descriptor_pb2.FieldDescriptorProto) -> str:
        """Format a FieldDescriptorProto as RST definition list item."""
        leading_comment = self.comment_with_annotations(
            type_context.leading_comment)

        if self.hide_not_implemented(type_context.leading_comment):
            return ''

        field_annotations = []
        anchor = self.rst.anchor(
            self.cross_ref_label(
                self.normalize_field_type_name(f".{type_context.name}"),
                "field"))

        validate_rule = self._get_extension(field, self.validate_pb2.rules)
        if validate_rule and self._is_required(validate_rule):
            field_annotations = ['*REQUIRED*']
        required, oneof_comment = self.oneof_comment(
            outer_type_context, type_context, field)
        if required is None:
            return ""
        if not required:
            field_annotations = []

        comment = '(%s) ' % ', '.join(
            [self.extra_field_type_names[field.label]
             + self.field_type(type_context, field)]
            + field_annotations) + leading_comment
        lines = self.rst.map_lines(
            functools.partial(self.rst.indent, 2),
            f"{comment}{oneof_comment}")
        # If there is a udpa.annotations.security option, include it after
        # the comment.
        return (
            f"{anchor}{field.name}\n{lines}"
            f"{self.security_extension(type_context.name, field)}")

    def field_type(
            self,
            type_context,
            field: descriptor_pb2.FieldDescriptorProto) -> str:
        """Format a FieldDescriptorProto type description."""
        if self._is_envoy_field(field):
            return self._envoy_field_type(type_context, field)
        elif field.type_name.startswith(WKT_NAMESPACE_PREFIX):
            wkt = field.type_name[len(WKT_NAMESPACE_PREFIX):]
            return self.rst.external_link(
                wkt, PROTOBUF_URL_TPL.format(wkt=wkt.lower()))
        elif field.type_name.startswith(RPC_NAMESPACE_PREFIX):
            rpc = field.type_name[len(RPC_NAMESPACE_PREFIX):]
            return self.rst.external_link(
                rpc, GOOGLE_RPC_URL_TPL.format(rpc=rpc.lower()))
        elif field.type_name:
            return field.type_name
        if field.type in self.field_type_names:
            return self.rst.external_link(
                self.field_type_names[field.type],
                PROTOBUF_SCALAR_URL)
        raise RSTFormatterError('Unknown field type ' + str(field.type))

    def field_type_as_json(
            self,
            type_context,
            field: descriptor_pb2.FieldDescriptorProto) -> str:
        """Format FieldDescriptorProto.Type as a pseudo-JSON string."""
        if field.label == field.LABEL_REPEATED:
            return '[]'
        return_object = (
            (field.type == field.TYPE_MESSAGE)
            or (self.type_name_from_fqn(field.type_name)
                in type_context.map_typenames))
        return (
            '"{...}"'
            if return_object
            else '"..."')

    def cross_ref_label(self, name: str, type: str) -> str:
        return f"envoy_v3_api_{type}_{name}"

    def header_from_file(
            self,
            style,
            source_code_info,
            proto_name,
            v2_link) -> Tuple[str, str]:
        """Format RST header based on special file level title."""
        anchor = self.rst.anchor(
            self.cross_ref_label(proto_name, "file"))
        stripped_comment = self.annotations.without_annotations(
            self.rst.strip_leading_space(
                "\n".join(
                    f"{c}\n"
                    for c
                    in source_code_info.file_level_comments)))
        formatted_extension = ''
        extension_annotation = source_code_info.file_level_annotations.get(
            self.annotations.EXTENSION_ANNOTATION)
        if extension_annotation:
            formatted_extension = self.rst.extension(
                extension_annotation)
        doc_title_annotation = source_code_info.file_level_annotations.get(
            self.annotations.DOC_TITLE_ANNOTATION)
        if doc_title_annotation:
            return (
                f"{anchor}"
                f"{self.rst.header(doc_title_annotation, style)}"
                f"{v2_link}\n\n{formatted_extension}",
                stripped_comment)
        return (
            f"{anchor}{self.rst.header(proto_name, style)}{v2_link}"
            f"\n\n{formatted_extension}",
            stripped_comment)

    def hide_not_implemented(self, comment) -> bool:
        """Hide comments marked with [#not-implemented-hide:]"""
        return bool(
            self.annotations.NOT_IMPLEMENTED_HIDE_ANNOTATION
            in comment.annotations)

    def oneof_comment(
            self,
            outer_type_context,
            type_context,
            field):
        if not field.HasField('oneof_index'):
            return True, ""
        oneof_context = outer_type_context.extend_oneof(
            field.oneof_index,
            type_context.oneof_names[field.oneof_index])

        if self.hide_not_implemented(oneof_context.leading_comment):
            return None, ""
        oneof_comment = self.comment_with_annotations(
            oneof_context.leading_comment)

        # If the oneof only has one field and marked required, mark the
        # field as required.
        required = (
            len(type_context.oneof_fields[field.oneof_index]) == 1
            and type_context.oneof_required[field.oneof_index])

        if len(type_context.oneof_fields[field.oneof_index]) > 1:
            # Fields in oneof shouldn't be marked as required when we have
            # oneof comment below it.
            required = False
            oneof_comment += self._oneof_comment(
                outer_type_context, type_context, field)
        return required, oneof_comment

    def message_as_json(self, type_context, msg) -> str:
        """Format a message definition DescriptorProto as a pseudo-JSON
        block."""
        lines = []
        for index, field in enumerate(msg.field):
            field_type_context = type_context.extend_field(index, field.name)
            if self.hide_not_implemented(field_type_context.leading_comment):
                continue
            lines.append(
                f'"{field.name}": '
                f"{self.field_type_as_json(type_context, field)}")
        if lines:
            return (
                ".. code-block:: json\n\n  {\n%s\n  }\n\n"
                % ",\n".join(self.rst.indent_lines(4, lines)))
        return ""

    def message_as_dl(self, type_context, msg) -> str:
        """Format a DescriptorProto as RST definition list."""
        type_context.oneof_fields = defaultdict(list)
        type_context.oneof_required = defaultdict(bool)
        type_context.oneof_names = defaultdict(list)
        for index, field in enumerate(msg.field):
            if field.HasField('oneof_index'):
                leading_comment = type_context.extend_field(
                    index, field.name).leading_comment
                if self.hide_not_implemented(leading_comment):
                    continue
                type_context.oneof_fields[field.oneof_index].append(
                    (index, field.name))
        for index, oneof_decl in enumerate(msg.oneof_decl):
            if oneof_decl.options.HasExtension(self.validate_pb2.required):
                type_context.oneof_required[index] = (
                    oneof_decl.options.Extensions[self.validate_pb2.required])
            type_context.oneof_names[index] = oneof_decl.name
        return '\n'.join(
            self.field_as_dl_item(
                type_context,
                type_context.extend_field(index, field.name),
                field)
            for index, field in enumerate(msg.field)) + '\n'

    def normalize_field_type_name(self, field_fqn: str) -> str:
        """Normalize a fully qualified field type name, e.g.

        .envoy.foo.bar.

        Strips leading ENVOY_API_NAMESPACE_PREFIX and ENVOY_PREFIX.
        """
        if field_fqn.startswith(self.api_namespace):
            return field_fqn[len(self.api_namespace):]
        if field_fqn.startswith(self.namespace):
            return field_fqn[len(self.namespace):]
        return field_fqn

    def security_extension(
            self,
            name: str,
            field: descriptor_pb2.FieldDescriptorProto):
        sec_extension = self._get_extension(field, self.security_pb2.security)
        if not sec_extension:
            return ""
        manifest = self.protodoc_manifest.fields.get(name)
        if not manifest:
            raise RSTFormatterError(
                f"Missing protodoc manifest YAML for {name}")
        return self.security_options(
            sec_extension,
            field,
            name,
            manifest.edge_config)

    def security_options(
            self,
            security_option,
            field: descriptor_pb2.FieldDescriptorProto,
            name,
            edge_config) -> str:
        sections = []
        if security_option.configure_for_untrusted_downstream:
            sections.append(
                self.rst.indent(
                    4,
                    ("This field should be configured in the presence of "
                     "untrusted *downstreams*.")))
        if security_option.configure_for_untrusted_upstream:
            sections.append(
                self.rst.indent(
                    4,
                    ("This field should be configured in the presence of "
                     "untrusted *upstreams*.")))
        if edge_config.note:
            sections.append(self.rst.indent(4, edge_config.note))

        example_dict = self.json_format.MessageToDict(edge_config.example)
        self.rst.validate_fragment(field.type_name[1:], example_dict)
        field_name = name.split('.')[-1]
        example = {field_name: example_dict}
        sections.append(
            "".join([
                self.rst.indent(
                    4,
                    'Example configuration for untrusted environments:\n\n'),
                self.rst.indent(
                    4,
                    '.. code-block:: yaml\n\n'),
                '\n'.join(
                    self.rst.indent_lines(
                        6,
                        yaml.dump(example).split('\n')))]))
        joined_sections = '\n\n'.join(sections)
        return f".. attention::\n{joined_sections}"

    def type_name_from_fqn(self, fqn: str) -> str:
        return fqn[1:]

    def _envoy_field_type(
            self,
            type_context,
            field: descriptor_pb2.FieldDescriptorProto) -> str:
        normal_type_name = self.normalize_field_type_name(field.type_name)
        if field.type == field.TYPE_MESSAGE:
            type_name = self.type_name_from_fqn(field.type_name)
            if type_name in (type_context.map_typenames or []):
                return (
                    'map<%s, %s>'
                    % tuple(
                        map(functools.partial(self.field_type, type_context),
                            type_context.map_typenames[type_name])))
            return self.rst.internal_link(
                normal_type_name,
                self.cross_ref_label(normal_type_name, "msg"))
        if field.type == field.TYPE_ENUM:
            return self.rst.internal_link(
                normal_type_name,
                self.cross_ref_label(normal_type_name, "enum"))

    def _is_envoy_field(
            self,
            field: descriptor_pb2.FieldDescriptorProto) -> bool:
        return bool(
            field.type_name.startswith(self.api_namespace)
            or field.type_name.startswith(self.namespace))

    def _is_required(self, rule):
        return (
            (rule.HasField('message') and rule.message.required)
            or (rule.HasField('duration') and rule.duration.required)
            or (rule.HasField('string') and rule.string.min_len > 0)
            or (rule.HasField('string') and rule.string.min_bytes > 0)
            or (rule.HasField('repeated') and rule.repeated.min_items > 0))

    def _oneof_comment(
            self,
            outer_type_context,
            type_context,
            field: descriptor_pb2.FieldDescriptorProto) -> str:
        oneof_template = (
            '\nPrecisely one of %s must be set.\n'
            if type_context.oneof_required[field.oneof_index]
            else '\nOnly one of %s may be set.\n')
        return (
            oneof_template
            % ', '.join(
                self.rst.internal_link(
                    f,
                    self.cross_ref_label(
                        self.normalize_field_type_name(
                            f".{outer_type_context.extend_field(i, f).name}"),
                        "field"))
                for i, f in type_context.oneof_fields[field.oneof_index]))

    def _get_extension(
            self,
            field: descriptor_pb2.FieldDescriptorProto,
            extension):
        if field.options.HasExtension(extension):
            return field.options.Extensions[extension]
