
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import gidgethub

import abstracts

from aio.api import github
from aio.core import event

from envoy.dependency.check import ADependencyGithubRelease


@abstracts.implementer(ADependencyGithubRelease)
class DummyDependencyGithubRelease:
    pass


@pytest.mark.parametrize("asset_url", [None, "", "ASSET_URL"])
@pytest.mark.parametrize("loop", [None, "", "LOOP"])
@pytest.mark.parametrize("pool", [None, "", "POOL"])
@pytest.mark.parametrize("gh_release", [None, "", "RELEASE"])
def test_release_constructor(asset_url, loop, pool, gh_release):
    kwargs = {}
    if asset_url is not None:
        kwargs["asset_url"] = asset_url
    if loop is not None:
        kwargs["loop"] = loop
    if pool is not None:
        kwargs["pool"] = pool
    if gh_release is not None:
        kwargs["release"] = gh_release
    release = DummyDependencyGithubRelease("REPO", "VERSION", **kwargs)
    assert release.repo == "REPO"
    assert release._version == "VERSION"
    assert release.tag_name == "VERSION"
    assert release.asset_url == asset_url
    assert release._release == gh_release
    assert release._loop == loop
    assert release._pool == pool
    assert "tag_name" not in release.__dict__
    assert isinstance(release, event.IReactive)


@pytest.mark.parametrize(
    "raises",
    [None, Exception, gidgethub.BadRequest])
