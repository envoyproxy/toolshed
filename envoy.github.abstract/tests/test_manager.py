
from unittest.mock import AsyncMock, PropertyMock

import pytest

import packaging.version

import abstracts

from aio.functional import async_property
from envoy.github.abstract import manager


@abstracts.implementer(manager.AGithubReleaseManager)
class DummyGithubReleaseManager:

    async def __aenter__(self):
        return super().__aenter__()

    async def __aexit__(self, *args):
        return super().__aexit__(*args)

    def __getitem__(self, version):
        return super().__getitem__(version)

    @property
    def github(self):
        return super().github

    @async_property
    async def latest(self):
        return super().latest

    @property
    def log(self):
        return super().log

    @async_property
    async def releases(self):
        return super().releases

    @async_property
    def releases_url(self):
        return super().releases_url

    @property
    def session(self):
        return super().session

    def fail(self, message):
        return super().fail(message)

    def format_version(self, version):
        return super().format_version(version)

    def parse_version(self, version):
        return super().parse_version(version)


@pytest.mark.parametrize("continues", [None, True, False])
@pytest.mark.parametrize("create", [None, True, False])
@pytest.mark.parametrize("user", [None, "USER"])
@pytest.mark.parametrize("oauth_token", [None, "OAUTH TOKEN"])
@pytest.mark.parametrize("log", [None, "LOG"])
@pytest.mark.parametrize("asset_types", [None, "ASSET TYPES"])
@pytest.mark.parametrize("github", [None, "GITHUB"])
@pytest.mark.parametrize("session", [None, "SESSION"])
def test_release_manager_constructor(
        continues, create, user, oauth_token,
        log, asset_types, github, session):
    kwargs = dict(
        continues=continues,
        create=create,
        user=user,
        oauth_token=oauth_token,
        log=log,
        asset_types=asset_types,
        github=github,
        session=session)
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    releaser = DummyGithubReleaseManager("PATH", "REPOSITORY", **kwargs)
    assert releaser._path == "PATH"
    assert releaser.repository == "REPOSITORY"
    assert (
        releaser.continues
        == (continues
            if continues is not None
            else False))
    assert (
        releaser.create
        == (create
            if create is not None
            else True))
    assert releaser._log == log
    assert releaser.oauth_token == oauth_token
    assert releaser.user == (user or "")
    assert releaser._asset_types == asset_types
    assert releaser._github == github
    assert releaser._session == session

    # assert releaser._version_re == r"v(\w+)"
    assert (
        releaser.version_min
        == manager.VERSION_MIN
        == packaging.version.Version("0"))
    assert "version_min" not in releaser.__dict__


@pytest.mark.parametrize("session", [True, False])
async def test_release_manager_close(patches, session):
    releaser = DummyGithubReleaseManager("PATH", "REPOSITORY")
    patched = patches(
        ("AGithubReleaseManager.session", dict(new_callable=PropertyMock)),
        prefix="envoy.github.abstract.manager")

    if session:
        releaser.__dict__["session"] = "SESSION"

    with patched as (m_session, ):
        m_session.return_value.close = AsyncMock()
        assert not await releaser.close()

    assert "session" not in releaser.__dict__
