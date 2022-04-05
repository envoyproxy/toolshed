from unittest.mock import PropertyMock

import pytest

from aio.api import github, nist

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

    assert checker.cves_class == check.DependencyCVEs
    assert "cves_class" not in checker.__dict__
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


@pytest.mark.parametrize("config", [None, "CONFIG"])
def test_checker_cves_constructor(patches, config):
    patched = patches(
        "check.ADependencyCVEs.__init__",
        prefix="envoy.dependency.check.checker")
    kwargs = (
        dict(config_path=config)
        if config
        else {})

    with patched as (m_super, ):
        m_super.return_value = None
        cves = check.DependencyCVEs("DEPENDENCIES", **kwargs)

    assert isinstance(cves, check.ADependencyCVEs)
    assert (
        m_super.call_args
        == [("DEPENDENCIES", ), kwargs])
    assert cves.cpe_class == nist.CPE
    assert "cpe_class" not in cves.__dict__
    assert cves.cve_class == check.DependencyCVE
    assert "cve_class" not in cves.__dict__
    assert cves.nist_downloader_class == nist.NISTDownloader
    assert "nist_downloader_class" not in cves.__dict__


def test_checker_cves_ignored_cves(patches):
    cves = check.DependencyCVEs("DEPENDENCIES")
    patched = patches(
        ("check.ADependencyCVEs.ignored_cves",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.checker")

    with patched as (m_super, ):
        assert cves.ignored_cves == m_super.return_value

    assert "ignored_cves" in cves.__dict__


def test_checker_cve_constructor(patches):
    patched = patches(
        "check.ADependencyCVE.__init__",
        prefix="envoy.dependency.check.checker")

    with patched as (m_super, ):
        m_super.return_value = None
        cve = check.DependencyCVE("CVE_DATA", "TRACKED CPES")

    assert isinstance(cve, check.ADependencyCVE)
    assert (
        m_super.call_args
        == [("CVE_DATA", "TRACKED CPES"), {}])
