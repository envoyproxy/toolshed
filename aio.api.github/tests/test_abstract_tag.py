
from unittest.mock import AsyncMock, PropertyMock, MagicMock

import pytest

import abstracts

from aio.api import github as base_github


@abstracts.implementer(base_github.AGithubTag)
class DummyGithubTag:
    pass


def test_abstract_tag_constructor(patches):
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}
    patched = patches(
        "GithubRepoEntity.__init__",
        prefix="aio.api.github.abstract.tag")

    with patched as (m_super, ):
        m_super.return_value = None
        tag = DummyGithubTag(*args, **kwargs)

    assert isinstance(tag, base_github.abstract.base.GithubRepoEntity)
    assert (
        list(m_super.call_args)
        == [args, kwargs])


@pytest.mark.parametrize("obj", [True, False])
def test_abstract_tag_commit_url(obj):
    url = MagicMock()
    data = dict(object=dict(url=url))
    if not obj:
        data = dict(url=url)
    tag = DummyGithubTag("GITHUB", data)
    assert tag.commit_url == url.replace.return_value
    assert (
        list(url.replace.call_args)
        == [("git/commits", "commits"), {}])
    assert "commit_url" not in tag.__dict__


@pytest.mark.asyncio
async def test_abstract_tag_commit(patches):
    tag = DummyGithubTag("REPO", {})
    patched = patches(
        ("AGithubTag.commit_url",
         dict(new_callable=PropertyMock)),
        ("AGithubTag.github",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.tag")

    with patched as (m_url, m_github):
        m_github.return_value.getitem = AsyncMock()
        result = await tag.commit
        assert (
            result
            == m_github.return_value.commit_class.return_value)

    assert (
        list(m_github.return_value.commit_class.call_args)
        == [(m_github.return_value,
             m_github.return_value.getitem.return_value), {}])
    assert (
        list(m_github.return_value.getitem.call_args)
        == [(m_url.return_value, ), {}])
    assert (
        getattr(
            tag,
            base_github.AGithubTag.commit.cache_name)[
                "commit"]
        == result)
