
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio.functional import async_property

from envoy.base.checker import AsyncChecker

from envoy.dependency.check import ADependencyChecker, exceptions


@abstracts.implementer(ADependencyChecker)
class DummyDependencyChecker:

    @property
    def access_token(self):
        return super().access_token

    @property
    def dependency_metadata(self):
        return super().dependency_metadata

    @property
    def github_dependency_class(self):
        return super().github_dependency_class

    @property
    def issues_class(self):
        return super().issues_class


def test_checker_constructor():

    with pytest.raises(TypeError):
        ADependencyChecker()

    checker = DummyDependencyChecker()
    assert isinstance(checker, AsyncChecker)
    assert checker.checks == ("dates", "issues", "releases")

    iface_props = [
        "dependency_metadata",
        "github_dependency_class", "issues_class"]

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(checker, prop)


@pytest.mark.parametrize("arg", [True, False])
def test_checker_access_token(patches, arg):
    checker = DummyDependencyChecker()
    patched = patches(
        "os",
        "pathlib",
        ("ADependencyChecker.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_os, m_plib, m_args):
        if not arg:
            m_args.return_value.github_token = None
        assert (
            checker.access_token
            == ((m_plib.Path.return_value
                       .read_text.return_value
                       .strip.return_value)
                if arg
                else m_os.getenv.return_value))

    if arg:
        assert not m_os.getenv.called
        assert (
            list(m_plib.Path.call_args)
            == [(m_args.return_value.github_token, ), {}])
        assert (
            list(m_plib.Path.return_value.read_text.call_args)
            == [(), {}])
        assert (
            list(m_plib.Path.return_value
                       .read_text.return_value
                       .strip.call_args)
            == [(), {}])
    else:
        assert not m_plib.Path.called
        assert (
            list(m_os.getenv.call_args)
            == [("GITHUB_TOKEN", ), {}])
    assert "access_token" not in checker.__dict__


def test_checker_dep_ids(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.dependencies",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")
    deps = [MagicMock()] * 5

    with patched as (m_deps, ):
        m_deps.return_value = deps
        assert checker.dep_ids == tuple(dep.id for dep in deps)

    assert "dep_ids" in checker.__dict__


@pytest.mark.parametrize(
    "failures",
    [{},
     {1: exceptions.NotGithubDependency, 2: exceptions.NotGithubDependency},
     {1: Exception, 2: exceptions.NotGithubDependency},
     {1: exceptions.NotGithubDependency, 2: Exception}])
def test_checker_dependencies(patches, failures):
    checker = DummyDependencyChecker()
    patched = patches(
        "sorted",
        "tuple",
        ("ADependencyChecker.dependency_metadata",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.github",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.github_dependency_class",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")
    deps = [(i, MagicMock()) for i in range(0, 5)]
    errors = {}

    def dep_class(i, v, github):
        if i in failures:
            errors[i] = failures[i]("BOOM")
            raise errors[i]
        return f"DEP{i}"

    does_fail = any(f == Exception for f in failures.values())

    with patched as (m_sorted, m_tuple, m_meta, m_github, m_dep, m_log):
        m_meta.return_value.items.return_value = deps
        m_dep.return_value.side_effect = dep_class

        if does_fail:
            with pytest.raises(Exception):
                checker.dependencies
            return

        assert checker.dependencies == m_tuple.return_value

    assert (
        list(m_tuple.call_args)
        == [(m_sorted.return_value, ), {}])
    assert (
        list(m_sorted.call_args)
        == [([f"DEP{i}"
              for i in range(0, 5)
              if i not in failures], ), {}])
    assert (
        list(list(c) for c in m_dep.return_value.call_args_list)
        == [[(i, dep, m_github.return_value), {}]
            for i, dep in deps])
    assert (
        list(list(c) for c in m_log.return_value.info.call_args_list)
        == [[(errors[i], ), {}]
            for i, v in deps if i in failures])
    assert "dependencies" in checker.__dict__


def test_checker_github(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        "github",
        ("ADependencyChecker.access_token",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_github, m_token, m_session):
        assert checker.github == m_github.GithubAPI.return_value

    assert (
        list(m_github.GithubAPI.call_args)
        == [(m_session.return_value, ""),
            dict(oauth_token=m_token.return_value)])
    assert "github" in checker.__dict__


def test_checker_issues(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.github",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.issues_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_github, m_issues):
        assert checker.issues == m_issues.return_value.return_value

    assert (
        list(m_issues.return_value.call_args)
        == [(m_github.return_value, ), {}])
    assert "issues" in checker.__dict__


def test_checker_session(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        "aiohttp",
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_aiohttp, ):
        assert checker.session == m_aiohttp.ClientSession.return_value

    assert (
        list(m_aiohttp.ClientSession.call_args)
        == [(), {}])
    assert "session" in checker.__dict__


def test_checker_sync_issues(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_args, ):
        assert checker.sync_issues == m_args.return_value.sync_issues

    assert "sync_issues" not in checker.__dict__


def test_checker_add_arguments(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        "checker.AsyncChecker.add_arguments",
        prefix="envoy.dependency.check.abstract.checker")
    parser = MagicMock()

    with patched as (m_super, ):
        assert not checker.add_arguments(parser)

    assert (
        list(m_super.call_args)
        == [(parser, ), {}])
    assert (
        list(list(c) for c in parser.add_argument.call_args_list)
        == [[('--github_token',), {}],
            [('--sync_issues',), {'action': 'store_true'}]])


@pytest.mark.asyncio
async def test_checker_check_dates(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.dependencies",
         dict(new_callable=PropertyMock)),
        "ADependencyChecker.dep_date_check",
        prefix="envoy.dependency.check.abstract.checker")
    deps = [MagicMock() for i in range(0, 5)]

    with patched as (m_deps, m_check):
        m_deps.return_value = deps
        assert not await checker.check_dates()

    assert (
        list(list(c) for c in m_check.call_args_list)
        == [[(mock,), {}] for mock in deps])


@pytest.mark.asyncio
async def test_checker_check_issues(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.dependencies",
         dict(new_callable=PropertyMock)),
        "ADependencyChecker.dep_issue_check",
        "ADependencyChecker.issues_missing_dep_check",
        "ADependencyChecker.issues_duplicate_check",
        "ADependencyChecker.issues_labels_check",
        prefix="envoy.dependency.check.abstract.checker")
    deps = [MagicMock() for i in range(0, 5)]

    with patched as (m_deps, m_dep_check, m_issue_check, m_dupes, m_labels):
        m_deps.return_value = deps
        assert not await checker.check_issues()

    assert (
        list(m_labels.call_args)
        == [(), {}])
    assert (
        list(m_issue_check.call_args)
        == [(), {}])
    assert (
        list(m_dupes.call_args)
        == [(), {}])
    assert (
        list(list(c) for c in m_dep_check.call_args_list)
        == [[(mock,), {}] for mock in deps])


@pytest.mark.asyncio
async def test_checker_check_releases(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.dependencies",
         dict(new_callable=PropertyMock)),
        "ADependencyChecker.dep_release_check",
        prefix="envoy.dependency.check.abstract.checker")
    deps = [MagicMock() for i in range(0, 5)]

    with patched as (m_deps, m_check):
        m_deps.return_value = deps
        assert not await checker.check_releases()

    assert (
        list(list(c) for c in m_check.call_args_list)
        == [[(mock,), {}] for mock in deps])


@pytest.mark.asyncio
@pytest.mark.parametrize("gh_date", [None, "GH_DATE"])
@pytest.mark.parametrize("mismatch", [True, False])
async def test_checker_dep_date_check(patches, gh_date, mismatch):
    checker = DummyDependencyChecker()
    patched = patches(
        "ADependencyChecker.error",
        "ADependencyChecker.succeed",
        prefix="envoy.dependency.check.abstract.checker")

    class DummyDepRelease:

        @async_property
        async def date(self):
            return gh_date

    class DummyDep:
        id = "DUMMY_DEP"
        release_date = "DUMMY_RELEASE_DATE"

        @property
        def release(self):
            return DummyDepRelease()

        @async_property
        async def release_date_mismatch(self):
            return mismatch

    dep = DummyDep()

    with patched as (m_error, m_succeed):
        assert not await checker.dep_date_check(dep)

    if not gh_date:
        assert (
            list(m_error.call_args)
            == [("dates",
                 ["DUMMY_DEP is a GitHub repository with no no inferrable "
                  "release date"]),
                {}])
        assert not m_succeed.called
        return
    if mismatch:
        assert (
            list(m_error.call_args)
            == [("dates",
                 ["Date mismatch: DUMMY_DEP "
                  f"DUMMY_RELEASE_DATE != {gh_date}"]),
                {}])
        assert not m_succeed.called
        return
    assert not m_error.called
    assert (
        list(m_succeed.call_args)
        == [("dates", ["Date matches(DUMMY_RELEASE_DATE): DUMMY_DEP"]),
            {}])


@pytest.mark.asyncio
@pytest.mark.parametrize("issue", [None, "ISSUE"])
@pytest.mark.parametrize("newer_release", [True, False])
@pytest.mark.parametrize("sync_issues", [True, False])
@pytest.mark.parametrize("version_matches", [True, False])
async def test_checker_dep_issue_check(
        patches, issue, newer_release, sync_issues, version_matches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.issues",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.sync_issues",
         dict(new_callable=PropertyMock)),
        "ADependencyChecker.succeed",
        "ADependencyChecker.warn",
        "ADependencyChecker._dep_issue_close_stale",
        "ADependencyChecker._dep_issue_create",
        prefix="envoy.dependency.check.abstract.checker")

    class DummyDep:
        id = "DUMMY_DEP"

        @async_property
        async def newer_release(self):
            if newer_release:
                mock_release = MagicMock()
                mock_release.version = "NEWER_RELEASE_NAME"
                return mock_release

    dep = DummyDep()
    issues_dict = MagicMock()

    if issue:
        mock_issue = MagicMock()
        if version_matches:
            mock_issue.version = "NEWER_RELEASE_NAME"
        issues_dict.get.return_value = mock_issue
    else:
        mock_issue = None
        issues_dict.get.return_value = None

    with patched as patchy:
        (m_issue, m_manage,
         m_succeed, m_warn, m_close, m_create) = patchy
        dep_issues = AsyncMock(return_value=issues_dict)
        m_issue.return_value.dep_issues = dep_issues()
        m_manage.return_value = sync_issues
        assert not await checker.dep_issue_check(dep)

    if not newer_release:
        assert not m_create.called
        if issue:
            assert (
                list(list(c) for c in m_warn.call_args_list)
                == [[('issues',
                    [f"Stale issue: DUMMY_DEP #{mock_issue.number}"]),
                    {}]])
            assert not m_succeed.called
            if sync_issues:
                assert (
                    list(m_close.call_args)
                    == [(mock_issue, dep), {}])
            else:
                assert not m_close.called
        else:
            assert (
                list(list(c) for c in m_succeed.call_args_list)
                == [[('issues',
                      ["No issue required: DUMMY_DEP"]),
                     {}]])
            assert not m_warn.called
            assert not m_close.called
            assert not m_manage.called
        return
    assert not m_close.called
    if issue:
        if version_matches:
            assert (
                list(list(c) for c in m_succeed.call_args_list)
                == [[('issues',
                      [f"Issue exists (#{mock_issue.number}): DUMMY_DEP"]),
                    {}]])
            assert not m_warn.called
            assert not m_manage.called
            assert not m_create.called
            return
        assert (
            list(list(c) for c in m_warn.call_args_list)
            == [[('issues',
                  [f"Out-of-date issue (#{mock_issue.number}): "
                   f"DUMMY_DEP ({mock_issue.version} -> NEWER_RELEASE_NAME)"]),
                 {}]])
    assert not m_succeed.called
    if sync_issues:
        assert (
            list(m_create.call_args)
            == [(mock_issue, dep), {}])
    else:
        assert not m_create.called


@pytest.mark.asyncio
@pytest.mark.parametrize("newer_release", [True, False])
@pytest.mark.parametrize("recent_commits", [True, False])
async def test_checker_dep_release_check(
        patches, newer_release, recent_commits):
    checker = DummyDependencyChecker()
    patched = patches(
        "ADependencyChecker.warn",
        "ADependencyChecker.succeed",
        prefix="envoy.dependency.check.abstract.checker")

    class DummyDep:
        id = "DUMMY_DEP"
        release_date = "DUMMY_RELEASE_DATE"
        github_version_name = "GH_VERSION_NAME"

        @async_property
        async def has_recent_commits(self):
            return recent_commits

        @async_property
        async def newer_release(self):
            if newer_release:
                mock_release = MagicMock()
                mock_release.tag_name = "NEWER_RELEASE_NAME"
                mock_release.date = AsyncMock(
                    return_value="NEWER_RELEASE_DATE")()
                return mock_release

        @async_property
        async def recent_commits(self):
            return 23

    dep = DummyDep()

    with patched as (m_warn, m_succeed):
        assert not await checker.dep_release_check(dep)

    if newer_release:
        assert (
            list(m_warn.call_args)
            == [("releases",
                ["Newer release (NEWER_RELEASE_NAME): DUMMY_DEP\n"
                 "DUMMY_RELEASE_DATE "
                 "GH_VERSION_NAME\n"
                 "NEWER_RELEASE_DATE "
                 "NEWER_RELEASE_NAME "]),
                {}])
        assert not m_succeed.called
        return
    if recent_commits:
        assert (
            list(m_warn.call_args)
            == [("releases",
                ["Recent commits (23): DUMMY_DEP\n"
                 "There have been 23 commits since "
                 "GH_VERSION_NAME landed on "
                 "DUMMY_RELEASE_DATE"]),
                {}])
        assert not m_succeed.called
        return
    assert not m_warn.called
    assert (
        list(m_succeed.call_args)
        == [("releases", ["Up-to-date (GH_VERSION_NAME): DUMMY_DEP"]),
            {}])


@pytest.mark.asyncio
async def test_checker_on_checks_complete(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        "checker.AsyncChecker.on_checks_complete",
        ("ADependencyChecker.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_super, m_session):
        m_session.return_value.close = AsyncMock()
        assert await checker.on_checks_complete() == m_super.return_value

    assert (
        list(m_session.return_value.close.call_args)
        == [(), {}])


@pytest.mark.asyncio
@pytest.mark.parametrize("sync_issues", [True, False])
@pytest.mark.parametrize("dupes", [0, 1, 3, 5])
async def test_checker_issues_duplicate_check(patches, sync_issues, dupes):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.issues",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.sync_issues",
         dict(new_callable=PropertyMock)),
        "ADependencyChecker.warn",
        "ADependencyChecker.succeed",
        "ADependencyChecker._issue_close_duplicate",
        prefix="envoy.dependency.check.abstract.checker")
    mock_dupes = []

    for dupe in range(0, dupes):
        mock_dupe = MagicMock()
        mock_dupes.append(mock_dupe)

    async def dupe_iter():
        for dupe in mock_dupes:
            yield dupe

    with patched as (m_issues, m_manage, m_warn, m_succeed, m_close):
        m_manage.return_value = sync_issues
        m_issues.return_value.duplicate_issues = dupe_iter()
        assert not await checker.issues_duplicate_check()

    assert (
        list(list(c) for c in m_warn.call_args_list)
        == [[('issues',
              [f"Duplicate issue for dependency (#{issue.number}): "
               f"{issue.dep}"]), {}]
            for issue in mock_dupes])
    if sync_issues:
        assert (
            list(list(c) for c in m_close.call_args_list)
            == [[(issue, ), {}]
                for issue in mock_dupes])
    else:
        assert not m_close.called
    if not dupes:
        assert not m_warn.called
        assert not m_close.called
        assert (
            list(list(c) for c in m_succeed.call_args_list)
            == [[('issues',
                ["No duplicate issues found."]),
                {}]])
    else:
        assert not m_succeed.called


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "missing_labels",
    [[],
     [f"LABEL{i}" for i in range(0, 5)]])
async def test_checker_issues_labels_check(patches, missing_labels):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.issues",
         dict(new_callable=PropertyMock)),
        "ADependencyChecker.error",
        "ADependencyChecker.succeed",
        prefix="envoy.dependency.check.abstract.checker")

    with patched as (m_issues, m_error, m_succeed):
        m_issues.return_value.missing_labels = AsyncMock(
            return_value=missing_labels)()
        assert not await checker.issues_labels_check()

    assert (
        list(list(c) for c in m_error.call_args_list)
        == [[("issues", [f"Missing label: {label}"]), {}]
            for label in missing_labels])
    if not missing_labels:
        assert not m_error.called
        assert (
            list(list(c) for c in m_succeed.call_args_list)
            == [[('issues',
                [f"All ({m_issues.return_value.labels.__len__.return_value}) "
                 "required labels are available."]),
                {}]])
    else:
        assert not m_succeed.called


