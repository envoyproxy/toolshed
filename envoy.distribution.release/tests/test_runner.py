
from unittest.mock import AsyncMock, PropertyMock

import pytest

from envoy.distribution.release import runner
from envoy.github.abstract import AGithubReleaseRunner
from envoy.github.release.manager import GithubReleaseManager


def test_runner_constructor():
    run = runner.ReleaseRunner()
    isinstance(run, AGithubReleaseRunner)
    assert run.release_manager_class == GithubReleaseManager


@pytest.mark.parametrize("prop", ["command", "commands", "release_manager"])
def test_runner_super_props(patches, prop):
    run = runner.ReleaseRunner()
    patched = patches(
        (f"AGithubReleaseRunner.{prop}",
         dict(new_callable=PropertyMock)),
        prefix="envoy.distribution.release.runner")

    with patched as (m_prop, ):
        assert getattr(run, prop) == m_prop.return_value

    assert prop in run.__dict__


def test_runner_add_arguments(patches):
    run = runner.ReleaseRunner()
    patched = patches(
        "AGithubReleaseRunner.add_arguments",
        prefix="envoy.distribution.release.runner")

    with patched as (m_args, ):
        assert not run.add_arguments("PARSER")

    assert (
        list(m_args.call_args)
        == [("PARSER", ), {}])


@pytest.mark.asyncio
async def test_runner_run(patches):
    run = runner.ReleaseRunner()
    patched = patches(
        ("AGithubReleaseRunner.run",
         dict(new_callable=AsyncMock)),
        prefix="envoy.distribution.release.runner")

    with patched as (m_super, ):
        assert await run.run() == m_super.return_value
