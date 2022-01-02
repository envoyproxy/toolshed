
from unittest.mock import AsyncMock, PropertyMock, MagicMock

import pytest

import abstracts

from aio.api import github as base_github


@abstracts.implementer(base_github.AGithubRepo)
class DummyGithubRepo:
    pass


def test_abstract_repo_constructor():
    repo = DummyGithubRepo("GITHUB", "NAME")
    assert repo.github == "GITHUB"
    assert repo.name == "NAME"
    assert str(repo) == f"<{repo.__class__.__name__} NAME>"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "releases",
    [(),
     ((False, None, 6),
      (False, 3, 5),
      (False, 2, 4),
      (True, 7, 3),
      (False, 5, 2),
      (False, 4, 1),
      (True, 1, 0))])
@pytest.mark.parametrize("since", range(0, 6))
async def test_abstract_repo_highest_release(patches, releases, since):
    repo = DummyGithubRepo("GITHUB", "NAME")
    patched = patches(
        "AGithubRepo.releases",
        prefix="aio.api.github.abstract.repo")
    kwargs = {}
    if since:
        kwargs["since"] = since
    actual_releases = [r for r in releases if (r[1] and not r[0])]
    recent_releases = [r for r in actual_releases if r[2] >= since]

    class ReleaseIter:
        results = []

        async def __aiter__(self):
            for prerelease, version, date in releases:
                m_release = MagicMock()
                m_release.prerelease = prerelease
                m_release.version = version
                m_release.published_at = date
                if version and not prerelease:
                    self.results.append(m_release)
                yield m_release

    release_iter = ReleaseIter()

    with patched as (m_releases, ):
        m_releases.return_value = release_iter
        result = await repo.highest_release(**kwargs)

    if not recent_releases:
        assert not result
        return
    expected = sorted(recent_releases, key=lambda x: x[1])[-1]
    assert expected[1] == result.version
    assert expected[2] == result.published_at


def test_abstract_repo_github_path(patches):
    repo = DummyGithubRepo("GITHUB", "NAME")
    patched = patches(
        "pathlib",
        prefix="aio.api.github.abstract.repo")

    with patched as (m_plib, ):
        assert repo.github_path == m_plib.PurePosixPath.return_value

    assert (
        list(m_plib.PurePosixPath.call_args)
        == [("/repos/NAME", ), {}])
    assert "github_path" in repo.__dict__


def test_abstract_repo_issues(patches):
    github = MagicMock()
    repo = DummyGithubRepo(github, "NAME")
    assert repo.issues == github.issues_class.return_value
    assert (
        list(github.issues_class.call_args)
        == [(github, ), dict(repo=repo)])
    assert "issues" in repo.__dict__


def test_abstract_repo_labels(patches):
    github = MagicMock()
    repo = DummyGithubRepo(github, "NAME")
    patched = patches(
        "AGithubRepo.iter_entities",
        prefix="aio.api.github.abstract.repo")

    with patched as (m_iter, ):
        assert repo.labels == m_iter.return_value

    assert (
        list(m_iter.call_args)
        == [(github.label_class, "labels"), {}])
    assert "labels" not in repo.__dict__


@pytest.mark.asyncio
async def test_abstract_repo_commit(patches):
    github = MagicMock()
    repo = DummyGithubRepo(github, "NAME")
    patched = patches(
        "AGithubRepo.getitem",
        prefix="aio.api.github.abstract.repo")

    with patched as (m_getitem, ):
        assert (
            await repo.commit("COMMIT_NAME")
            == github.commit_class.return_value)

    assert (
        list(github.commit_class.call_args)
        == [(repo, m_getitem.return_value), {}])
    assert (
        list(m_getitem.call_args)
        == [("commits/COMMIT_NAME", ), {}])


