
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from packaging import version

import pytest

import abstracts

from envoy.dependency.check import (
    abstract,
    AGithubDependencyReleaseIssue,
    AGithubDependencyReleaseIssues)


@abstracts.implementer(AGithubDependencyReleaseIssue)
class DummyGithubDependencyReleaseIssue:
    pass


@abstracts.implementer(AGithubDependencyReleaseIssues)
class DummyGithubDependencyReleaseIssues:

    @property
    def issue_class(self):
        return super().issue_class


def test_issue_constructor():
    issue = DummyGithubDependencyReleaseIssue("ISSUES", "ISSUE")
    assert issue.issues == "ISSUES"
    assert issue.issue == "ISSUE"
    assert issue.parse_vars == ("key", "version")
    assert "parse_vars" not in issue.__dict__


@pytest.mark.parametrize("parsed", [True, False])
@pytest.mark.parametrize("raises", [None, Exception, version.InvalidVersion])
def test_issue_version(patches, parsed, raises):
    issue = DummyGithubDependencyReleaseIssue("ISSUES", "ISSUE")
    patched = patches(
        "version.parse",
        ("AGithubDependencyReleaseIssue.parsed",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.issues")

    with patched as (m_version, m_parsed):
        if raises:
            error = raises("An error occurred")
            m_version.side_effect = error
        m_parsed.return_value = (
            dict(version=23)
            if parsed
            else {})
        if not parsed:
            assert not issue.version
        elif raises == version.InvalidVersion:
            assert not issue.version
        elif raises:
            with pytest.raises(raises):
                issue.version
        else:
            assert (
                issue.version
                == m_version.return_value)

    if not parsed:
        assert not m_version.called
        return
    if raises and raises != version.InvalidVersion:
        assert "version" not in issue.__dict__
    else:
        assert "version" in issue.__dict__
    assert (
        m_version.call_args
        == [(23, ), {}])


async def test_issue_close_old(patches):
    issue = DummyGithubDependencyReleaseIssue("ISSUES", "ISSUE")
    patched = patches(
        ("AGithubDependencyReleaseIssue.closing_tpl",
         dict(new_callable=PropertyMock)),
        ("AGithubDependencyReleaseIssue.number",
         dict(new_callable=PropertyMock)),
        ("AGithubDependencyReleaseIssue.repo_name",
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
        assert not await issue.close_old(old_issue, dep=dep)

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


def test_issues_constructor():
    with pytest.raises(TypeError):
        AGithubDependencyReleaseIssues("GITHUB")

    issues = DummyGithubDependencyReleaseIssues("GITHUB")

    with pytest.raises(NotImplementedError):
        issues.issue_class

    assert (
        issues.body_tpl
        == abstract.issues.BODY_TPL)
    assert (
        issues.closing_tpl
        == abstract.issues.CLOSING_TPL)
    assert (
        issues.labels
        == abstract.issues.LABELS)
    assert (
        issues.repo_name
        == abstract.issues.GITHUB_REPO_LOCATION)
    assert (
        issues.title_prefix
        == abstract.issues.TITLE_PREFIX)
    assert (
        issues.title_re_tpl
        == abstract.issues.TITLE_RE_TPL)
    assert (
        issues.title_tpl
        == abstract.issues.TITLE_TPL)
    props = [
        "body_tpl", "closing_tpl", "labels",
        "repo_name", "title_prefix", "title_re_tpl", "title_tpl"]
    for prop in props:
        assert prop not in issues.__dict__


@pytest.mark.parametrize("prop", ["issue_author", "issues_search_tpl"])
def test_issues_super_props(patches, prop):
    issues = DummyGithubDependencyReleaseIssues("GITHUB")
    patched = patches(
        (f"_github.AGithubTrackedIssues.{prop}",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.issues")

    with patched as (m_super, ):
        assert (
            getattr(issues, prop)
            == m_super.return_value)

    assert prop not in issues.__dict__


async def test_issues_issue_body(patches):
    issues = DummyGithubDependencyReleaseIssues("GITHUB")
    patched = patches(
        ("AGithubDependencyReleaseIssues.body_tpl",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.issues")

    dep = MagicMock()
    date = AsyncMock()
    mock_release = MagicMock()
    mock_release.date = date()
    newer_release = AsyncMock(return_value=mock_release)
    dep.newer_release = newer_release()
    release_date = AsyncMock()
    dep.release.date = release_date()

    with patched as (m_body_tpl, ):
        assert (
            await issues.issue_body(dep=dep)
            == m_body_tpl.return_value.format.return_value)

    assert (
        m_body_tpl.return_value.format.call_args
        == [(),
            dict(dep=dep,
                 newer_release=newer_release.return_value,
                 newer_release_date=date.return_value,
                 release_date=release_date.return_value)])


async def test_issues_issue_title(patches):
    issues = DummyGithubDependencyReleaseIssues("GITHUB")
    patched = patches(
        ("AGithubDependencyReleaseIssues.title_prefix",
         dict(new_callable=PropertyMock)),
        ("AGithubDependencyReleaseIssues.title_tpl",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.issues")

    dep = MagicMock()
    newer_release = AsyncMock()
    dep.newer_release = newer_release()

    with patched as (m_title_prefix, m_title_tpl):
        assert (
            await issues.issue_title(dep=dep)
            == m_title_tpl.return_value.format.return_value)

    assert (
        m_title_tpl.return_value.format.call_args
        == [(),
            dict(dep=dep,
                 newer_release=newer_release.return_value,
                 title_prefix=m_title_prefix.return_value)])


@pytest.mark.parametrize("is_dupe", [True, False])
@pytest.mark.parametrize("existing_version", [0, None, 7, 23])
@pytest.mark.parametrize("version", [0, None, 7, 23])
async def test_issues_track_issue(is_dupe, existing_version, version):
    issues = DummyGithubDependencyReleaseIssues("GITHUB")
    issue = MagicMock()
    issue.version = version
    existing_issues = MagicMock()
    existing_issues.__contains__.return_value = is_dupe
    existing_issues.__getitem__.return_value.version = existing_version
    expected = False
    if not is_dupe:
        expected = True
    elif not existing_version:
        expected = bool(version)
    elif not version:
        expected = bool(existing_version)
    else:
        expected = version > existing_version
    assert (
        issues.track_issue(existing_issues, issue)
        == expected)
