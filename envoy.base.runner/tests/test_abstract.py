
from unittest.mock import AsyncMock, PropertyMock

import abstracts

from envoy.base.runner import (
    AsyncRunner, AAsyncRunnerWithCommands)


@abstracts.implementer(AAsyncRunnerWithCommands)
class DummyAsyncRunnerWithCommands:

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


def test_async_commandrunner_constructor():
    runner = DummyAsyncRunnerWithCommands()
    assert isinstance(runner, AsyncRunner)
    assert runner._commands == ()


def test_async_commandrunner_register_command():
    assert DummyAsyncRunnerWithCommands._commands == ()

    class Command1(object):
        pass

    class Command2(object):
        pass

    DummyAsyncRunnerWithCommands.register_command("command1", Command1)
    assert (
        DummyAsyncRunnerWithCommands._commands
        == (('command1', Command1),))

    DummyAsyncRunnerWithCommands.register_command("command2", Command2)
    assert (
        DummyAsyncRunnerWithCommands._commands
        == (('command1', Command1),
            ('command2', Command2),))


def test_async_commandrunner_command(patches):
    runner = DummyAsyncRunnerWithCommands()
    patched = patches(
        ("AAsyncRunnerWithCommands.args",
         dict(new_callable=PropertyMock)),
        ("AAsyncRunnerWithCommands.commands",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.runner.abstract")

    with patched as (m_args, m_commands):
        assert (
            runner.command
            == m_commands.return_value.__getitem__.return_value.return_value)

    assert (
        list(m_commands.return_value.__getitem__.call_args)
        == [(m_args.return_value.command, ), {}])
    assert (
        list(m_commands.return_value.__getitem__.return_value.call_args)
        == [(runner, ), {}])


def test_async_commandrunner_commands():
    runner = DummyAsyncRunnerWithCommands()
    runner._commands = (("A", "aaa"), ("B", "bbb"))
    assert (
        runner.commands
        == {'A': 'aaa', 'B': 'bbb'})


async def test_async_commandrunner_run(patches):
    runner = DummyAsyncRunnerWithCommands()
    patched = patches(
        ("AAsyncRunnerWithCommands.command",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.runner.abstract")

    with patched as (m_cmd, ):
        cmd_run = AsyncMock()
        m_cmd.return_value.run = cmd_run
        assert (
            await runner.run()
            == cmd_run.return_value)

    assert (
        list(cmd_run.call_args)
        == [(), {}])
