
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from envoy.github.abstract.runner import AGithubReleaseRunner


@abstracts.implementer(AGithubReleaseRunner)
class DummyGithubReleaseRunner:

    def __init__(self):
        pass

    @property
    def command(self):
        return super().command

    @property
    def commands(self):
        return super().commands

    @property
    def release_manager(self):
        return super().release_manager

    @property
    def release_manager_class(self):
        return super().release_manager_class

    def add_arguments(self, parser):
        return super().add_arguments(parser)

    async def run(self):
        return await super().run()


def _release_arg_props(patches, prop, arg=None):
    run = DummyGithubReleaseRunner()
    patched = patches(
        ("AGithubReleaseRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.runner")

    with patched as (m_args, ):
        assert getattr(run, prop) == getattr(m_args.return_value, arg or prop)


@pytest.mark.parametrize(
    "props",
    (("continues", "continue"),
     ("repository", )))
def test_runner_arg_props(patches, props):
    _release_arg_props(patches, *props)


@pytest.mark.parametrize("token_set", [True, False])
@pytest.mark.parametrize("token_exists", [True, False])
def test_runner_oauth_token(patches, token_set, token_exists):
    run = DummyGithubReleaseRunner()
    patched = patches(
        ("AGithubReleaseRunner.oauth_token_file",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.runner")

    with patched as (m_file, ):
        if not token_set:
            m_file.return_value = None
        elif not token_exists:
            m_file.return_value.exists.return_value = False
        assert (
            run.oauth_token
            == (m_file.return_value.read_text.return_value.strip.return_value
                if token_set and token_exists
                else ""))
    assert "oauth_token" not in run.__dict__
    if not token_set:
        return
    if not token_exists:
        assert not m_file.return_value.read_text.called
        return
    assert (
        list(m_file.return_value.read_text.call_args)
        == [(), {}])
    assert (
        list(m_file.return_value.read_text.return_value.strip.call_args)
        == [(), {}])


@pytest.mark.parametrize("token_set", [True, False])
def test_runner_oauth_token_file(patches, token_set):
    run = DummyGithubReleaseRunner()
    patched = patches(
        "pathlib",
        ("AGithubReleaseRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.runner")

    with patched as (m_plib, m_args):
        if not token_set:
            m_args.return_value.oauth_token_file = None
        assert (
            run.oauth_token_file
            == (m_plib.Path.return_value
                if token_set
                else None))

    assert "oauth_token_file" not in run.__dict__
    if not token_set:
        assert not m_plib.Path.called
        return
    assert (
        list(m_plib.Path.call_args)
        == [(m_args.return_value.oauth_token_file, ), {}])


def test_runner_path(patches):
    run = DummyGithubReleaseRunner()
    patched = patches(
        "pathlib",
        ("AGithubReleaseRunner.tempdir",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.runner")

    with patched as (m_plib, m_tempdir):
        assert run.path == m_plib.Path.return_value

    assert (
        list(m_plib.Path.call_args)
        == [(m_tempdir.return_value.name, ), {}])


def test_runner_release_manager(patches):
    run = DummyGithubReleaseRunner()
    patched = patches(
        ("AGithubReleaseRunner.continues",
         dict(new_callable=PropertyMock)),
        ("AGithubReleaseRunner.log",
         dict(new_callable=PropertyMock)),
        ("AGithubReleaseRunner.oauth_token",
         dict(new_callable=PropertyMock)),
        ("AGithubReleaseRunner.path",
         dict(new_callable=PropertyMock)),
        ("AGithubReleaseRunner.release_manager_class",
         dict(new_callable=PropertyMock)),
        ("AGithubReleaseRunner.repository",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.runner")

    with patched as (m_continues, m_log, m_token, m_path, m_class, m_repo):
        assert run.release_manager == m_class.return_value.return_value

    assert (
        list(m_class.return_value.call_args)
        == [(m_path.return_value,
             m_repo.return_value),
            {'log': m_log.return_value,
             'oauth_token': m_token.return_value,
             'continues': m_continues.return_value}])


def test_runner_add_arguments(patches):
    run = DummyGithubReleaseRunner()
    parser = MagicMock()
    patched = patches(
        "runner.BaseRunner.add_arguments",
        prefix="envoy.github.abstract.runner")

    with patched as (m_super, ):
        run.add_arguments(parser)

    assert (
        list(m_super.call_args)
        == [(parser, ), {}])
    assert (
        list(list(c) for c in parser.add_argument.call_args_list)
        == [[('repository',),
             {'help': 'Github repository'}],
            [('oauth_token_file',),
             {'help': 'Path to an OAuth token credentials file'}],
            [('--continue',),
             {'action': 'store_true',
              'help': 'Continue if an indidividual github action fails'}],
            [('command',), {'choices': {}.keys(), 'help': 'Command to run'}]])


@pytest.mark.asyncio
@pytest.mark.parametrize("indict", [True, False])
async def test_runner_cleanup(patches, indict):
    run = DummyGithubReleaseRunner()
    patched = patches(
        ("AGithubReleaseRunner.release_manager",
         dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.runner")

    if indict:
        run.__dict__["release_manager"] = "RELEASE MANAGER"

    with patched as (m_manager, ):
        m_manager.return_value.close = AsyncMock()
        await run.cleanup()

    assert "release_manager" not in run.__dict__
    if indict:
        assert (
            list(m_manager.return_value.close.call_args)
            == [(), {}])
    else:
        assert not m_manager.return_value.close.called
