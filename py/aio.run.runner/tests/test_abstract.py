
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio.run.runner import (
    ACommand, ARunnerWithCommands, ICommand, Runner)


@abstracts.implementer(ACommand)
class DummyCommand:

    @property
    def parser(self):
        return super().parser

    def add_arguments(self, parser):
        super().add_arguments(parser)

    async def run(self):
        return await super().run()


def test_command_constructor():
    base = DummyCommand("CONTEXT")
    assert base.context == "CONTEXT"


async def test_command_run():
    base = DummyCommand("CONTEXT")

    with pytest.raises(NotImplementedError):
        await base.run()


def test_command_args(patches):
    context = MagicMock()
    base = DummyCommand(context)
    patched = patches(
        ("ACommand.parser", dict(new_callable=PropertyMock)),
        prefix="aio.run.runner.abstract")

    with patched as (m_parser, ):
        known_args = m_parser.return_value.parse_known_args
        assert (
            base.args
            == known_args.return_value.__getitem__.return_value)

    assert (
        known_args.call_args
        == [(context.extra_args, ), {}])
    assert (
        known_args.return_value.__getitem__.call_args
        == [(0, ), {}])


def test_command_extra_args(patches):
    context = MagicMock()
    base = DummyCommand(context)
    patched = patches(
        ("ACommand.parser", dict(new_callable=PropertyMock)),
        prefix="aio.run.runner.abstract")

    with patched as (m_parser, ):
        known_args = m_parser.return_value.parse_known_args
        assert (
            base.extra_args
            == known_args.return_value.__getitem__.return_value)

    assert (
        known_args.call_args
        == [(context.extra_args, ), {}])
    assert (
        known_args.return_value.__getitem__.call_args
        == [(1, ), {}])


def test_command_parser(patches):
    base = DummyCommand("CONTEXT")
    patched = patches(
        "argparse",
        "ACommand.add_arguments",
        prefix="aio.run.runner.abstract")

    with patched as (m_argparse, m_addargs):
        assert (
            base.parser
            == m_argparse.ArgumentParser.return_value)

    assert (
        m_argparse.ArgumentParser.call_args
        == [(), dict(allow_abbrev=False)])
    assert (
        m_addargs.call_args
        == [(m_argparse.ArgumentParser.return_value, ), {}])


def test_command_add_arguments():
    base = DummyCommand("CONTEXT")
    with pytest.raises(NotImplementedError):
        base.add_arguments("PARSER")


async def test_icommand():

    @abstracts.implementer(ICommand)
    class DummyCommand:

        async def run(self):
            return "RAN"

    icommand = DummyCommand()
    assert await icommand.run() == "RAN"

    with pytest.raises(NotImplementedError):
        await ICommand.run(icommand)


def test_acommand():
    assert issubclass(ACommand, ICommand)
    assert issubclass(ACommand, ACommand)


@abstracts.implementer(ARunnerWithCommands)
class DummyRunnerWithCommands:

    def __init__(self):
        pass

    @property
    def command(self):
        return super().command

    @property
    def commands(self):
        return super().commands

    async def run(self):
        return await super().run()


def test_commandrunner_constructor():
    runner = DummyRunnerWithCommands()
    assert isinstance(runner, Runner)
    assert runner._commands == ()


def test_commandrunner_register_command():
    assert DummyRunnerWithCommands._commands == ()

    class Command1(object):
        pass

    class Command2(object):
        pass

    DummyRunnerWithCommands.register_command("command1", Command1)
    assert (
        DummyRunnerWithCommands._commands
        == (('command1', Command1),))

    DummyRunnerWithCommands.register_command("command2", Command2)
    assert (
        DummyRunnerWithCommands._commands
        == (('command1', Command1),
            ('command2', Command2),))


def test_commandrunner_command(patches):
    runner = DummyRunnerWithCommands()
    patched = patches(
        ("ARunnerWithCommands.args",
         dict(new_callable=PropertyMock)),
        ("ARunnerWithCommands.commands",
         dict(new_callable=PropertyMock)),
        prefix="aio.run.runner.abstract")

    with patched as (m_args, m_commands):
        assert (
            runner.command
            == m_commands.return_value.__getitem__.return_value.return_value)

    assert (
        m_commands.return_value.__getitem__.call_args
        == [(m_args.return_value.command, ), {}])
    assert (
        m_commands.return_value.__getitem__.return_value.call_args
        == [(runner, ), {}])


def test_commandrunner_commands():
    runner = DummyRunnerWithCommands()
    runner._commands = (("A", "aaa"), ("B", "bbb"))
    assert (
        runner.commands
        == {'A': 'aaa', 'B': 'bbb'})


async def test_commandrunner_run(patches):
    runner = DummyRunnerWithCommands()
    patched = patches(
        ("ARunnerWithCommands.command",
         dict(new_callable=PropertyMock)),
        prefix="aio.run.runner.abstract")

    with patched as (m_cmd, ):
        cmd_run = AsyncMock()
        m_cmd.return_value.run = cmd_run
        assert (
            await runner.run()
            == cmd_run.return_value)

    assert (
        cmd_run.call_args
        == [(), {}])
