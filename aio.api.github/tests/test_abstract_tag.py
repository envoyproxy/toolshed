
from unittest.mock import AsyncMock, MagicMock

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
    tag.repo = MagicMock()
    tag.tag = "TAG_NAME"
    assert (
        str(tag)
        == f"<{tag.__class__.__name__} {tag.repo.name}@TAG_NAME>")


@pytest.mark.asyncio
async def test_abstract_tag_commit(patches):
    repo = AsyncMock()
    tag = DummyGithubTag(repo, dict(object=dict(sha="SHA")))
    result = await tag.commit
    assert (
        result
        == repo.commit.return_value)
    assert (
        list(repo.commit.call_args)
        == [("SHA", ), {}])
    assert (
        getattr(
            tag,
            base_github.AGithubTag.commit.cache_name)[
                "commit"]
        == result)