@pytest.mark.parametrize("err", ["", "SOMETHING ELSE", "Not Found"])
async def test_release_commit(patches, raises, err):
    repo = AsyncMock()
    if raises:
        msg = MagicMock()
        msg.phrase = err
        error = raises(msg)
        repo.commit.side_effect = error
    release = DummyDependencyGithubRelease(repo, "VERSION")
    patched = patches(
        ("ADependencyGithubRelease.tag_name",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.release")
    should_fail = (
        raises
        and not (raises == gidgethub.BadRequest
                 and err == "Not Found"))

    with patched as (m_tagname, ):
        if should_fail:
            with pytest.raises(raises):
                await release.commit
        else:
            result = await release.commit
            assert (
                result
                == (repo.commit.return_value
                    if not raises
                    else None))
    assert (
        repo.commit.call_args
        == [(m_tagname.return_value, ), {}])

    if not should_fail:
        assert (
            getattr(
                release,
                ADependencyGithubRelease.commit.cache_name)[
                    "commit"]
            == result)


async def test_release_date(patches):
    release = DummyDependencyGithubRelease("REPO", "VERSION")
    patched = patches(
        "utils",
        ("ADependencyGithubRelease.timestamp",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.release")

    with patched as (m_utils, m_timestamp):
        m_timestamp.side_effect = AsyncMock(return_value=23)
        result = await release.date
        assert (
            result
            == m_utils.dt_to_utc_isoformat.return_value)

    assert (
        m_utils.dt_to_utc_isoformat.call_args
        == [(23, ), {}])
    assert (
        getattr(
            release,
            ADependencyGithubRelease.date.cache_name)[
                "date"]
        == result)


def test_release_github():
    repo = MagicMock()
    release = DummyDependencyGithubRelease(repo, "VERSION")
    assert release.github == repo.github
    assert "github" not in release.__dict__


@pytest.mark.parametrize(
    "raises",
    [None, Exception, gidgethub.BadRequest])
@pytest.mark.parametrize("provided", [True, False])
@pytest.mark.parametrize("err", ["", "SOMETHING ELSE", "Not Found"])
async def test_release_release(patches, raises, err, provided):
    repo = AsyncMock()
    if raises:
        msg = MagicMock()
        msg.phrase = err
        error = raises(msg)
        repo.release.side_effect = error
    kwargs = {}
    if provided:
        kwargs["release"] = MagicMock()
    release = DummyDependencyGithubRelease(repo, "VERSION", **kwargs)
    patched = patches(
        ("ADependencyGithubRelease.tag_name",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.release")
    should_fail = (
        raises
        and not provided
        and not (raises == gidgethub.BadRequest
                 and err == "Not Found"))

    with patched as (m_tagname, ):
        if should_fail:
            with pytest.raises(raises):
                await release.release
        else:
            result = await release.release

    if not should_fail:
        if provided:
            assert result == kwargs["release"]
        else:
            assert (
                result
                == (repo.release.return_value
                    if not raises
                    else None))
        assert (
            getattr(
                release,
                ADependencyGithubRelease.release.cache_name)[
                    "release"]
            == result)
    if not provided:
        assert (
            repo.release.call_args
            == [(m_tagname.return_value, ), {}])
    else:
        assert not repo.release.called


@pytest.mark.parametrize(
    "raises",
    [None, Exception, gidgethub.BadRequest, github.exceptions.TagNotFound])
@pytest.mark.parametrize("err", ["", "SOMETHING ELSE", "Not Found"])
async def test_release_tag(patches, raises, err):
    repo = AsyncMock()
    if raises:
        msg = MagicMock()
        msg.phrase = err
        error = raises(msg)
        repo.tag.side_effect = error
    release = DummyDependencyGithubRelease(repo, "VERSION")
    patched = patches(
        ("ADependencyGithubRelease.tag_name",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.release")
    should_fail = (
        raises
        and not (raises == gidgethub.BadRequest
                 and err == "Not Found")
        and not raises == github.exceptions.TagNotFound)

    with patched as (m_tagname, ):
        if should_fail:
            with pytest.raises(raises):
                await release.tag
        else:
            result = await release.tag
    if not should_fail:
        assert (
            result
            == (repo.tag.return_value
                if not raises
                else None))
        assert (
            getattr(
                release,
                ADependencyGithubRelease.tag.cache_name)[
                    "tag"]
            == result)
    assert (
        repo.tag.call_args
        == [(m_tagname.return_value, ), {}])


def test_release_session(patches):
    release = DummyDependencyGithubRelease("REPO", "VERSION")
    patched = patches(
        ("ADependencyGithubRelease.github",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.release")

    with patched as (m_github, ):
        assert release.session == m_github.return_value.api._session

    assert "session" not in release.__dict__


@pytest.mark.parametrize("is_sha", [True, False])
def test_release_tagged(patches, is_sha):
    release = DummyDependencyGithubRelease("REPO", "VERSION")
    patched = patches(
        "utils",
        ("ADependencyGithubRelease.tag_name",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.release")

    with patched as (m_utils, m_tagname):
        m_utils.is_sha.return_value = is_sha
        assert release.tagged == (not is_sha)

    assert (
        m_utils.is_sha.call_args
        == [(m_tagname.return_value, ), {}])
    assert "tagged" in release.__dict__


@pytest.mark.parametrize("tagged", [True, False])
async def test_release_timestamp(patches, tagged):
    release = DummyDependencyGithubRelease("REPO", "VERSION")
    patched = patches(
        ("ADependencyGithubRelease.tagged",
         dict(new_callable=PropertyMock)),
        ("ADependencyGithubRelease.timestamp_commit",
         dict(new_callable=PropertyMock)),
        ("ADependencyGithubRelease.timestamp_tag",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.release")
    tcommit = AsyncMock()
    ttag = AsyncMock()

    with patched as (m_tagged, m_tcommit, m_ttag):
        m_tagged.return_value = tagged
        m_tcommit.side_effect = tcommit
        m_ttag.side_effect = ttag
        result = await release.timestamp
        assert (
            result
            == (ttag.return_value
                if tagged
                else tcommit.return_value))

    assert (
        getattr(
            release,
            ADependencyGithubRelease.timestamp.cache_name)[
                "timestamp"]
        == result)


async def test_release_timestamp_commit(patches):
    release = DummyDependencyGithubRelease("REPO", "VERSION")
    patched = patches(
        ("ADependencyGithubRelease.commit",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.release")

    with patched as (m_commit, ):
        commit = AsyncMock()
        m_commit.side_effect = commit
        result = await release.timestamp_commit
    assert (
        result
        == commit.return_value.timestamp)

    assert (
        getattr(
            release,
            ADependencyGithubRelease.timestamp_commit.cache_name)[
                "timestamp_commit"]
        == result)


@pytest.mark.parametrize("has_release", [True, False])
@pytest.mark.parametrize("has_tag", [True, False])
async def test_release_timestamp_tag(patches, has_release, has_tag):
    release = DummyDependencyGithubRelease("REPO", "VERSION")
    patched = patches(
        ("ADependencyGithubRelease.release",
         dict(new_callable=PropertyMock)),
        ("ADependencyGithubRelease.tag",
         dict(new_callable=PropertyMock)),
        ("ADependencyGithubRelease.timestamp_commit",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.release")
    git_release = AsyncMock()
    if not has_release:
        git_release.return_value = None
    git_tag = AsyncMock()
    if not has_tag:
        git_tag.return_value = None
    else:
        git_commit = AsyncMock()
        type(git_tag.return_value).commit = PropertyMock(
            side_effect=git_commit)

    with patched as (m_release, m_tag, m_commit):
        m_release.side_effect = git_release
        m_tag.side_effect = git_tag
        commit = AsyncMock()
        m_commit.side_effect = commit
        result = await release.timestamp_tag

    if not has_release and not has_tag:
        assert (
            result
            == commit.return_value)
    else:
        assert (
            result
            == (git_release.return_value.published_at
                if has_release
                else git_commit.return_value.timestamp))
    assert (
        getattr(
            release,
            ADependencyGithubRelease.timestamp_tag.cache_name)[
                "timestamp_tag"]
        == result)


def test_release_version(patches):
    release = DummyDependencyGithubRelease("REPO", "VERSION")
    patched = patches(
        "version",
        ("ADependencyGithubRelease.tag_name",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.release")

    with patched as (m_version, m_tagname):
        assert release.version == m_version.parse.return_value

    assert (
        m_version.parse.call_args
        == [(m_tagname.return_value, ), {}])
    assert "version" in release.__dict__