@pytest.mark.asyncio
@pytest.mark.parametrize("sync_issues", [True, False])
@pytest.mark.parametrize(
    "open_issues",
    [[],
     [True, False, True],
     [False, False, False],
     [True, True, True]])
async def test_checker_issues_missing_dep_check(
        patches, sync_issues, open_issues):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.dep_ids",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.issues",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.sync_issues",
         dict(new_callable=PropertyMock)),
        "ADependencyChecker.warn",
        "ADependencyChecker.succeed",
        "ADependencyChecker._issue_close_missing_dep",
        prefix="envoy.dependency.check.abstract.checker")
    ids = []
    mock_issues = []
    should_fail = any(open_issues)

    for issue in open_issues:
        mock_issue = MagicMock()
        if not issue:
            ids.append(mock_issue.dep)
        mock_issues.append(mock_issue)

    with patched as (m_ids, m_issues, m_manage, m_warn, m_succeed, m_close):
        m_issues.return_value.open_issues = AsyncMock(
            return_value=mock_issues)()
        m_ids.return_value = ids
        m_manage.return_value = sync_issues
        assert not await checker.issues_missing_dep_check()

    assert (
        list(list(c) for c in m_warn.call_args_list)
        == [[('issues',
              [f"Missing dependency (#{issue.number}): {issue.dep}"]), {}]
            for issue in mock_issues if issue.dep not in ids])
    if sync_issues:
        assert (
            list(list(c) for c in m_close.call_args_list)
            == [[(issue, ), {}]
                for issue in mock_issues if issue.dep not in ids])
    else:
        assert not m_close.called
    if not should_fail:
        assert not m_warn.called
        assert not m_close.called
        assert (
            list(list(c) for c in m_succeed.call_args_list)
            == [[('issues',
                [f"All ({len(open_issues)}) issues have "
                 "current dependencies."]),
                {}]])
    else:
        assert not m_succeed.called


