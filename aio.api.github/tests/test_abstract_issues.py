
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import gidgethub

import abstracts

from aio.api import github
from aio.api import github as base_github


@abstracts.implementer(github.AGithubIssue)
class DummyGithubIssue:
    pass


@abstracts.implementer(github.AGithubIssues)
class DummyGithubIssues:
    pass


def test_abstract_issue_constructor(patches):
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}
    patched = patches(
        "GithubRepoEntity.__init__",
        prefix="aio.api.github.abstract.issues")

    with patched as (m_super, ):
        m_super.return_value = None
        issue = DummyGithubIssue(*args, **kwargs)

    assert isinstance(issue, github.abstract.base.GithubRepoEntity)
    assert (
        m_super.call_args
        == [args, kwargs])
    issue.repo = MagicMock()
    issue.number = 23
    assert (
        str(issue)
        == f"<{issue.__class__.__name__} {issue.repo.name}#23>")


@pytest.mark.parametrize("number", range(0, 3))
@pytest.mark.parametrize("other_number", range(0, 3))
def test_issue_dunder_gt(number, other_number):
    issue1 = DummyGithubIssue("REPO", "DATA")
    issue1.number = number
    issue2 = DummyGithubIssue("REPO", "DATA")
    issue2.number = other_number
    assert (issue1 > issue2) == (number > other_number)


@pytest.mark.parametrize("number", range(0, 3))
@pytest.mark.parametrize("other_number", range(0, 3))
def test_issue_dunder_lt(number, other_number):
    issue1 = DummyGithubIssue("REPO", "DATA")
    issue1.number = number
    issue2 = DummyGithubIssue("REPO", "DATA")
    issue2.number = other_number
    assert (issue1 < issue2) == (number < other_number)


async def test_abstract_issue_close(patches):
    issue = DummyGithubIssue("REPO", "DATA")
    patched = patches(
        "AGithubIssue.edit",
        prefix="aio.api.github.abstract.issues")
    with patched as (m_edit, ):
        assert (
            await issue.close()
            == m_edit.return_value)
    assert (
        m_edit.call_args
        == [(), dict(state="closed")])


async def test_abstract_issue_comment():
    repo = MagicMock()
    repo.post = AsyncMock()
    issue = DummyGithubIssue(repo, "DATA")
    issue.number = 23
    assert (
        await issue.comment("COMMENT")
        == repo.post.return_value)
    assert (
        repo.post.call_args
        == [("issues/23/comments", ),
            dict(data=dict(body="COMMENT"))])


@pytest.mark.parametrize(
    "kwargs", [{}, {f"K{i}": f"V{i}" for i in range(0, 3)}])
async def test_abstract_issue_edit(patches, kwargs):
    repo = MagicMock()
    repo.patch = AsyncMock()
    issue = DummyGithubIssue(repo, "DATA")
    issue.number = 23
    patched = patches(
        "AGithubIssue.__init__",
        prefix="aio.api.github.abstract.issues")

    with patched as (m_init, ):
        m_init.return_value = None
        result = await issue.edit(**kwargs)

    assert isinstance(result, github.AGithubIssue)
    assert (
        m_init.call_args
        == [(repo, repo.patch.return_value), {}])
    assert (
        repo.patch.call_args
        == [("issues/23", ), dict(data=kwargs)])


@pytest.mark.parametrize("repo", [None, "REPO"])
@pytest.mark.parametrize("filter", [None, "FILTER"])
def test_abstract_issues_constructor(repo, filter):
    args = (
        (repo, )
        if repo
        else ())
    kwargs = {}
    if filter:
        kwargs["filter"] = filter
    issues = DummyGithubIssues("GITHUB", *args, **kwargs)
    assert issues.github == "GITHUB"
    assert issues.repo == repo
    assert issues._filter == (filter or "")


@pytest.mark.parametrize("repo", [None, "REPO"])
@pytest.mark.parametrize("filter", [None, "FILTER"])
def test_abstract_issues_filter(repo, filter):
    repo = MagicMock() if repo else None
    args = (
        (repo, )
        if repo
        else ())
    kwargs = {}
    if filter:
        kwargs["filter"] = filter
    issues = DummyGithubIssues("GITHUB", *args, **kwargs)
    filter_parts = []
    if filter:
        filter_parts.append(filter)
    if repo:
        filter_parts.append(f"repo:{repo.name}")
    filters = " ".join(filter_parts)
    assert (
        issues.filter
        == (f"{filters} " if filters else ""))


