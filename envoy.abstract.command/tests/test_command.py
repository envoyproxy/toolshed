
from unittest.mock import MagicMock, PropertyMock

import pytest

import abstracts

from envoy.abstract import command


@abstracts.implementer(command.ABaseCommand)
class DummyBaseCommand:

    @property
    def parser(self):
        return super().parser

    def add_arguments(self, parser):
        super().add_arguments(parser)


def test_base_command_constructor():
    base = DummyBaseCommand("CONTEXT")
    assert base.context == "CONTEXT"


def test_base_command_args(patches):
    context = MagicMock()
    base = DummyBaseCommand(context)
    patched = patches(
        ("ABaseCommand.parser", dict(new_callable=PropertyMock)),
        prefix="envoy.abstract.command.command")

    with patched as (m_parser, ):
        known_args = m_parser.return_value.parse_known_args
        assert (
            base.args
            == known_args.return_value.__getitem__.return_value)

    assert (
        list(known_args.call_args)
        == [(context.extra_args, ), {}])
    assert (
        list(known_args.return_value.__getitem__.call_args)
        == [(0, ), {}])


def test_base_command_extra_args(patches):
    context = MagicMock()
    base = DummyBaseCommand(context)
    patched = patches(
        ("ABaseCommand.parser", dict(new_callable=PropertyMock)),
        prefix="envoy.abstract.command.command")

    with patched as (m_parser, ):
        known_args = m_parser.return_value.parse_known_args
        assert (
            base.extra_args
            == known_args.return_value.__getitem__.return_value)

    assert (
        list(known_args.call_args)
        == [(context.extra_args, ), {}])
    assert (
        list(known_args.return_value.__getitem__.call_args)
        == [(1, ), {}])


def test_base_command_parser(patches):
    base = DummyBaseCommand("CONTEXT")
    patched = patches(
        "argparse",
        "ABaseCommand.add_arguments",
        prefix="envoy.abstract.command.command")

    with patched as (m_argparse, m_addargs):
        assert (
            base.parser
            == m_argparse.ArgumentParser.return_value)

    assert (
        list(m_argparse.ArgumentParser.call_args)
        == [(), dict(allow_abbrev=False)])
    assert (
        list(m_addargs.call_args)
        == [(m_argparse.ArgumentParser.return_value, ), {}])


def test_base_command_add_arguments():
    base = DummyBaseCommand("CONTEXT")
    with pytest.raises(NotImplementedError):
        base.add_arguments("PARSER")


def test_icommand():

    @abstracts.implementer(command.ICommand)
    class DummyCommand:

        def run(self):
            return "RAN"

    icommand = DummyCommand()
    assert icommand.run() == "RAN"

    with pytest.raises(NotImplementedError):
        command.ICommand.run(icommand)


async def test_iasynccommand():

    @abstracts.implementer(command.ICommand)
    class DummyCommand:

        async def run(self):
            return "RAN"

    icommand = DummyCommand()
    assert await icommand.run() == "RAN"

    with pytest.raises(NotImplementedError):
        await command.ICommand.run(icommand)


def test_acommand():
    assert issubclass(command.ACommand, command.ICommand)
    assert issubclass(command.ACommand, command.ABaseCommand)


def test_aasynccommand():
    assert issubclass(command.AAsyncCommand, command.IAsyncCommand)
    assert issubclass(command.AAsyncCommand, command.ABaseCommand)
