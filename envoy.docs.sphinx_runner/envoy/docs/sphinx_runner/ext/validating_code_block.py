
import os
from functools import cached_property
from typing import Dict, List

from docutils.parsers.rst import directives

from google.protobuf.json_format import ParseError

from sphinx.application import Sphinx
from sphinx.directives.code import CodeBlock
from sphinx.errors import ExtensionError

from envoy.base.utils import interface, from_yaml, ProtobufValidator


class ValidatingCodeBlock(CodeBlock):
    """A directive that provides protobuf yaml formatting and validation.

    'type-name' option is required and expected to conain full Envoy API
    type. An ExtensionError is raised on validation failure. Validation
    will be skipped if SPHINX_SKIP_CONFIG_VALIDATION environment
    variable is set.
    """
    has_content = True
    required_arguments = CodeBlock.required_arguments
    optional_arguments = CodeBlock.optional_arguments
    final_argument_whitespace = CodeBlock.final_argument_whitespace
    CodeBlock.option_spec.update({'type-name': directives.unchanged})

    @cached_property
    def configs(self) -> Dict:
        _configs = dict(skip_validation=False)
        if config_path := os.environ.get("ENVOY_DOCS_BUILD_CONFIG"):
            _configs.update(from_yaml(config_path))
        return _configs

    @property
    def skip_validation(self) -> bool:
        return bool(self.configs["skip_validation"])

    @cached_property
    def proto_validator(self) -> interface.IProtobufValidator:
        return ProtobufValidator(self.configs["descriptor_path"])

    def run(self) -> List:
        source, line = self.state_machine.get_source_and_line(self.lineno)
        # built-in directives.unchanged_required option validator produces
        # a confusing error message
        if self.options.get('type-name') is None:
            raise ExtensionError(
                f"Expected type name in: {source} line: {line}")

        if not self.skip_validation:
            self._validate(source, line)
        self.options.pop('type-name', None)
        return list(super().run())

    def _validate(self, source: str, line: int) -> None:
        try:
            self.proto_validator.validate_yaml(
                '\n'.join(self.content),
                self.options.get('type-name'))
        except (ParseError, KeyError):
            raise ExtensionError(
                "Failed config validation for type: "
                f"'{self.options.get('type-name')}' in: {source} line: "
                f"{line}")


def setup(app: Sphinx) -> Dict:
    app.add_directive("validated-code-block", ValidatingCodeBlock)
    return dict(
        version="0.1",
        parallel_read_safe=True,
        parallel_write_safe=True)