@pytest.mark.asyncio
async def test_checker__dep_issue_close_stale(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")
    issue = AsyncMock()
    dep = MagicMock()

    with patched as (m_log, ):
        assert not await checker._dep_issue_close_stale(issue, dep)

    assert (
        list(issue.close.call_args)
        == [(), {}])
    assert (
        list(m_log.return_value.notice.call_args)
        == [(f"Closed stale issue (#{issue.number}): {dep.id}\n"
             f"{issue.title}\n{issue.body}", ), {}])


@pytest.mark.asyncio
@pytest.mark.parametrize("issue", [True, False])
@pytest.mark.parametrize("missing_labels", [True, False])
async def test_checker__dep_issue_create(patches, issue, missing_labels):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.issues",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.log",
         dict(new_callable=PropertyMock)),
        "ADependencyChecker.error",
        prefix="envoy.dependency.check.abstract.checker")
    issue = (
        AsyncMock()
        if issue
        else None)
    dep = MagicMock()

    with patched as (m_issues, m_log, m_error):
        m_issues.return_value.missing_labels = AsyncMock(
            return_value=missing_labels)()
        create = AsyncMock()
        m_issues.return_value.create = create
        assert not await checker._dep_issue_create(issue, dep)

    if missing_labels:
        assert (
            list(m_error.call_args)
            == [("issues",
                 [f"Unable to create issue for {dep.id}: missing labels"]),
                {}])
        assert not m_log.return_value.called
        assert not create.called
        return

    assert not m_error.called
    new_issue = create.return_value
    assert (
        list(m_log.return_value.notice.call_args_list[0])
        == [(f"Created issue (#{new_issue.number}): "
             f"{dep.id} {new_issue.version}\n"
             f"{new_issue.title}\n{new_issue.body}", ), {}])
    if not issue:
        assert len(m_log.return_value.notice.call_args_list) == 1
        assert not new_issue.close_old.called
        return
    assert len(m_log.return_value.notice.call_args_list) == 2
    assert (
        list(new_issue.close_old.call_args)
        == [(issue, dep), {}])
    assert (
        list(m_log.return_value.notice.call_args_list[1])
        == [(f"Closed old issue (#{issue.number}): "
             f"{dep.id} {issue.version}\n"
             f"{issue.title}\n{issue.body}", ), {}])


