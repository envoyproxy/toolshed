
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio.api import github

from envoy.dependency.check import (
    abstract,
    AGithubDependencyIssue,
    AGithubDependencyIssues)


@abstracts.implementer(AGithubDependencyIssue)
class DummyGithubDependencyIssue:
    pass


@abstracts.implementer(AGithubDependencyIssues)
class DummyGithubDependencyIssues:

    @property
    def issue_class(self):
        return super().issue_class


def test_issue_constructor():
    issue = DummyGithubDependencyIssue("ISSUES", "ISSUE")
    assert issue.issues == "ISSUES"
    assert issue.issue == "ISSUE"


@pytest.mark.parametrize(
    "param", ["body", "number", "title"])
def test_issue_issue_params(param):
    mock_issue = MagicMock()
    issue = DummyGithubDependencyIssue("ISSUES", mock_issue)
    assert getattr(issue, param) == getattr(mock_issue, param)
    assert param not in issue.__dict__


@pytest.mark.parametrize(
    "param",
    ["closing_tpl", "repo_name", "title_re"])
def test_issue_issues_params(param):
    mock_issues = MagicMock()
    issue = DummyGithubDependencyIssue(mock_issues, "ISSUE")
    assert getattr(issue, param) == getattr(mock_issues, param)
    assert param not in issue.__dict__


