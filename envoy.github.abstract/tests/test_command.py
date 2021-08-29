
from unittest.mock import MagicMock, PropertyMock

import pytest

import abstracts

from envoy.abstract.command import AAsyncCommand
from envoy.github.abstract.command import AGithubReleaseCommand


@abstracts.implementer(AGithubReleaseCommand)
class DummyGithubReleaseCommand:

    async def run(self):
        return await super().run()


@pytest.mark.asyncio
async def test_release_command_constructor():
    command = DummyGithubReleaseCommand("CONTEXT")
    assert isinstance(command, AAsyncCommand)

    assert command.runner == "CONTEXT"
    assert "runner" not in command.__dict__

    with pytest.raises(NotImplementedError):
        await command.run()


def test_release_command_manager(patches):
    command = DummyGithubReleaseCommand("CONTEXT")
    patched = patches(
        ("AGithubReleaseCommand.runner",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.command")

    with patched as (m_runner, ):
        assert command.manager == m_runner.return_value.release_manager

    assert "manager" in command.__dict__


def test_release_command_parser(patches):
    command = DummyGithubReleaseCommand("CONTEXT")
    patched = patches(
        ("command.AAsyncCommand.parser",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.command")

    with patched as (m_super, ):
        assert command.parser == m_super.return_value

    assert "parser" in command.__dict__


def test_release_command_release(patches):
    command = DummyGithubReleaseCommand("CONTEXT")
    patched = patches(
        ("AGithubReleaseCommand.manager",
         dict(new_callable=PropertyMock)),
        ("AGithubReleaseCommand.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.command")

    with patched as (m_manager, m_version):
        assert (
            command.release
            == m_manager.return_value.__getitem__.return_value)

    assert (
        list(m_manager.return_value.__getitem__.call_args)
        == [(m_version.return_value, ), {}])
    assert "release" in command.__dict__


def test_release_command_version(patches):
    command = DummyGithubReleaseCommand("CONTEXT")
    patched = patches(
        ("AGithubReleaseCommand.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.command")

    with patched as (m_args, ):
        assert command.version == m_args.return_value.version

    assert "version" not in command.__dict__


def test_release_command_add_arguments():
    command = DummyGithubReleaseCommand("CONTEXT")
    parser = MagicMock()
    assert not command.add_arguments(parser)
    assert (
        list(list(c) for c in parser.add_argument.call_args_list)
        == [[("version", ), dict(help="Github release version")]])