@pytest.mark.parametrize("since", [None, "SINCE"])
def test_abstract_repo_commits(patches, since):
    github = MagicMock()
    repo = DummyGithubRepo(github, "NAME")
    args = (
        (since, )
        if since
        else ())
    patched = patches(
        "partial",
        "utils",
        "AGithubRepo.getiter",
        prefix="aio.api.github.abstract.repo")

    with patched as (m_partial, m_utils, m_getiter):
        assert (
            repo.commits(*args)
            == m_getiter.return_value)

    query = "commits"
    if since:
        query = f"{query}?since={m_utils.dt_to_js_isoformat.return_value}"
        assert (
            list(m_utils.dt_to_js_isoformat.call_args)
            == [(since, ), {}])
    else:
        assert not m_utils.dt_to_js_isoformat.called
    assert (
        list(m_getiter.call_args)
        == [(query, ), dict(inflate=m_partial.return_value)])
    assert (
        list(m_partial.call_args)
        == [(github.commit_class, repo), {}])


@pytest.mark.asyncio
async def test_abstract_repo_getitem(patches):
    github = MagicMock()
    repo = DummyGithubRepo(github, "NAME")
    patched = patches(
        "AGithubRepo.github_endpoint",
        prefix="aio.api.github.abstract.repo")

    with patched as (m_gh_endpoint, ):
        github.getitem = AsyncMock()
        assert (
            await repo.getitem("QUERY")
            == github.getitem.return_value)

    assert (
        list(github.getitem.call_args)
        == [(m_gh_endpoint.return_value, ), {}])
    assert (
        list(m_gh_endpoint.call_args)
        == [("QUERY", ), {}])


@pytest.mark.parametrize(
    "kwargs", [{}, {f"K{i}": f"V{i}" for i in range(0, 3)}])
def test_abstract_repo_getiter(patches, kwargs):
    github = MagicMock()
    repo = DummyGithubRepo(github, "NAME")
    patched = patches(
        "AGithubRepo.github_endpoint",
        prefix="aio.api.github.abstract.repo")

    with patched as (m_gh_endpoint, ):
        assert (
            repo.getiter("QUERY", **kwargs)
            == github.getiter.return_value)

    assert (
        list(github.getiter.call_args)
        == [(m_gh_endpoint.return_value, ), kwargs])
    assert (
        list(m_gh_endpoint.call_args)
        == [("QUERY", ), {}])


