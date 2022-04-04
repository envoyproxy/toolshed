
import pytest

import abstracts

from aio.api import github
from aio.core.functional import async_property


@abstracts.implementer(github.IGithubIterator)
class DummyGithubIterator:

    def __aiter__(self):
        return github.IGithubIterator.__aiter__(self)

    @async_property
    async def total_count(self):
        return await github.IGithubIterator.total_count.async_result(self)


@abstracts.implementer(github.IGithubAPI)
class DummyGithubAPI:

    def __getitem__(self, k):
        return github.IGithubAPI.__getitem__(self, k)

    @property
    def commit_class(self):
        return github.IGithubAPI.commit_class.fget(self)

    @property
    def issue_class(self):
        return github.IGithubAPI.issue_class.fget(self)

    @property
    def issues_class(self):
        return github.IGithubAPI.issues_class.fget(self)

    @property
    def label_class(self):
        return github.IGithubAPI.label_class.fget(self)

    @property
    def release_class(self):
        return github.IGithubAPI.release_class.fget(self)

    @property
    def session(self):
        return github.IGithubAPI.session.fget(self)

    @property
    def tag_class(self):
        return github.IGithubAPI.tag_class.fget(self)

    async def getitem(self, *args, **kwargs):
        return github.IGithubAPI.getitem(self, *args, **kwargs)

    def getiter(self, *args, **kwargs):
        return github.IGithubAPI.getiter(self, *args, **kwargs)

    async def patch(self, query, data=None):
        return await github.IGithubAPI.patch(self, query, data)

    async def post(self, query, data=None):
        return await github.IGithubAPI.post(self, query, data)

    def repo_from_url(self, url):
        return github.IGithubAPI.repo_from_url(self, url)


@abstracts.implementer(github.IGithubIssues)
class DummyGithubIssues:

    async def create(self, title, **kwargs):
        return github.IGithubIssues.create(self, title, **kwargs)

    def search(self, query, repo=None):
        return github.IGithubIssues.search(self, query, repo)


@abstracts.implementer(github.IGithubTrackedIssue)
class DummyGithubTrackedIssue:

    @property
    def body(self):
        return github.IGithubTrackedIssue.body.fget(self)

    @property
    def closing_tpl(self):
        return github.IGithubTrackedIssue.closing_tpl.fget(self)

    @property
    def key(self):
        return github.IGithubTrackedIssue.key.fget(self)

    @property
    def number(self):
        return github.IGithubTrackedIssue.number.fget(self)

    @property
    def parsed(self):
        return github.IGithubTrackedIssue.body.fget(self)

    @property
    def repo_name(self):
        return github.IGithubTrackedIssue.repo_name.fget(self)

    @property
    def title(self):
        return github.IGithubTrackedIssue.repo_name.fget(self)

    async def close(self):
        return await github.IGithubTrackedIssue.close(self)

    async def close_duplicate(self):
        return await github.IGithubTrackedIssue.close_duplicate(self)

    async def comment(self, comment):
        return await github.IGithubTrackedIssue.comment(self, comment)


@abstracts.implementer(github.IGithubTrackedIssues)
class DummyGithubTrackedIssues:

    def __aiter__(self):
        return github.IGithubTrackedIssues.__aiter__()

    @property
    def closing_tpl(self):
        return github.IGithubTrackedIssues.closing_tpl.fget(self)

    @async_property
    async def duplicate_issues(self):
        return (
            await github.IGithubTrackedIssues.duplicate_issues
                                             .async_result(self))

    @property
    def github(self):
        return github.IGithubTrackedIssues.github.fget(self)

    @property
    def issue_author(self):
        return github.IGithubTrackedIssues.issue_author.fget(self)

    @property
    def issue_class(self):
        return github.IGithubTrackedIssues.issue_class.fget(self)

    @async_property
    async def issues(self):
        return await github.IGithubTrackedIssues.issues.async_result(self)

    @property
    def issues_search_tpl(self):
        return github.IGithubTrackedIssues.issues_search_tpl.fget(self)

    @property
    def labels(self):
        return github.IGithubTrackedIssues.labels.fget(self)

    @async_property
    async def missing_labels(self):
        return (
            await github.IGithubTrackedIssues.missing_labels
                                             .async_result(self))

    @async_property
    async def open_issues(self):
        return await github.IGithubTrackedIssues.open_issues.async_result(self)

    @property
    def repo(self):
        return github.IGithubTrackedIssues.repo.fget(self)

    @property
    def repo_name(self):
        return github.IGithubTrackedIssues.repo_name.fget(self)

    @property
    def title_prefix(self):
        return github.IGithubTrackedIssues.title_prefix.fget(self)

    @property
    def title_re(self):
        return github.IGithubTrackedIssues.title_re.fget(self)

    @property
    def titles(self):
        return github.IGithubTrackedIssues.titles.fget(self)

    async def create(self, **kwargs):
        return github.IGithubTrackedIssues.create(self, **kwargs)

    async def issue_body(self, **kwargs):
        return github.IGithubTrackedIssues.issue_body(self, **kwargs)

    async def issue_title(self, **kwargs):
        return github.IGithubTrackedIssues.issue_title(self, **kwargs)

    def iter_issues(self):
        return github.IGithubTrackedIssues.iter_issues(self)

    def track_issue(self, issues, issue):
        return github.IGithubTrackedIssues.track_issue(self, issues, issue)


