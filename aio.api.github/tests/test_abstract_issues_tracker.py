
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio.api import github


@abstracts.implementer(github.IGithubTrackedIssue)
class DummyGithubTrackedIssue(github.AGithubTrackedIssue):
    pass


@abstracts.implementer(github.IGithubTrackedIssues)
class DummyGithubTrackedIssues(github.AGithubTrackedIssues):

    @property
    def closing_tpl(self):
        return super().closing_tpl

    @property
    def issue_author(self):
        return super().issue_author

    @property
    def issue_class(self):
        return super().issue_class

    @property
    def issues(self):
        return super().issues

    @property
    def issues_search_tpl(self):
        return super().issues_search_tpl

    @property
    def labels(self):
        return super().labels

    @property
    def repo_name(self):
        return super().repo_name

    @property
    def title_prefix(self):
        return super().title_prefix

    @property
    def title_re_tpl(self):
        return super().title_re_tpl

    @property
    def title_tpl(self):
        return super().title_tpl


@abstracts.implementer(github.IGithubIssuesTracker)
class DummyGithubIssuesTracker(github.AGithubIssuesTracker):

    @property
    def tracked_issues(self):
        return super().tracked_issues


def test_abstract_tracked_issue_constructor():
    with pytest.raises(TypeError):
        github.IGithubTrackedIssue("ISSUES", "ISSUE")

    issue = DummyGithubTrackedIssue("ISSUES", "ISSUE")
    assert issue.issues == "ISSUES"
    assert issue.issue == "ISSUE"

    assert issue.parse_vars == ("key", )
    assert "parse_vars" not in issue.__dict__


@pytest.mark.parametrize(
    "prop", ["body", "number", "title"])
def test_abstract_tracked_issue_issue_props(prop):
    mock_issue = MagicMock()
    issue = DummyGithubTrackedIssue("ISSUES", mock_issue)
    assert getattr(issue, prop) == getattr(mock_issue, prop)
    assert prop not in issue.__dict__


@pytest.mark.parametrize(
    "prop",
    ["closing_tpl", "repo_name", "title_re"])
def test_abstract_tracked_issue_issues_props(prop):
    mock_issues = MagicMock()
    issue = DummyGithubTrackedIssue(mock_issues, "ISSUE")
    assert getattr(issue, prop) == getattr(mock_issues, prop)
    assert prop not in issue.__dict__


