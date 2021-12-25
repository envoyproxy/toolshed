
from unittest.mock import PropertyMock

from aio.api import github


def test_api_constructor(patches):
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}
    patched = patches(
        "AGithubAPI.__init__",
        prefix="aio.api.github.api")

    with patched as (m_super, ):
        m_super.return_value = None
        api = github.GithubAPI(*args, **kwargs)

    assert isinstance(api, github.AGithubAPI)
    assert (
        list(m_super.call_args)
        == [args, kwargs])
    assert api.commit_class == github.GithubCommit
    assert api.issue_class == github.GithubIssue
    assert api.issues_class == github.GithubIssues
    assert api.iterator_class == github.GithubIterator
    assert api.label_class == github.GithubLabel
    assert api.release_class == github.GithubRelease
    assert api.repo_class == github.GithubRepo
    assert api.tag_class == github.GithubTag


def test_api_api_class(patches):
    api = github.GithubAPI()
    patched = patches(
        ("AGithubAPI.api_class", dict(new_callable=PropertyMock)),
        prefix="aio.api.github.api")

    with patched as (m_super, ):
        assert api.api_class == m_super.return_value


def test_commit_constructor():
    commit = github.GithubCommit("GITHUB", "DATA")
    assert isinstance(commit, github.AGithubCommit)


def test_issues_constructor():
    issues = github.GithubIssues("GITHUB")
    assert isinstance(issues, github.AGithubIssues)


def test_iterator_constructor():
    iterator = github.GithubIterator("API", "QUERY")
    assert isinstance(iterator, github.AGithubIterator)


def test_label_constructor():
    label = github.GithubLabel("GITHUB", "DATA")
    assert isinstance(label, github.AGithubLabel)


def test_release_constructor():
    release = github.GithubRelease("GITHUB", "DATA")
    assert isinstance(release, github.AGithubRelease)


def test_repo_constructor():
    repo = github.GithubRepo("GITHUB", "NAME")
    assert isinstance(repo, github.AGithubRepo)