@pytest.mark.parametrize("repo1", [None, "REPO1"])
@pytest.mark.parametrize("repo2", [None, "REPO2"])
@pytest.mark.parametrize(
    "raises", [None, Exception, gidgethub.GitHubException])
async def test_abstract_issues_create(repo1, repo2, raises):
    github = MagicMock()
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}
    repo1 = (
        MagicMock()
        if repo1
        else None)
    repo2 = (
        MagicMock()
        if repo2
        else None)
    args1 = (
        (repo1, )
        if repo1
        else ())
    data_kwargs = dict(data=kwargs.copy())
    data_kwargs["data"]["title"] = "ISSUE_TITLE"
    if repo2:
        kwargs["repo"] = repo2
    repo = repo2 or repo1
    issues = DummyGithubIssues(github, *args1)
    if not repo:
        with pytest.raises(base_github.exceptions.IssueCreateError) as e:
            await issues.create("ISSUE_TITLE", **kwargs)
        assert not github.issue_class.called
        assert (
            e.value.args[0]
            == ("To create an issue, either `DummyGithubIssues` must be "
                "instantiated with a `repo` or `create` must be called with "
                "one."))
        return
    repo.post = AsyncMock()
    if raises:
        repo.post.side_effect = raises("BOOM!")
        error = (
            base_github.exceptions.IssueCreateError
            if raises != Exception
            else raises)
        with pytest.raises(error) as e:
            await issues.create("ISSUE_TITLE", **kwargs)
        if raises != Exception:
            assert (
                e.value.args[0]
                == ("Failed to create issue 'ISSUE_TITLE' in "
                    f"{repo.name}\nRecieved: BOOM!"))
        assert not github.issue_class.called
        assert (
            repo.post.call_args
            == [('issues',), data_kwargs])
    else:
        assert (
            await issues.create("ISSUE_TITLE", **kwargs)
            == github.issue_class.return_value)
        assert (
            github.issue_class.call_args
            == [(repo, repo.post.return_value), {}])
    assert (
        repo.post.call_args
        == [('issues',), data_kwargs])


@pytest.mark.parametrize("repo1", [None, "REPO1"])
@pytest.mark.parametrize("repo2", [None, "REPO2"])
def test_abstract_issues_inflater(patches, repo1, repo2):
    github = MagicMock()
    args1 = (
        (repo1, )
        if repo1
        else ())
    args2 = (
        (repo2, )
        if repo2
        else ())
    repo = repo2 or repo1
    issues = DummyGithubIssues(github, *args1)
    patched = patches(
        "partial",
        "AGithubIssues._inflate",
        prefix="aio.api.github.abstract.issues")

    with patched as (m_partial, m_inflate):
        assert (
            issues.inflater(*args2)
            == (m_inflate
                if not repo
                else m_partial.return_value))
    if not repo:
        assert not m_partial.called
        return
    assert (
        m_partial.call_args
        == [(github.issue_class, repo), {}])


@pytest.mark.parametrize("repo", [None, "REPO"])
def test_abstract_issues_search(patches, repo):
    github = MagicMock()
    args = (
        (repo, )
        if repo
        else ())
    issues = DummyGithubIssues(github)
    patched = patches(
        "AGithubIssues.inflater",
        "AGithubIssues.search_query",
        prefix="aio.api.github.abstract.issues")

    with patched as (m_inflater, m_query):
        assert (
            issues.search("QUERY", *args)
            == github.getiter.return_value)

    assert (
        github.getiter.call_args
        == [(m_query.return_value, ),
            dict(inflate=m_inflater.return_value)])
    assert (
        m_query.call_args
        == [("QUERY", ), {}])
    assert (
        m_inflater.call_args
        == [(repo, ), {}])


def test_abstract_issues_search_query(patches):
    issues = DummyGithubIssues("GITHUB")
    patched = patches(
        "urllib",
        ("AGithubIssues.filter",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.issues")

    with patched as (m_url, m_filter):
        assert (
            issues.search_query("QUERY")
            == f"/search/issues?q={m_url.parse.quote.return_value}")

    assert (
        m_url.parse.quote.call_args
        == [(f"{m_filter.return_value}QUERY", ), {}])


def test_abstract_issues__inflate():
    github = MagicMock()
    issues = DummyGithubIssues(github)
    result = dict(foo="BAR", repository_url="URL")
    assert (
        issues._inflate(result)
        == github.issue_class.return_value)
    assert (
        github.issue_class.call_args
        == [(github.repo_from_url.return_value, result), {}])
    assert (
        github.repo_from_url.call_args
        == [("URL", ), {}])