@pytest.mark.asyncio
async def test_checker__issue_close_duplicate(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.issues",
         dict(new_callable=PropertyMock)),
        ("ADependencyChecker.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")
    issue = AsyncMock()
    issue.dep = "DEP"
    current_issue = AsyncMock()
    issues_dict = dict(DEP=current_issue)

    with patched as (m_issues, m_log):
        dep_issues = AsyncMock(return_value=issues_dict)
        m_issues.return_value.dep_issues = dep_issues()
        assert not await checker._issue_close_duplicate(issue)

    assert (
        list(current_issue.close_duplicate.call_args)
        == [(issue, ), {}])
    assert (
        list(m_log.return_value.notice.call_args)
        == [(f"Closed duplicate issue (#{issue.number}): {issue.dep}\n"
             f" {issue.title}\n"
             f"current issue #({current_issue.number}):\n"
             f" {current_issue.title}", ),
            {}])


@pytest.mark.asyncio
async def test_checker__issue_close_missing_dep(patches):
    checker = DummyDependencyChecker()
    patched = patches(
        ("ADependencyChecker.log",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.checker")
    issue = AsyncMock()

    with patched as (m_log, ):
        assert not await checker._issue_close_missing_dep(issue)

    assert (
        list(issue.close.call_args)
        == [(), {}])
    assert (
        list(m_log.return_value.notice.call_args)
        == [(f"Closed issue with no current dependency (#{issue.number})", ),
            {}])
