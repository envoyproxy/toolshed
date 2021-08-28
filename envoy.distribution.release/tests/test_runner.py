
from unittest.mock import MagicMock, PropertyMock

import pytest

from envoy.distribution.release import runner


def _release_arg_props(patches, prop, arg=None):
    run = runner.ReleaseRunner()
    patched = patches(
        ("ReleaseRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.runner")

    with patched as (m_args, ):
        assert getattr(run, prop) == getattr(m_args.return_value, arg or prop)


@pytest.mark.parametrize(
    "props",
    (("continues", "continue"),
     ("repository", ),
     ("user", )))
def test_runner_arg_props(patches, props):
    _release_arg_props(patches, *props)


def test_runner_oauth_token(patches):
    run = runner.ReleaseRunner()
    patched = patches(
        ("ReleaseRunner.oauth_token_file", dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.runner")

    with patched as (m_file, ):
        assert (
            run.oauth_token
            == m_file.return_value.read_text.return_value.strip.return_value)

    assert (
        list(m_file.return_value.read_text.call_args)
        == [(), {}])
    assert (
        list(m_file.return_value.read_text.return_value.strip.call_args)
        == [(), {}])
    assert "oauth_token" not in run.__dict__


def test_runner_oauth_token_file(patches):
    run = runner.ReleaseRunner()
    patched = patches(
        "pathlib",
        ("ReleaseRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.runner")

    with patched as (m_plib, m_args):
        assert (
            run.oauth_token_file
            == m_plib.Path.return_value)

    assert (
        list(m_plib.Path.call_args)
        == [(m_args.return_value.oauth_token_file, ), {}])
    assert "oauth_token_file" not in run.__dict__


def test_runner_add_arguments(patches):
    run = runner.ReleaseRunner()
    parser = MagicMock()
    patched = patches(
        "runner.BaseRunner.add_arguments",
        prefix="envoy.distribution.release.runner")

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
