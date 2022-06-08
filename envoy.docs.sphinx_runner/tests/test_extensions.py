
from unittest.mock import MagicMock, PropertyMock

import pytest

from docutils.parsers.rst import directives

from google.protobuf.json_format import ParseError

from sphinx.directives.code import CodeBlock
from sphinx.errors import ExtensionError

from envoy.docs.sphinx_runner import ext
from envoy.docs.sphinx_runner.ext import validating_code_block


class DummyValidatingCodeBlock(validating_code_block.ValidatingCodeBlock):

    def __init__(self):
        pass


def test_ext_powershell_lexer_setup(patches):
    patched = patches(
        "PowerShellLexer",
        prefix="envoy.docs.sphinx_runner.ext.powershell_lexer")
    app = MagicMock()

    with patched as (m_lexer, ):
        assert (
            ext.powershell_lexer.setup(app)
            == dict(
                parallel_read_safe=True,
                parallel_write_safe=True))

    assert (
        app.add_lexer.call_args
        == [("powershell", m_lexer), {}])


def test_ext_validating_code_block_setup(patches):
    patched = patches(
        "ValidatingCodeBlock",
        prefix="envoy.docs.sphinx_runner.ext.validating_code_block")
    app = MagicMock()

    with patched as (m_block, ):
        assert (
            ext.validating_code_block.setup(app)
            == dict(
                version="0.1",
                parallel_read_safe=True,
                parallel_write_safe=True))

    assert (
        app.add_directive.call_args
        == [("validated-code-block", m_block), {}])


def test_ext_validating_code_block_vbc_constructor():
    vbc = DummyValidatingCodeBlock()
    assert isinstance(vbc, CodeBlock)
    assert vbc.has_content is True
    assert vbc.required_arguments == CodeBlock.required_arguments
    assert vbc.optional_arguments == CodeBlock.optional_arguments
    assert vbc.final_argument_whitespace == CodeBlock.final_argument_whitespace
    option_spec = {"type-name": directives.unchanged}
    option_spec.update(CodeBlock.option_spec)
    assert vbc.option_spec == option_spec


@pytest.mark.parametrize("config_path", [True, False])
def test_ext_validating_code_block_vbc_configs(patches, config_path):
    vbc = DummyValidatingCodeBlock()
    patched = patches(
        "dict",
        "os",
        "from_yaml",
        prefix="envoy.docs.sphinx_runner.ext.validating_code_block")
    config = MagicMock() if config_path else None

    with patched as (m_dict, m_os, m_yaml):
        m_os.environ.get.return_value = config
        assert (
            vbc.configs
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(), dict(skip_validation=False)])
    assert (
        m_os.environ.get.call_args
        == [("ENVOY_DOCS_BUILD_CONFIG", ), {}])
    if config_path:
        assert (
            m_dict.return_value.update.call_args
            == [(m_yaml.return_value, )])
        assert (
            m_yaml.call_args
            == [(config, ), {}])
    else:
        assert not m_dict.return_value.update.called
        assert not m_yaml.called
    assert "configs" in vbc.__dict__


def test_ext_validating_code_block_vbc_skip_validation(patches):
    vbc = DummyValidatingCodeBlock()
    patched = patches(
        "bool",
        ("ValidatingCodeBlock.configs",
         dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.ext.validating_code_block")

    with patched as (m_bool, m_configs):
        assert (
            vbc.skip_validation
            == m_bool.return_value)

    assert (
        m_bool.call_args
        == [(m_configs.return_value.__getitem__.return_value, ), {}])
    assert (
        m_configs.return_value.__getitem__.call_args
        == [("skip_validation", ), {}])
    assert "skip_validation" not in vbc.__dict__


def test_ext_validating_code_block_vbc_proto_validator(patches):
    vbc = DummyValidatingCodeBlock()
    patched = patches(
        "ProtobufValidator",
        ("ValidatingCodeBlock.configs",
         dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.ext.validating_code_block")

    with patched as (m_valid, m_configs):
        assert (
            vbc.proto_validator
            == m_valid.return_value)

    assert (
        m_valid.call_args
        == [(m_configs.return_value.__getitem__.return_value, ), {}])
    assert (
        m_configs.return_value.__getitem__.call_args
        == [("descriptor_path", ), {}])
    assert "proto_validator" in vbc.__dict__


@pytest.mark.parametrize("type_name", [None, "TYPENAME"])
@pytest.mark.parametrize("skip_validation", [True, False])
def test_ext_validating_code_block_vbc_run(
        iters, patches, type_name, skip_validation):
    vbc = DummyValidatingCodeBlock()
    patched = patches(
        "list",
        "CodeBlock.run",
        ("ValidatingCodeBlock.skip_validation",
         dict(new_callable=PropertyMock)),
        "ValidatingCodeBlock._validate",
        prefix="envoy.docs.sphinx_runner.ext.validating_code_block")
    vbc.options = MagicMock()
    vbc.options.get.return_value = type_name
    source = MagicMock()
    line = MagicMock()
    vbc.state_machine = MagicMock()
    vbc.lineno = MagicMock()
    vbc.state_machine.get_source_and_line.return_value = (source, line)

    with patched as (m_list, m_run, m_skip, m_valid):
        m_skip.return_value = skip_validation
        if not type_name:
            with pytest.raises(ExtensionError) as e:
                vbc.run()
        else:
            assert vbc.run() == m_list.return_value

    assert (
        vbc.state_machine.get_source_and_line.call_args
        == [(vbc.lineno, ), {}])
    assert (
        vbc.options.get.call_args
        == [("type-name", ), {}])
    if not type_name:
        assert not m_skip.called
        assert not m_run.called
        assert not m_valid.called
        assert not vbc.options.pop.called
        assert not m_list.called
        assert not m_run.called
        assert (
            e.value.args[0]
            == f"Expected type name in: {source} line: {line}")
        return
    if skip_validation:
        assert not m_valid.called
    else:
        assert (
            m_valid.call_args
            == [(source, line), {}])
    assert (
        vbc.options.pop.call_args
        == [("type-name", None), {}])
    assert (
        m_list.call_args
        == [(m_run.return_value, ), {}])
    assert (
        m_run.call_args
        == [(), {}])


@pytest.mark.parametrize("raises", [None, ParseError, KeyError, Exception])
def test_ext_validating_code_block_vbc__validate(iters, patches, raises):
    vbc = DummyValidatingCodeBlock()
    patched = patches(
        ("ValidatingCodeBlock.proto_validator",
         dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.ext.validating_code_block")
    source = MagicMock()
    line = MagicMock()
    vbc.content = iters()
    vbc.options = MagicMock()

    with patched as (m_valid, ):
        if raises:
            m_valid.return_value.validate_yaml.side_effect = raises(
                "AN ERROR OCCURRED")

        if raises == Exception:
            with pytest.raises(Exception):
                vbc._validate(source, line)
        elif raises:
            with pytest.raises(ExtensionError) as e:
                vbc._validate(source, line)
        else:
            assert not vbc._validate(source, line)

    assert (
        m_valid.return_value.validate_yaml.call_args
        == [("\n".join(vbc.content),
             vbc.options.get.return_value), {}])
    assert (
        vbc.options.get.call_args
        == [("type-name", ), {}])
    if raises and not raises == Exception:
        assert (
            e.value.args[0]
            == ("Failed config validation for type: "
                f"'{vbc.options.get.return_value}' in: {source} line: "
                f"{line}"))