def test_issue_dep(patches):
    issue = DummyGithubDependencyIssue("ISSUES", "ISSUE")
    patched = patches(
        ("AGithubDependencyIssue.parsed",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.issues")

    with patched as (m_parsed, ):
        assert issue.dep == m_parsed.return_value.get.return_value

    assert (
        m_parsed.return_value.get.call_args
        == [("dep", ), {}])
    assert "dep" not in issue.__dict__


@pytest.mark.parametrize("parsed", [True, False])
def test_issue_parsed(patches, parsed):
    issue = DummyGithubDependencyIssue("ISSUES", "ISSUE")
    patched = patches(
        ("AGithubDependencyIssue.title",
         dict(new_callable=PropertyMock)),
        ("AGithubDependencyIssue.title_re",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.issues")

    with patched as (m_title, m_re):
        if not parsed:
            m_re.return_value.search.return_value = None
        else:
            m_re.return_value.search.return_value.group.side_effect = (
                lambda x: x)
        assert (
            issue.parsed
            == (dict(dep=1, version=2)
                if parsed
                else {}))

    assert "parsed" in issue.__dict__
    assert (
        m_re.return_value.search.call_args
        == [(m_title.return_value, ), {}])
    if not parsed:
        return
    assert (
        m_re.return_value.search.return_value.group.call_args_list
        == [[(1, ), {}], [(2, ), {}]])


@pytest.mark.parametrize("parsed", [True, False])
def test_issue_version(patches, parsed):
    issue = DummyGithubDependencyIssue("ISSUES", "ISSUE")
    patched = patches(
        "version",
        ("AGithubDependencyIssue.parsed",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.issues")

    with patched as (m_version, m_parsed):
        m_parsed.return_value = (
            dict(version=23)
            if parsed
            else {})
        assert (
            issue.version
            == (m_version.parse.return_value
                if parsed
                else None))

    assert "version" in issue.__dict__
    if not parsed:
        assert not m_version.parse.called
        return
    assert (
        m_version.parse.call_args
        == [(23, ), {}])


async def test_issue_close():
    mock_issue = AsyncMock()
    issue = DummyGithubDependencyIssue("ISSUES", mock_issue)
    assert (
        await issue.close()
        == mock_issue.close.return_value)
    assert (
        mock_issue.close.call_args
        == [(), {}])


async def test_issue_close_duplicate(patches):
    issue = DummyGithubDependencyIssue("ISSUES", "ISSUE")
    dupe = AsyncMock()
    assert not await issue.close_duplicate(dupe)
    assert (
        dupe.close.call_args
        == [(), {}])


async def test_issue_close_old(patches):
    issue = DummyGithubDependencyIssue("ISSUES", "ISSUE")
    patched = patches(
        ("AGithubDependencyIssue.closing_tpl",
         dict(new_callable=PropertyMock)),
        ("AGithubDependencyIssue.number",
         dict(new_callable=PropertyMock)),
        ("AGithubDependencyIssue.repo_name",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.issues")
    old_issue = AsyncMock()
    dep = MagicMock()
    mock_release = MagicMock()
    date = AsyncMock()
    mock_release.date = date()
    newer_release = AsyncMock(return_value=mock_release)
    dep.newer_release = newer_release()

    with patched as (m_tpl, m_number, m_name):
        assert not await issue.close_old(old_issue, dep)

    assert (
        old_issue.comment.call_args
        == [(m_tpl.return_value.format.return_value, ), {}])
    assert (
        m_tpl.return_value.format.call_args
        == [(),
            dict(newer_release=newer_release.return_value,
                 newer_release_date=date.return_value,
                 full_name=dep.repo.name,
                 repo_location=m_name.return_value,
                 number=m_number.return_value)])
    assert (
        old_issue.close.call_args
        == [(), {}])


async def test_issue_comment():
    mock_issue = AsyncMock()
    issue = DummyGithubDependencyIssue("ISSUES", mock_issue)
    assert (
        await issue.comment("COMMENT")
        == mock_issue.comment.return_value)
    assert (
        mock_issue.comment.call_args
        == [("COMMENT", ), {}])


@pytest.mark.parametrize("body_tpl", [None, "BODY_TPL"])
@pytest.mark.parametrize("closing_tpl", [None, "CLOSING_TPL"])
@pytest.mark.parametrize("issue_author", [None, "ISSUE_AUTHOR"])
@pytest.mark.parametrize("issues_search_tpl", [None, "ISSUES_SEARCH_TPL"])
@pytest.mark.parametrize("labels", [None, "LABELS"])
@pytest.mark.parametrize("repo_name", [None, "REPO_NAME"])
@pytest.mark.parametrize("title_prefix", [None, "TITLE_PREFIX"])
@pytest.mark.parametrize("title_re_tpl", [None, "TITLE_RE_TPL"])
@pytest.mark.parametrize("title_tpl", [None, "TITLE_TPL"])
def test_issues_constructor(
        body_tpl, closing_tpl, issue_author, issues_search_tpl, labels,
        repo_name, title_prefix, title_re_tpl, title_tpl):
    kwargs = {}
    if body_tpl:
        kwargs["body_tpl"] = body_tpl
    if closing_tpl:
        kwargs["closing_tpl"] = closing_tpl
    if issue_author:
        kwargs["issue_author"] = issue_author
    if issues_search_tpl:
        kwargs["issues_search_tpl"] = issues_search_tpl
    if labels:
        kwargs["labels"] = labels
    if repo_name:
        kwargs["repo_name"] = repo_name
    if title_prefix:
        kwargs["title_prefix"] = title_prefix
    if title_re_tpl:
        kwargs["title_re_tpl"] = title_re_tpl
    if title_tpl:
        kwargs["title_tpl"] = title_tpl

    with pytest.raises(TypeError):
        AGithubDependencyIssues("GITHUB", **kwargs)

    issues = DummyGithubDependencyIssues("GITHUB", **kwargs)
    assert (
        issues.body_tpl
        == (body_tpl or abstract.issues.BODY_TPL))
    assert (
        issues.closing_tpl
        == (closing_tpl or abstract.issues.CLOSING_TPL))
    assert (
        issues.issue_author
        == (issue_author or abstract.issues.ISSUE_AUTHOR))
    assert (
        issues.issues_search_tpl
        == (issues_search_tpl or abstract.issues.ISSUES_SEARCH_TPL))
    assert (
        issues.labels
        == (labels or abstract.issues.LABELS))
    assert (
        issues.repo_name
        == (repo_name or abstract.issues.GITHUB_REPO_LOCATION))
    assert (
        issues.title_prefix
        == (title_prefix or abstract.issues.TITLE_PREFIX))
    assert (
        issues.title_re_tpl
        == (title_re_tpl or abstract.issues.TITLE_RE_TPL))
    assert (
        issues.title_tpl
        == (title_tpl or abstract.issues.TITLE_TPL))

    with pytest.raises(NotImplementedError):
        issues.issue_class


@pytest.mark.parametrize(
    "search_results",
    [[],
     [True, False, True],
     [False, False, False],
     [True, True, True]])
async def test_issues_dunder_aiter(patches, search_results):
    issues = DummyGithubDependencyIssues("GITHUB")
    patched = patches(
        ("AGithubDependencyIssues.issue_class",
         dict(new_callable=PropertyMock)),
        "AGithubDependencyIssues.iter_issues",
        prefix="envoy.dependency.check.abstract.issues")
    expected = []
    results = []
    mock_issues = []
    for issue in search_results:
        mock_issue = MagicMock()
        mock_issue.dep = issue
        if issue:
            expected.append(mock_issue)
        mock_issues.append(mock_issue)

    async def search_iter():
        for issue in mock_issues:
            yield issue

    with patched as (m_class, m_iter):
        m_iter.side_effect = search_iter
        m_class.return_value.side_effect = lambda s, x: x
        async for result in issues:
            results.append(result)

    assert results == expected
    assert (
        m_class.return_value.call_args_list
        == [[(issues, issue), {}] for issue in mock_issues])


@pytest.mark.parametrize(
    "open_issues",
    [[],
     [dict(dep="DEP1", version=1)],
     [dict(dep="DEP1", version=1),
      dict(dep="DEP2", version=1)],
     [dict(dep="DEP1", version=1),
      dict(dep="DEP2", version=1),
      dict(dep="DEP1", version=2)],
     [dict(dep="DEP1", version=2),
      dict(dep="DEP2", version=1),
      dict(dep="DEP1", version=1)],
     [dict(dep="DEP1", version=1),
      dict(dep="DEP2", version=1),
      dict(dep="DEP1", version=1)]])
async def test_issues_dep_issues(patches, open_issues):
    issues = DummyGithubDependencyIssues("GITHUB")
    patched = patches(
        ("AGithubDependencyIssues.open_issues",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.issues")

    mock_issues = []
    expected = {}
    for issue in open_issues:
        open_issue = MagicMock()
        open_issue.dep = issue["dep"]
        open_issue.version = issue["version"]
        mock_issues.append(open_issue)
        if issue["dep"] in expected:
            if issue["version"] > expected[issue["dep"]].version:
                expected[issue["dep"]] = open_issue
        else:
            expected[issue["dep"]] = open_issue

    with patched as (m_open, ):
        m_open.side_effect = AsyncMock(return_value=mock_issues)
        assert await issues.dep_issues == expected

    assert (
        getattr(
            issues,
            AGithubDependencyIssues.dep_issues.cache_name)[
                "dep_issues"]
        == expected)


@pytest.mark.parametrize(
    "open_issues", [[], range(0, 5), range(0, 3), range(2, 5)])
@pytest.mark.parametrize(
    "dep_issues", [[], range(0, 5), range(0, 3), range(2, 5)])
async def test_issues_duplicate_issues(patches, open_issues, dep_issues):
    issues = DummyGithubDependencyIssues("GITHUB")
    patched = patches(
        ("AGithubDependencyIssues.dep_issues",
         dict(new_callable=PropertyMock)),
        ("AGithubDependencyIssues.open_issues",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.issues")
    results = set()
    expected = set(open_issues) - set(dep_issues)
    deps_obj = MagicMock()
    deps_obj.values.return_value = dep_issues
    deps = AsyncMock(return_value=deps_obj)

    with patched as (m_dep, m_open):
        m_open.side_effect = AsyncMock(return_value=open_issues)
        m_dep.side_effect = deps

        async for issue in issues.duplicate_issues:
            results.add(issue)

    assert results == expected
    assert not getattr(
        issues,
        AGithubDependencyIssues.duplicate_issues.cache_name,
        None)


@pytest.mark.parametrize(
    "repo_labels",
    [[],
     [f"LABEL{i}" for i in range(0, 5)],
     [f"LABEL{i}" for i in range(0, 3)],
     [f"LABEL{i}" for i in range(0, 10)],
     [f"LABEL{i}" for i in range(2, 7)]])
async def test_issues_missing_labels(patches, repo_labels):
    labels = [f"LABEL{i}" for i in range(1, 5)]
    issues = DummyGithubDependencyIssues("GITHUB", labels=labels)
    patched = patches(
        ("AGithubDependencyIssues.repo",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.issues")

    expected = 0
    found = {}
    for label in repo_labels:
        expected += 1
        if label in labels:
            found[label] = None
        if len(labels) == len(found):
            break

    class LabelIter:
        count = 0

        async def __aiter__(self):
            for issue in repo_labels:
                self.count += 1
                mock_label = MagicMock()
                mock_label.name = issue
                yield mock_label

    label_iter = LabelIter()

    with patched as (m_repo, ):
        m_repo.return_value.labels = label_iter
        result = await issues.missing_labels
        assert (
            result
            == tuple(
                label
                for label
                in labels
                if label not in repo_labels))
    assert label_iter.count == expected
    assert (
        getattr(
            issues,
            AGithubDependencyIssues.missing_labels.cache_name)[
                "missing_labels"]
        == result)


@pytest.mark.parametrize("self_issues", [[], range(0, 5)])
async def test_issues_open_issues(patches, self_issues):
    issues = DummyGithubDependencyIssues("GITHUB")
    patched = patches(
        "AGithubDependencyIssues.__aiter__",
        prefix="envoy.dependency.check.abstract.issues")
    mock_issues = []

    for issue in self_issues:
        mock_issue = MagicMock()
        mock_issues.append(mock_issue)

    async def iter_issues():
        for issue in mock_issues:
            yield issue

    with patched as (m_iter, ):
        m_iter.side_effect = iter_issues
        result = await issues.open_issues
        assert result == tuple(mock_issues)

    assert (
        getattr(
            issues,
            AGithubDependencyIssues.open_issues.cache_name)[
                "open_issues"]
        == result)


def test_issues_repo(patches):
    github = MagicMock()
    issues = DummyGithubDependencyIssues(
        github, repo_name="REPO_NAME")
    assert issues.repo == github.__getitem__.return_value
    assert (
        github.__getitem__.call_args
        == [("REPO_NAME", ), {}])
    assert "repo" in issues.__dict__


def test_issues_title_re(patches):
    title_prefix = MagicMock()
    title_re_tpl = MagicMock()
    issues = DummyGithubDependencyIssues(
        "GITHUB",
        title_re_tpl=title_re_tpl,
        title_prefix=title_prefix)
    patched = patches(
        "re",
        prefix="envoy.dependency.check.abstract.issues")

    with patched as (m_re, ):
        assert issues.title_re == m_re.compile.return_value

    assert "title_re" in issues.__dict__
    assert (
        m_re.compile.call_args
        == [(title_re_tpl.format.return_value, ), {}])
    assert (
        title_re_tpl.format.call_args
        == [(), dict(title_prefix=title_prefix)])


@pytest.mark.parametrize(
    "titles",
    [[],
     [f"TITLE{i}" for i in range(0, 5)]])
async def test_issues_titles(patches, titles):
    issues = DummyGithubDependencyIssues("GITHUB")
    patched = patches(
        ("AGithubDependencyIssues.open_issues",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.issues")

    mock_titles = []
    for title in titles:
        mock_title = MagicMock()
        mock_title.title = title
        mock_titles.append(mock_title)

    with patched as (m_open, ):
        m_open.side_effect = AsyncMock(return_value=mock_titles)
        result = await issues.titles
        assert (
            result
            == tuple(titles))

    assert (
        getattr(
            issues,
            AGithubDependencyIssues.titles.cache_name)[
                "titles"]
        == result)


@pytest.mark.parametrize("in_titles", [True, False])
async def test_issues_create(patches, in_titles):
    issues = DummyGithubDependencyIssues("GITHUB", labels=["LABEL"])
    patched = patches(
        ("AGithubDependencyIssues.repo",
         dict(new_callable=PropertyMock)),
        ("AGithubDependencyIssues.issue_class",
         dict(new_callable=PropertyMock)),
        ("AGithubDependencyIssues.titles",
         dict(new_callable=PropertyMock)),
        "AGithubDependencyIssues.issue_body",
        "AGithubDependencyIssues.issue_title",
        prefix="envoy.dependency.check.abstract.issues")
    titles = [f"TITLE{i}" for i in range(0, 5)]
    dep = MagicMock()

    with patched as (m_repo, m_class, m_titles, m_body, m_title):
        m_titles.side_effect = AsyncMock(return_value=titles)
        if in_titles:
            titles.append(m_title.return_value)
        m_repo.return_value.issues.create = AsyncMock()
        if in_titles:
            with pytest.raises(github.exceptions.IssueExists) as e:
                await issues.create(dep)
            assert e.value.args[0] == m_title.return_value
        else:
            assert (
                await issues.create(dep)
                == m_class.return_value.return_value)

    assert (
        m_title.call_args
        == [(dep, ), {}])
    if in_titles:
        assert not m_class.called
        assert not m_repo.called
        assert not m_body.called
        return
    assert (
        m_class.return_value.call_args
        == [(issues, m_repo.return_value.issues.create.return_value), {}])
    assert (
        m_repo.return_value.issues.create.call_args
        == [(m_title.return_value,),
            dict(body=m_body.return_value, labels=["LABEL"])])
    assert (
        m_body.call_args
        == [(dep, ), {}])


async def test_issues_issue_body():
    body_tpl = MagicMock()
    issues = DummyGithubDependencyIssues("GITHUB", body_tpl=body_tpl)
    dep = MagicMock()
    date = AsyncMock()
    mock_release = MagicMock()
    mock_release.date = date()
    newer_release = AsyncMock(return_value=mock_release)
    dep.newer_release = newer_release()
    release_date = AsyncMock()
    dep.release.date = release_date()
    assert (
        await issues.issue_body(dep)
        == body_tpl.format.return_value)
    assert (
        body_tpl.format.call_args
        == [(),
            dict(dep=dep,
                 newer_release=newer_release.return_value,
                 newer_release_date=date.return_value,
                 release_date=release_date.return_value)])


async def test_issues_issue_title():
    title_tpl = MagicMock()
    issues = DummyGithubDependencyIssues(
        "GITHUB",
        title_tpl=title_tpl,
        title_prefix="TITLE_PREFIX")
    dep = MagicMock()
    newer_release = AsyncMock()
    dep.newer_release = newer_release()
    assert (
        await issues.issue_title(dep)
        == title_tpl.format.return_value)
    assert (
        title_tpl.format.call_args
        == [(),
            dict(dep=dep,
                 newer_release=newer_release.return_value,
                 title_prefix="TITLE_PREFIX")])


def test_issues_iter_issues(patches):
    issues_search_tpl = MagicMock()
    issues = DummyGithubDependencyIssues(
        "GITHUB", issues_search_tpl=issues_search_tpl)
    patched = patches(
        ("AGithubDependencyIssues.repo",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.issues")

    with patched as (m_repo, ):
        assert (
            issues.iter_issues()
            == m_repo.return_value.issues.search.return_value)

    assert (
        m_repo.return_value.issues.search.call_args
        == [(issues_search_tpl.format.return_value, ), {}])
    assert (
        issues_search_tpl.format.call_args
        == [(), dict(self=issues)])
