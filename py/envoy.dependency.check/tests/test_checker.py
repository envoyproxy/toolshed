from unittest.mock import PropertyMock

from aio.api import github

from envoy.dependency import check


def test_checker_checker_constructor(patches):
    patched = patches(
        "check.ADependencyChecker.__init__",
        prefix="envoy.dependency.check.checker")

    with patched as (m_super, ):
        m_super.return_value = None
        checker = check.DependencyChecker()

    assert isinstance(checker, check.ADependencyChecker)
    assert (
        m_super.call_args
        == [(), {}])

    assert checker.dependency_class == check.Dependency
    assert "dependency_class" not in checker.__dict__
    assert checker.issues_class == check.GithubDependencyIssuesTracker
    assert "issues_class" not in checker.__dict__


def test_checker_checker_access_token(patches):
    checker = check.DependencyChecker()
    patched = patches(
        ("check.ADependencyChecker.access_token",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.checker")

    with patched as (m_super, ):
        assert checker.access_token == m_super.return_value

    assert "access_token" not in checker.__dict__


def test_checker_checker_dependency_metadata(patches):
    checker = check.DependencyChecker()
    patched = patches(
        ("check.ADependencyChecker.dependency_metadata",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.checker")

    with patched as (m_super, ):
        assert checker.dependency_metadata == m_super.return_value

    assert "dependency_metadata" in checker.__dict__


def test_checker_dependency_constructor(patches):
    patched = patches(
        "check.ADependency.__init__",
        prefix="envoy.dependency.check.checker")

    with patched as (m_super, ):
        m_super.return_value = None
        dependency = check.Dependency("ID", "METADATA", "GITHUB")

    assert isinstance(dependency, check.ADependency)
    assert (
        m_super.call_args
        == [("ID", "METADATA", "GITHUB"), {}])
    assert dependency.release_class == check.DependencyGithubRelease
    assert "release_class" not in dependency.__dict__


def test_checker_release_constructor(patches):
    patched = patches(
        "check.ADependencyGithubRelease.__init__",
        prefix="envoy.dependency.check.checker")

    with patched as (m_super, ):
        m_super.return_value = None
        checker = check.DependencyGithubRelease("REPO", "VERSION")

    assert isinstance(checker, check.ADependencyGithubRelease)
    assert (
        m_super.call_args
        == [("REPO", "VERSION"), {}])


def test_checker_issue_constructor(patches):
    patched = patches(
        "check.AGithubDependencyReleaseIssue.__init__",
        prefix="envoy.dependency.check.checker")

    with patched as (m_super, ):
        m_super.return_value = None
        issue = check.GithubDependencyReleaseIssue("ISSUES", "ISSUE")

    assert isinstance(issue, check.AGithubDependencyReleaseIssue)
    assert (
        m_super.call_args
        == [("ISSUES", "ISSUE"), {}])


def test_checker_issues_constructor(patches):
    patched = patches(
        "check.AGithubDependencyReleaseIssues.__init__",
        prefix="envoy.dependency.check.checker")

    with patched as (m_super, ):
        m_super.return_value = None
        issues = check.GithubDependencyReleaseIssues("GITHUB")

    assert isinstance(issues, check.AGithubDependencyReleaseIssues)
    assert (
        m_super.call_args
        == [("GITHUB", ), {}])
    assert issues.issue_class == check.GithubDependencyReleaseIssue
    assert "issue_class" not in issues.__dict__


def test_checker_issues_labels():
    issues = check.GithubDependencyReleaseIssues("GITHUB")
    assert issues.labels == check.checker.LABELS
    assert "labels" not in issues.__dict__


def test_checker_issues_repo_name():
    issues = check.GithubDependencyReleaseIssues("GITHUB")
    assert issues.repo_name == check.checker.GITHUB_REPO_LOCATION
    assert "repo_name" not in issues.__dict__


def test_checker_issues_tracker_constructor(patches):
    patched = patches(
        "github.AGithubIssuesTracker.__init__",
        prefix="envoy.dependency.check.checker")

    with patched as (m_super, ):
        m_super.return_value = None
        tracker = check.GithubDependencyIssuesTracker()

    assert isinstance(tracker, github.IGithubIssuesTracker)
    assert (
        m_super.call_args
        == [(), {}])


def test_checker_issues_tracker_tracked_issues(patches):
    tracker = check.GithubDependencyIssuesTracker("GITHUB")
    patched = patches(
        "GithubDependencyReleaseIssues",
        prefix="envoy.dependency.check.checker")
    tracker.github = "GITHUB"

    with patched as (m_release, ):
        assert (
            tracker.tracked_issues
            == dict(releases=m_release.return_value))

    assert "tracked_issues" in tracker.__dict__


def test_checker_checker_no_dep_issues_re():
    checker = check.DependencyChecker()
    assert checker.no_dep_issues_re == check.checker.NO_ISSUE_DEPENDENCIES
    assert "no_dep_issues_re" not in checker.__dict__