def test_iface_iterator_constructor():
    with pytest.raises(TypeError):
        github.IGithubIterator()

    iterator = DummyGithubIterator()

    with pytest.raises(NotImplementedError):
        iterator.__aiter__()


async def test_iface_iterator_total_count():
    iterator = DummyGithubIterator()

    with pytest.raises(NotImplementedError):
        await iterator.total_count


def test_iface_api_constructor():
    with pytest.raises(TypeError):
        github.IGithubAPI()

    api = DummyGithubAPI()

    iface_props = [
        "commit_class", "issue_class", "issues_class",
        "label_class", "release_class",
        "session", "tag_class"]

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(api, prop)


@pytest.mark.parametrize("args", [(), range(0, 5)])
@pytest.mark.parametrize(
    "kwargs", [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
async def test_iface_api_getitem(args, kwargs):
    api = DummyGithubAPI()

    with pytest.raises(NotImplementedError):
        await api.getitem(*args, **kwargs)


@pytest.mark.parametrize("args", [(), range(0, 5)])
@pytest.mark.parametrize(
    "kwargs", [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_iface_api_getiter(args, kwargs):
    api = DummyGithubAPI()

    with pytest.raises(NotImplementedError):
        api.getiter(*args, **kwargs)


def test_iface_api_repo_from_url():
    api = DummyGithubAPI()

    with pytest.raises(NotImplementedError):
        api.repo_from_url("URL")


def test_iface_api_dunder_getitem():
    api = DummyGithubAPI()

    with pytest.raises(NotImplementedError):
        api["KEY"]


async def test_iface_api_patch():
    api = DummyGithubAPI()

    with pytest.raises(NotImplementedError):
        await api.patch("QUERY", "DATA")


async def test_iface_api_post():
    api = DummyGithubAPI()

    with pytest.raises(NotImplementedError):
        await api.post("QUERY", "DATA")


def test_iface_issues_constructor():
    with pytest.raises(TypeError):
        github.IGithubIssues()

    assert DummyGithubIssues()


async def test_iface_issues_create():
    issues = DummyGithubIssues()

    with pytest.raises(NotImplementedError):
        await issues.create("TITLE")


def test_iface_issues_search():
    issues = DummyGithubIssues()

    with pytest.raises(NotImplementedError):
        issues.search("QUERY", "REPO")


async def test_iface_tracked_issue_constructor():
    with pytest.raises(TypeError):
        github.IGithubTrackedIssue()

    tracked_issue = DummyGithubTrackedIssue()

    with pytest.raises(NotImplementedError):
        return github.IGithubTrackedIssue.__init__(
            tracked_issue, "ISSUES", "ISSUE")

    iface_props = [
        "body", "closing_tpl", "key", "number",
        "parsed", "repo_name", "title"]

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(tracked_issue, prop)

    iface_async_methods = ["close", "close_duplicate"]

    for method in iface_async_methods:
        with pytest.raises(NotImplementedError):
            await getattr(tracked_issue, method)()


async def test_iface_tracked_issue_comment():
    tracked_issue = DummyGithubTrackedIssue()

    with pytest.raises(NotImplementedError):
        await tracked_issue.comment("COMMENT")


async def test_iface_tracked_issues_constructor():
    with pytest.raises(TypeError):
        github.IGithubTrackedIssues()

    tracked_issues = DummyGithubTrackedIssues()

    iface_props = [
        "closing_tpl", "github",
        "issue_author", "issue_class", "issues_search_tpl",
        "labels", "repo", "repo_name",
        "title_prefix", "title_re", "titles"]

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(tracked_issues, prop)

    iface_async_props = [
        "duplicate_issues", "issues", "missing_labels", "open_issues"]

    for prop in iface_async_props:
        with pytest.raises(NotImplementedError):
            await getattr(tracked_issues, prop)

    with pytest.raises(NotImplementedError):
        tracked_issues.__aiter__()

    with pytest.raises(NotImplementedError):
        tracked_issues.iter_issues()


@pytest.mark.parametrize(
    "kwargs", [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
async def test_iface_tracked_issues_kwargs_methods(kwargs):
    tracked_issues = DummyGithubTrackedIssues()

    iface_async_methods = ["create", "issue_body", "issue_title"]

    for method in iface_async_methods:
        with pytest.raises(NotImplementedError):
            await getattr(tracked_issues, method)(**kwargs)


def test_iface_tracked_issues_track_issue():
    tracked_issues = DummyGithubTrackedIssues()

    with pytest.raises(NotImplementedError):
        tracked_issues.track_issue("ISSUES", "ISSUE")
