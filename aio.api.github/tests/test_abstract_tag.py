
from unittest.mock import AsyncMock, MagicMock

import abstracts

from aio.api import github as base_github


@abstracts.implementer(base_github.AGithubTag)
class DummyGithubTag:
    pass


def test_abstract_tag_constructor(iters, patches):
    args = iters(tuple, count=3)
    kwargs = iters(dict, count=3)
    patched = patches(
        "GithubRepoEntity.__init__",
        prefix="aio.api.github.abstract.tag")

    with patched as (m_super, ):
        m_super.return_value = None
        tag = DummyGithubTag(*args, **kwargs)

    assert isinstance(tag, base_github.abstract.base.GithubRepoEntity)
    assert (
        m_super.call_args
        == [args, kwargs])
    tag._repo = MagicMock()
    tag.tag = "TAG_NAME"
    assert (
        str(tag)
        == f"<{tag.__class__.__name__} {tag._repo.name}@TAG_NAME>")


async def test_abstract_tag_commit(patches):
    repo = AsyncMock()
    tag = DummyGithubTag(repo, dict(object=dict(sha="SHA")))
    result = await tag.commit
    assert (
        result
        == repo.commit.return_value)
    assert (
        repo.commit.call_args
        == [("SHA", ), {}])
    assert (
        getattr(
            tag,
            base_github.AGithubTag.commit.cache_name)[
                "commit"]
        == result)
