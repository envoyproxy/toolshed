
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import packaging.version

from aio.core.functional import async_property

from envoy.github.abstract import exceptions
from envoy.github.action import GithubActionManager


@pytest.mark.parametrize("continues", [None, True, False])
@pytest.mark.parametrize("create", [None, True, False])
@pytest.mark.parametrize("user", [None, "USER"])
@pytest.mark.parametrize("oauth_token", [None, "OAUTH TOKEN"])
@pytest.mark.parametrize("log", [None, "LOG"])
@pytest.mark.parametrize("asset_types", [None, "ASSET TYPES"])
@pytest.mark.parametrize("github", [None, "GITHUB"])
@pytest.mark.parametrize("session", [None, "SESSION"])
def test_action_manager_constructor(
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
    actionr = GithubActionManager("PATH", "REPOSITORY", **kwargs)
    assert actionr._path == "PATH"
    assert actionr.repository == "REPOSITORY"
    assert (
        actionr.continues
        == (continues
            if continues is not None
            else False))
    assert (
        actionr.create
        == (create
            if create is not None
            else True))
    assert actionr._log == log
    assert actionr.oauth_token == oauth_token
    assert actionr.user == (user or "")
    assert actionr._asset_types == asset_types
    assert actionr._github == github
    assert actionr._session == session

    assert actionr._version_re == r"v(\w+)"


async def test_action_manager_async_contextmanager(patches):
    patched = patches(
        ("GithubActionManager.close", dict(new_callable=AsyncMock)),
        prefix="envoy.github.action.manager")

    with patched as (m_close, ):
        action_manager = GithubActionManager("PATH", "REPOSITORY")
        async with action_manager as actionr:
            assert isinstance(actionr, GithubActionManager)
            assert not m_close.called
        assert (
            m_close.call_args
            == [(), {}])


def test_action_manager_dunder_getitem(patches):
    actionr = GithubActionManager("PATH", "REPOSITORY")
    patched = patches(
        "GithubAction",
        prefix="envoy.github.action.manager")

    with patched as (m_action, ):
        assert actionr["X.Y.Z"] == m_action.return_value

    assert (
        m_action.call_args
        == [(actionr, "X.Y.Z"), {}])


@pytest.mark.parametrize("oauth_token", [None, "OAUTH_TOKEN"])
@pytest.mark.parametrize("user", [None, "USER"])
@pytest.mark.parametrize("github", [True, False])
def test_action_manager_github(patches, oauth_token, user, github):
    kwargs = {}
    if oauth_token:
        kwargs["oauth_token"] = oauth_token
    if user:
        kwargs["user"] = user
    if github:
        kwargs["github"] = "GITHUB"
    actionr = GithubActionManager("PATH", "REPOSITORY", **kwargs)
    patched = patches(
        "gidgethub",
        ("GithubActionManager.session", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.manager")

    with patched as (m_api, m_session):
        assert (
            actionr.github
            == (m_api.aiohttp.GitHubAPI.return_value
                if not github
                else "GITHUB"))

    assert "github" in actionr.__dict__
    if github:
        assert not m_api.aiohttp.GitHubAPI.called
        return
    assert (
        m_api.aiohttp.GitHubAPI.call_args
        == [(m_session.return_value, user or ""),
            {'oauth_token': oauth_token}])


@pytest.mark.parametrize("log", [True, False])
def test_action_manager_log(patches, log):
    actionr = GithubActionManager("PATH", "REPOSITORY")
    patched = patches(
        "verboselogs",
        prefix="envoy.github.action.manager")
    if log:
        actionr._log = "LOG"

    with patched as (m_log, ):
        assert (
            actionr.log
            == (m_log.VerboseLogger.return_value
                if not log
                else "LOG"))

    assert "log" in actionr.__dict__

    if log:
        assert not m_log.VerboseLogger.called
        return

    assert (
        m_log.VerboseLogger.call_args
        == [('envoy.github.action.manager',), {}])


def test_action_manager_path(patches):
    actionr = GithubActionManager("PATH", "REPOSITORY")
    patched = patches(
        "pathlib",
        prefix="envoy.github.action.manager")

    with patched as (m_plib, ):
        assert (
            actionr.path
            == m_plib.Path.return_value)

    assert "path" in actionr.__dict__
    assert (
        m_plib.Path.call_args
        == [('PATH',), {}])


async def test_action_manager_latest(patches):
    actionr = GithubActionManager("PATH", "REPOSITORY")
    patched = patches(
        "GithubActionManager.parse_version",
        ("GithubActionManager.actions", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.manager")

    _versions = [
        dict(tag_name=v)
        for v
        in ("1.19.2", "X", "1.19.1", "Y_Z", "1.20.3", "", "0.0.1")]

    with patched as (m_version, m_actions):
        m_version.side_effect = (
            lambda version: (
                packaging.version.Version(version)
                if "." in version
                else None))
        m_actions.side_effect = AsyncMock(return_value=_versions)
        result = await actionr.latest

    assert (
        result
        == {'0.0.1': packaging.version.Version('0.0.1'),
            '0.0': packaging.version.Version('0.0.1'),
            '1.19.2': packaging.version.Version('1.19.2'),
            '1.19': packaging.version.Version('1.19.2'),
            '1.19.1': packaging.version.Version('1.19.1'),
            '1.20.3': packaging.version.Version('1.20.3'),
            '1.20': packaging.version.Version('1.20.3')})
    assert not hasattr(actionr, "__async_prop_cache__")


async def test_action_manager_actions(patches):
    actionr = GithubActionManager("PATH", "REPOSITORY")
    patched = patches(
        ("GithubActionManager.github", dict(new_callable=PropertyMock)),
        ("GithubActionManager.actions_url", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.manager")
    getiter_mock = MagicMock()

    async def getiter(url):
        getiter_mock(url)
        for i in range(0, 5):
            yield i

    with patched as (m_github, m_actions):
        m_github.return_value.getiter = getiter
        assert await actionr.actions == list(range(0, 5))

    assert (
        getiter_mock.call_args
        == [(str(m_actions.return_value), ), {}])
    assert not hasattr(actionr, async_property.cache_name)


def test_action_manager_actions_url(patches):
    actionr = GithubActionManager("PATH", "REPOSITORY")
    patched = patches(
        "pathlib",
        prefix="envoy.github.action.manager")

    with patched as (m_plib, ):
        assert actionr.actions_url == m_plib.PurePosixPath.return_value

    assert (
        m_plib.PurePosixPath.call_args
        == [("/repos/REPOSITORY/actions", ), {}])
    assert "actions_url" in actionr.__dict__


@pytest.mark.parametrize("session", [True, False])
def test_action_manager_session(patches, session):
    actionr = GithubActionManager("PATH", "REPOSITORY")
    patched = patches(
        "aiohttp",
        prefix="envoy.github.action.manager")
    if session:
        actionr._session = "SESSION"

    with patched as (m_http, ):
        assert (
            actionr.session
            == (m_http.ClientSession.return_value
                if not session
                else "SESSION"))

    assert "session" in actionr.__dict__
    if session:
        assert not m_http.ClientSession.called
        return
    assert (
        m_http.ClientSession.call_args
        == [(), {}])


def test_action_manager_version_re(patches):
    actionr = GithubActionManager("PATH", "REPOSITORY")
    patched = patches(
        "re",
        prefix="envoy.github.action.manager")
    actionr._version_re = "VERSION RE"

    with patched as (m_re, ):
        assert actionr.version_re == m_re.compile.return_value

    assert (
        m_re.compile.call_args
        == [("VERSION RE", ), {}])


@pytest.mark.parametrize("session", [True, False])
async def test_action_manager_close(patches, session):
    actionr = GithubActionManager("PATH", "REPOSITORY")
    patched = patches(
        ("GithubActionManager.session", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.manager")

    if session:
        actionr.__dict__["session"] = "SESSION"

    with patched as (m_session, ):
        m_session.return_value.close = AsyncMock()
        assert not await actionr.close()

    assert "session" not in actionr.__dict__

    if not session:
        assert not m_session.called
        return

    assert (
        m_session.return_value.close.call_args
        == [(), {}])


@pytest.mark.parametrize("continues", [True, False])
def test_action_manager_fail(patches, continues):
    actionr = GithubActionManager(
        "PATH", "REPOSITORY", continues=continues)
    patched = patches(
        ("GithubActionManager.log", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.manager")

    with patched as (m_log, ):
        if continues:
            assert (
                actionr.fail("MESSAGE")
                == "MESSAGE")
        else:
            with pytest.raises(exceptions.GithubActionError):
                actionr.fail("MESSAGE")

    if not continues:
        assert not m_log.return_value.warning.called
        return

    assert (
        m_log.return_value.warning.call_args
        == [("MESSAGE", ), {}])


def test_action_manager_format_version():
    actionr = GithubActionManager("PATH", "REPOSITORY")
    actionr._version_format = MagicMock()
    assert (
        actionr.format_version("VERSION")
        == actionr._version_format.format.return_value)
    assert (
        actionr._version_format.format.call_args
        == [(), dict(version="VERSION")])


@pytest.mark.parametrize("version", [None, 0, "", "1.2.3"])
@pytest.mark.parametrize(
    "raises",
    [None, BaseException, packaging.version.InvalidVersion])
def test_action_manager_parse_version(patches, version, raises):
    actionr = GithubActionManager("PATH", "REPOSITORY")
    patched = patches(
        "packaging.version.Version",
        ("GithubActionManager.log", dict(new_callable=PropertyMock)),
        ("GithubActionManager.version_re", dict(new_callable=PropertyMock)),
        prefix="envoy.github.action.manager")

    with patched as (m_packaging, m_log, m_version):
        m_version.return_value.sub.return_value = version
        if raises:
            m_packaging.side_effect = raises()

        if version and raises == BaseException:
            with pytest.raises(BaseException):
                actionr.parse_version("VERSION")
        else:
            assert (
                actionr.parse_version("VERSION")
                == (None
                    if not version or raises
                    else m_packaging.return_value))

    assert (
        m_version.return_value.sub.call_args
        == [(r"\1", "VERSION"), {}])
    if version:
        assert (
            m_packaging.call_args
            == [(m_version.return_value.sub.return_value, ), {}])
    else:
        assert not m_packaging.called

    if not version or raises and raises != BaseException:
        assert (
            m_log.return_value.warning.call_args
            == [("Unable to parse version: VERSION", ), {}])
    else:
        assert not m_log.called
