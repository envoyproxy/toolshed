
from unittest.mock import MagicMock

import abstracts

from aio.api import github


@abstracts.implementer(github.AGithubCommit)
class DummyGithubCommit:
    pass


def test_abstract_commit_constructor(iters, patches):
    args = iters(tuple, count=3)
    kwargs = iters(dict, count=3)
    patched = patches(
        "GithubRepoEntity.__init__",
        prefix="aio.api.github.abstract.commit")

    with patched as (m_super, ):
        m_super.return_value = None
        commit = DummyGithubCommit(*args, **kwargs)

    assert isinstance(commit, github.abstract.base.GithubRepoEntity)
    assert (
        m_super.call_args
        == [args, kwargs])
    commit._repo = MagicMock()
    commit.sha = "SHA"
    assert (
        str(commit)
        == f"<{commit.__class__.__name__} {commit._repo.name}#{commit.sha}>")


def test_abstract_commit_timestamp(patches):
    data = MagicMock()
    commit = DummyGithubCommit("REPO", data)
    patched = patches(
        "utils",
        prefix="aio.api.github.abstract.commit")

    with patched as (m_utils, ):
        assert (
            commit.timestamp
            == m_utils.dt_from_js_isoformat.return_value)

    assert (
        m_utils.dt_from_js_isoformat.call_args
        == [(data.__getitem__.return_value
                 .__getitem__.return_value
                 .__getitem__.return_value, ), {}])
    assert (
        data.__getitem__.call_args
        == [("commit", ), {}])
    assert (
        (data.__getitem__.return_value
             .__getitem__.call_args)
        == [("committer", ), {}])
    assert (
        (data.__getitem__.return_value
             .__getitem__.return_value
             .__getitem__.call_args)
        == [("date", ), {}])