def test_abstract_repo_github_endpoint(patches):
    repo = DummyGithubRepo("GITHUB", "NAME")
    patched = patches(
        ("AGithubRepo.github_path",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.repo")

    with patched as (m_path, ):
        assert (
            repo.github_endpoint("ENDPOINT")
            == str(m_path.return_value.joinpath.return_value))

    assert (
        list(m_path.return_value.joinpath.call_args)
        == [("ENDPOINT", ), {}])


def test_abstract_repo_iter_entities(patches):
    repo = DummyGithubRepo("GITHUB", "NAME")
    patched = patches(
        "partial",
        "AGithubRepo.getiter",
        prefix="aio.api.github.abstract.repo")

    with patched as (m_partial, m_getiter):
        assert (
            repo.iter_entities("ENTITY", "PATH")
            == m_getiter.return_value)

    assert (
        list(m_getiter.call_args)
        == [("PATH", ), dict(inflate=m_partial.return_value)])
    assert (
        list(m_partial.call_args)
        == [("ENTITY", repo), {}])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data", [None, {f"K{i}": f"V{i}" for i in range(0, 3)}])
async def test_abstract_repo_patch(patches, data):
    github = MagicMock()
    repo = DummyGithubRepo(github, "NAME")
    patched = patches(
        "AGithubRepo.github_endpoint",
        prefix="aio.api.github.abstract.repo")
    args = (
        (data, )
        if data
        else ())

    with patched as (m_gh_endpoint, ):
        github.patch = AsyncMock()
        assert (
            await repo.patch("QUERY", *args)
            == github.patch.return_value)

    assert (
        list(github.patch.call_args)
        == [(m_gh_endpoint.return_value, ), dict(data=data)])
    assert (
        list(m_gh_endpoint.call_args)
        == [("QUERY", ), {}])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data", [None, {f"K{i}": f"V{i}" for i in range(0, 3)}])
async def test_abstract_repo_post(patches, data):
    github = MagicMock()
    repo = DummyGithubRepo(github, "NAME")
    patched = patches(
        "AGithubRepo.github_endpoint",
        prefix="aio.api.github.abstract.repo")
    args = (
        (data, )
        if data
        else ())

    with patched as (m_gh_endpoint, ):
        github.post = AsyncMock()
        assert (
            await repo.post("QUERY", *args)
            == github.post.return_value)

    assert (
        list(github.post.call_args)
        == [(m_gh_endpoint.return_value, ), dict(data=data)])
    assert (
        list(m_gh_endpoint.call_args)
        == [("QUERY", ), {}])


@pytest.mark.asyncio
async def test_abstract_repo_release(patches):
    github = MagicMock()
    repo = DummyGithubRepo(github, "NAME")
    patched = patches(
        "AGithubRepo.getitem",
        prefix="aio.api.github.abstract.repo")

    with patched as (m_getitem, ):
        assert (
            await repo.release("RELEASE_NAME")
            == github.release_class.return_value)

    assert (
        list(github.release_class.call_args)
        == [(repo, m_getitem.return_value), {}])
    assert (
        list(m_getitem.call_args)
        == [("releases/tags/RELEASE_NAME", ), {}])


def test_abstract_repo_releases(patches):
    github = MagicMock()
    repo = DummyGithubRepo(github, "NAME")
    patched = patches(
        "AGithubRepo.iter_entities",
        prefix="aio.api.github.abstract.repo")

    with patched as (m_iter, ):
        assert (
            repo.releases()
            == m_iter.return_value)

    assert (
        list(m_iter.call_args)
        == [(github.release_class, "releases?per_page=100"), {}])


@pytest.mark.asyncio
@pytest.mark.parametrize("is_tag", [True, False])
async def test_abstract_repo_tag(patches, is_tag):
    github = MagicMock()
    github.getitem = AsyncMock()
    repo = DummyGithubRepo(github, "NAME")
    patched = patches(
        "AGithubRepo.getitem",
        prefix="aio.api.github.abstract.repo")
    ref_tag = MagicMock()
    if is_tag:
        ref_tag.__getitem__.return_value.__getitem__.return_value = "tag"

    with patched as (m_getitem, ):
        m_getitem.return_value = ref_tag
        if not is_tag:
            with pytest.raises(base_github.exceptions.TagNotFound):
                await repo.tag("TAG_NAME")
            return
        assert (
            await repo.tag("TAG_NAME")
            == github.tag_class.return_value)

    assert (
        list(github.tag_class.call_args)
        == [(repo, github.getitem.return_value), {}])
    assert (
        list(github.getitem.call_args)
        == [(m_getitem.return_value
                      .__getitem__.return_value
                      .__getitem__.return_value, ), {}])
    assert (
        list(m_getitem.call_args)
        == [("git/ref/tags/TAG_NAME", ), {}])
    assert (
        list(m_getitem.return_value.__getitem__.call_args)
        == [("object", ), {}])
    assert (
        list(m_getitem.return_value
                      .__getitem__.return_value
                      .__getitem__.call_args)
        == [("url", ), {}])


def test_abstract_repo_tags(patches):
    github = MagicMock()
    repo = DummyGithubRepo(github, "NAME")
    patched = patches(
        "AGithubRepo.iter_entities",
        prefix="aio.api.github.abstract.repo")

    with patched as (m_iter, ):
        assert (
            repo.tags()
            == m_iter.return_value)

    assert (
        list(m_iter.call_args)
        == [(github.tag_class, "tags"), {}])
