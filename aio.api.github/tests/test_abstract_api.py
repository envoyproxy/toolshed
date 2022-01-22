
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import gidgethub.aiohttp

import abstracts

from aio.api import github


@abstracts.implementer(github.AGithubAPI)
class DummyGithubAPI:

    @property
    def api_class(self):
        return super().api_class

    @property
    def commit_class(self):
        return super().commit_class

    @property
    def issue_class(self):
        return super().issue_class

    @property
    def issues_class(self):
        return super().issues_class

    @property
    def iterator_class(self):
        return super().iterator_class

    @property
    def label_class(self):
        return super().label_class

    @property
    def release_class(self):
        return super().release_class

    @property
    def repo_class(self):
        return super().repo_class

    @property
    def tag_class(self):
        return super().tag_class


@pytest.mark.parametrize(
    "args", [(), tuple(f"ARG{i}" for i in range(0, 3))])
@pytest.mark.parametrize(
    "kwargs", [{}, {f"K{i}": f"V{i}" for i in range(0, 3)}])
def test_abstract_api_constructor(args, kwargs):

    with pytest.raises(TypeError):
        github.AGithubAPI(*args, **kwargs)

    api = DummyGithubAPI(*args, **kwargs)
    assert api.args == args
    assert api.kwargs == kwargs
    props = (
        "commit", "issue", "issues", "iterator",
        "label", "release", "repo", "tag")

    for prop in props:
        with pytest.raises(NotImplementedError):
            getattr(api, f"{prop}_class")

    assert api.api_class == gidgethub.aiohttp.GitHubAPI
    assert "api_class" not in api.__dict__


def test_abstract_api_dunder_getitem(patches):
    api = DummyGithubAPI()
    patched = patches(
        ("AGithubAPI.repo_class",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.api")

    with patched as (m_repo_class, ):
        assert api["REPO"] == m_repo_class.return_value.return_value

    assert (
        m_repo_class.return_value.call_args
        == [(api, "REPO"), {}])


def test_abstract_api_api(patches):
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}
    api = DummyGithubAPI(*args, **kwargs)
    patched = patches(
        ("AGithubAPI.api_class",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.api")

    with patched as (m_api_class, ):
        assert (
            api.api
            == m_api_class.return_value.return_value)

    assert (
        m_api_class.return_value.call_args
        == [args, kwargs])

    assert "api" in api.__dict__


async def test_abstract_api_getitem(patches):
    api = DummyGithubAPI()
    patched = patches(
        ("AGithubAPI.api",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.api")
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}

    with patched as (m_api, ):
        m_api.return_value.getitem = AsyncMock()
        assert (
            await api.getitem(*args, **kwargs)
            == m_api.return_value.getitem.return_value)

    assert (
        m_api.return_value.getitem.call_args
        == [args, kwargs])


def test_abstract_api_getiter(patches):
    api = DummyGithubAPI()
    patched = patches(
        ("AGithubAPI.api",
         dict(new_callable=PropertyMock)),
        ("AGithubAPI.iterator_class",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.api")
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}

    with patched as (m_api, m_iter):
        assert (
            api.getiter(*args, **kwargs)
            == m_iter.return_value.return_value)

    assert (
        m_iter.return_value.call_args
        == [(m_api.return_value, ) + args, kwargs])


async def test_abstract_api_patch(patches):
    api = DummyGithubAPI()
    patched = patches(
        ("AGithubAPI.api",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.api")
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}

    with patched as (m_api, ):
        m_api.return_value.patch = AsyncMock()
        assert (
            await api.patch(*args, **kwargs)
            == m_api.return_value.patch.return_value)

    assert (
        m_api.return_value.patch.call_args
        == [args, kwargs])


async def test_abstract_api_post(patches):
    api = DummyGithubAPI()
    patched = patches(
        ("AGithubAPI.api",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.api")
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}

    with patched as (m_api, ):
        m_api.return_value.post = AsyncMock()
        assert (
            await api.post(*args, **kwargs)
            == m_api.return_value.post.return_value)

    assert (
        m_api.return_value.post.call_args
        == [args, kwargs])


@pytest.mark.parametrize("isrepo", [True, False])
def test_abstract_api_repo_from_url(patches, isrepo):
    api = DummyGithubAPI()
    patched = patches(
        ("AGithubAPI.api",
         dict(new_callable=PropertyMock)),
        "AGithubAPI.__getitem__",
        prefix="aio.api.github.abstract.api")
    url = MagicMock()
    url.startswith.return_value = isrepo
    url.__getitem__.return_value = "X/Y/Z"

    with patched as (m_api, m_get):
        assert (
            api.repo_from_url(url)
            == (m_get.return_value
                if isrepo
                else None))

    repo_url = f"{m_api.return_value.base_url}/repos/"
    assert (
        url.startswith.call_args
        == [(repo_url, ), {}])
    if not isrepo:
        assert not m_get.called
        return
    assert (
        m_get.call_args
        == [("X/Y", ), {}])
    assert (
        url.__getitem__.call_args
        == [(slice(len(repo_url), None, None),), {}])