def test_abstract_tracked_issue_key(patches):
    issue = DummyGithubTrackedIssue("ISSUES", "ISSUE")
    patched = patches(
        ("AGithubTrackedIssue.parsed",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.issues.tracker")

    with patched as (m_parsed, ):
        assert issue.key == m_parsed.return_value.get.return_value

    assert (
        m_parsed.return_value.get.call_args
        == [("key", ), {}])
    assert "key" not in issue.__dict__


@pytest.mark.parametrize("parsed", [True, False])
def test_issue_parsed(patches, parsed):
    issue = DummyGithubTrackedIssue("ISSUES", "ISSUE")
    patched = patches(
        "enumerate",
        ("AGithubTrackedIssue.parse_vars",
         dict(new_callable=PropertyMock)),
        ("AGithubTrackedIssue.title",
         dict(new_callable=PropertyMock)),
        ("AGithubTrackedIssue.title_re",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.issues.tracker")

    with patched as (m_enum, m_vars, m_title, m_re):
        m_vars.return_value = ["key", "version"]
        m_enum.side_effect = enumerate
        if not parsed:
            m_re.return_value.search.return_value = None
        else:
            m_re.return_value.search.return_value.group.side_effect = (
                lambda x: x)
        assert (
            issue.parsed
            == (dict(key=1, version=2)
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


async def test_abstract_tracked_issue_close():
    mock_issue = AsyncMock()
    issue = DummyGithubTrackedIssue("ISSUES", mock_issue)
    assert (
        await issue.close()
        == mock_issue.close.return_value)
    assert (
        mock_issue.close.call_args
        == [(), {}])


async def test_abstract_tracked_issue_close_duplicate(patches):
    issue = DummyGithubTrackedIssue("ISSUES", "ISSUE")
    dupe = AsyncMock()
    assert not await issue.close_duplicate(dupe)
    assert (
        dupe.close.call_args
        == [(), {}])


async def test_issue_comment():
    mock_issue = AsyncMock()
    issue = DummyGithubTrackedIssue("ISSUES", mock_issue)
    assert (
        await issue.comment("COMMENT")
        == mock_issue.comment.return_value)
    assert (
        mock_issue.comment.call_args
        == [("COMMENT", ), {}])


@pytest.mark.parametrize("issue_author", [None, "ISSUE_AUTHOR"])
@pytest.mark.parametrize("repo_name", [None, "REPO_NAME"])
def test_abstract_tracked_issues_constructor(issue_author, repo_name):
    kwargs = {}
    if issue_author:
        kwargs["issue_author"] = issue_author
    if repo_name:
        kwargs["repo_name"] = repo_name

    with pytest.raises(TypeError):
        github.IGithubTrackedIssues("GITHUB", **kwargs)

    issues = DummyGithubTrackedIssues("GITHUB", **kwargs)
    assert (
        issues._issue_author
        == issue_author)
    assert (
        issues.issue_author
        == issue_author or github.abstract.issues.tracker.ISSUE_AUTHOR)
    assert "issue_author" not in issues.__dict__
    assert (
        issues.issues_search_tpl
        == github.abstract.issues.tracker.ISSUES_SEARCH_TPL)
    assert "issues_search_tpl" not in issues.__dict__
    assert issues._repo_name == repo_name

    iface_props = [
        "closing_tpl", "issue_class", "labels",
        "title_prefix", "title_tpl"]
    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(issues, prop)


@pytest.mark.parametrize(
    "search_results",
    [[],
     [True, False, True],
     [False, False, False],
     [True, True, True]])
async def test_abstract_tracked_issues_dunder_aiter(patches, search_results):
    issues = DummyGithubTrackedIssues("GITHUB", "REPO_NAME")
    patched = patches(
        ("AGithubTrackedIssues.issue_class",
         dict(new_callable=PropertyMock)),
        "AGithubTrackedIssues.iter_issues",
        prefix="aio.api.github.abstract.issues.tracker")
    expected = []
    results = []
    mock_issues = []
    for issue in search_results:
        mock_issue = MagicMock()
        mock_issue.key = issue
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
    "open_issues", [[], range(0, 5), range(0, 3), range(2, 5)])
@pytest.mark.parametrize(
    "issues", [[], range(0, 5), range(0, 3), range(2, 5)])
async def test_abstract_tracked_issues_duplicate_issues(
        patches, open_issues, issues):
    tracked_issues = DummyGithubTrackedIssues("GITHUB", "REPO_NAME")
    patched = patches(
        ("AGithubTrackedIssues.issues",
         dict(new_callable=PropertyMock)),
        ("AGithubTrackedIssues.open_issues",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.issues.tracker")
    results = set()
    expected = set(open_issues) - set(issues)
    deps_obj = MagicMock()
    deps_obj.values.return_value = issues
    deps = AsyncMock(return_value=deps_obj)

    with patched as (m_dep, m_open):
        m_open.side_effect = AsyncMock(return_value=open_issues)
        m_dep.side_effect = deps

        async for issue in tracked_issues.duplicate_issues:
            results.add(issue)

    assert results == expected
    assert not getattr(
        issues,
        github.AGithubTrackedIssues.duplicate_issues.cache_name,
        None)


@pytest.mark.parametrize(
    "open_issues",
    [[],
     [dict(key="KEY1", version=1)],
     [dict(key="KEY1", version=1),
      dict(key="KEY2", version=1)],
     [dict(key="KEY1", version=1),
      dict(key="KEY2", version=1),
      dict(key="KEY1", version=2)],
     [dict(key="KEY1", version=2),
      dict(key="KEY2", version=1),
      dict(key="KEY1", version=1)],
     [dict(key="KEY1", version=1),
      dict(key="KEY2", version=1),
      dict(key="KEY1", version=1)]])
@pytest.mark.parametrize("is_tracked", range(0, 3))
async def test_issues_key_issues(patches, open_issues, is_tracked):
    issues = DummyGithubTrackedIssues("GITHUB")
    patched = patches(
        ("AGithubTrackedIssues.open_issues",
         dict(new_callable=PropertyMock)),
        "AGithubTrackedIssues.track_issue",
        prefix="aio.api.github.abstract.issues.tracker")

    mock_issues = []
    expected = {}
    for issue in open_issues:
        open_issue = MagicMock()
        open_issue.key = issue["key"]
        open_issue.version = issue["version"]
        mock_issues.append(open_issue)
        if is_tracked and (int(issue["key"][-1]) % is_tracked):
            continue
        expected[issue["key"]] = open_issue

    def do_track(issues, issue):
        return (
            not is_tracked
            or not (int(issue.key[-1]) % is_tracked))

    with patched as (m_open, m_track):
        m_track.side_effect = do_track
        m_open.side_effect = AsyncMock(return_value=mock_issues)
        assert await issues.issues == expected

    assert (
        getattr(
            issues,
            github.AGithubTrackedIssues.issues.cache_name)[
                "issues"]
        == expected)


@pytest.mark.parametrize(
    "repo_labels",
    [[],
     [f"LABEL{i}" for i in range(0, 5)],
     [f"LABEL{i}" for i in range(0, 3)],
     [f"LABEL{i}" for i in range(0, 10)],
     [f"LABEL{i}" for i in range(2, 7)]])
async def test_abstract_tracked_issues_missing_labels(patches, repo_labels):
    labels = [f"LABEL{i}" for i in range(1, 5)]
    issues = DummyGithubTrackedIssues("GITHUB")
    patched = patches(
        ("AGithubTrackedIssues.labels",
         dict(new_callable=PropertyMock)),
        ("AGithubTrackedIssues.repo",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.issues.tracker")

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

    with patched as (m_labels, m_repo):
        m_labels.return_value = labels
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
            github.AGithubTrackedIssues.missing_labels.cache_name)[
                "missing_labels"]
        == result)


@pytest.mark.parametrize("self_issues", [[], range(0, 5)])
async def test_abstract_tracked_issues_open_issues(patches, self_issues):
    issues = DummyGithubTrackedIssues("GITHUB", "REPO_NAME")
    patched = patches(
        "AGithubTrackedIssues.__aiter__",
        prefix="aio.api.github.abstract.issues.tracker")
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
            github.AGithubTrackedIssues.open_issues.cache_name)[
                "open_issues"]
        == result)


def test_abstract_tracked_issues_repo(patches):
    github = MagicMock()
    issues = DummyGithubTrackedIssues(github)
    patched = patches(
        ("AGithubTrackedIssues.repo_name",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.issues.tracker")

    with patched as (m_repo_name, ):
        assert issues.repo == github.__getitem__.return_value

    assert (
        github.__getitem__.call_args
        == [(m_repo_name.return_value, ), {}])
    assert "repo" in issues.__dict__


def test_abstract_tracked_issues_title_re(patches):
    issues = DummyGithubTrackedIssues(
        "GITHUB",
        "REPO_NAME")
    patched = patches(
        "re",
        ("AGithubTrackedIssues.title_prefix",
         dict(new_callable=PropertyMock)),
        ("AGithubTrackedIssues.title_re_tpl",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.issues.tracker")

    with patched as (m_re, m_title_prefix, m_title_re_tpl):
        assert issues.title_re == m_re.compile.return_value

    assert "title_re" in issues.__dict__
    assert (
        m_re.compile.call_args
        == [(m_title_re_tpl.return_value.format.return_value, ), {}])
    assert (
        m_title_re_tpl.return_value.format.call_args
        == [(), dict(title_prefix=m_title_prefix.return_value)])


@pytest.mark.parametrize(
    "titles",
    [[],
     [f"TITLE{i}" for i in range(0, 5)]])
async def test_abstract_tracked_issues_titles(patches, titles):
    issues = DummyGithubTrackedIssues("GITHUB", "REPO_NAME")
    patched = patches(
        ("AGithubTrackedIssues.open_issues",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.issues.tracker")

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
            github.AGithubTrackedIssues.titles.cache_name)[
                "titles"]
        == result)


@pytest.mark.parametrize("in_titles", [True, False])
async def test_abstract_tracked_issues_create(patches, in_titles):
    issues = DummyGithubTrackedIssues("GITHUB")
    patched = patches(
        ("AGithubTrackedIssues.labels",
         dict(new_callable=PropertyMock)),
        ("AGithubTrackedIssues.repo",
         dict(new_callable=PropertyMock)),
        ("AGithubTrackedIssues.issue_class",
         dict(new_callable=PropertyMock)),
        ("AGithubTrackedIssues.titles",
         dict(new_callable=PropertyMock)),
        "AGithubTrackedIssues.issue_body",
        "AGithubTrackedIssues.issue_title",
        prefix="aio.api.github.abstract.issues.tracker")
    titles = [f"TITLE{i}" for i in range(0, 5)]
    kwargs = dict(foo=MagicMock())

    with patched as (m_labels, m_repo, m_class, m_titles, m_body, m_title):
        m_titles.side_effect = AsyncMock(return_value=titles)
        if in_titles:
            titles.append(m_title.return_value)
        m_repo.return_value.issues.create = AsyncMock()
        if in_titles:
            with pytest.raises(github.exceptions.IssueExists) as e:
                await issues.create(**kwargs)
            assert e.value.args[0] == m_title.return_value
        else:
            assert (
                await issues.create(**kwargs)
                == m_class.return_value.return_value)

    assert (
        m_title.call_args
        == [(), kwargs])
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
            dict(body=m_body.return_value, labels=m_labels.return_value)])
    assert (
        m_body.call_args
        == [(), kwargs])


def test_abstract_tracked_issues_iter_issues(patches):
    issues = DummyGithubTrackedIssues("GITHUB")
    patched = patches(
        ("AGithubTrackedIssues.issues_search_tpl",
         dict(new_callable=PropertyMock)),
        ("AGithubTrackedIssues.repo",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.issues.tracker")

    with patched as (m_issues_search, m_repo, ):
        assert (
            issues.iter_issues()
            == m_repo.return_value.issues.search.return_value)

    assert (
        m_repo.return_value.issues.search.call_args
        == [(m_issues_search.return_value.format.return_value, ), {}])
    assert (
        m_issues_search.return_value.format.call_args
        == [(), dict(self=issues)])


@pytest.mark.parametrize("key", range(0, 10))
def test_abstract_tracked_issues_track_issue(key):
    issues = DummyGithubTrackedIssues("GITHUB")
    issue_list = [1, 3, 5, 7, 9]
    issue = MagicMock()
    issue.key = key
    assert (
        issues.track_issue(issue_list, issue)
        == (key not in issue_list))


def test_abstract_tracker_constructor():
    with pytest.raises(TypeError):
        github.IGithubIssuesTracker("GITHUB")

    tracker = DummyGithubIssuesTracker("GITHUB")

    with pytest.raises(NotImplementedError):
        tracker.tracked_issues


def test_abstract_tracker_dunder_getitem(patches):
    tracker = DummyGithubIssuesTracker("GITHUB")
    patched = patches(
        ("AGithubIssuesTracker.tracked_issues",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.issues.tracker")
    key = MagicMock()

    with patched as (m_tracked, ):
        assert (
            tracker[key]
            == m_tracked.return_value.__getitem__.return_value)

    assert (
        m_tracked.return_value.__getitem__.call_args
        == [(key, ), {}])
