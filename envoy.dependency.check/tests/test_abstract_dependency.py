
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from packaging import version

import pytest

import abstracts

from aio.core import event

from envoy.dependency.check import ADependency, exceptions


@abstracts.implementer(ADependency)
class DummyDependency:

    @property
    def release_class(self):
        return super().release_class


class DummyDependency2(DummyDependency):

    def __init__(self, id, metadata, github):
        self.id = id
        self.metadata = metadata
        self.github = github


@pytest.mark.parametrize("loop", [None, "", "LOOP"])
@pytest.mark.parametrize("pool", [None, "", "POOL"])
def test_dependency_constructor(patches, loop, pool):
    kwargs = {}
    if loop is not None:
        kwargs["loop"] = loop
    if pool is not None:
        kwargs["pool"] = pool

    with pytest.raises(TypeError):
        ADependency("ID", "METADATA", "GITHUB", **kwargs)

    dependency = DummyDependency("ID", "METADATA", "GITHUB", **kwargs)
    assert dependency.id == "ID"
    assert dependency.metadata == "METADATA"
    assert dependency.github == "GITHUB"
    assert dependency.github_filetypes == {".zip", ".tar.gz"}
    assert dependency._loop == loop
    assert dependency._pool == pool
    assert "github_filetypes" not in dependency.__dict__
    assert isinstance(dependency, event.IReactive)


@pytest.mark.parametrize("id", range(0, 3))
@pytest.mark.parametrize("other_id", range(0, 3))
def test_dependency_dunder_gt(id, other_id):
    dependency1 = DummyDependency2(id, "METADATA", "GITHUB")
    dependency2 = DummyDependency2(other_id, "METADATA", "GITHUB")
    assert (dependency1 > dependency2) == (id > other_id)


@pytest.mark.parametrize("id", range(0, 3))
@pytest.mark.parametrize("other_id", range(0, 3))
def test_dependency_dunder_lt(id, other_id):
    dependency1 = DummyDependency2(id, "METADATA", "GITHUB")
    dependency2 = DummyDependency2(other_id, "METADATA", "GITHUB")
    assert (dependency1 < dependency2) == (id < other_id)


def test_dependency_dunder_str(patches):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.display_version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_version, ):
        assert (
            str(dependency)
            == f"ID@{m_version.return_value}")


@pytest.mark.parametrize("count", [None] + list(range(0, 3)))
async def test_dependency_commits_since_current(patches, count):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.release",
         dict(new_callable=PropertyMock)),
        ("ADependency.repo",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_release, m_repo):
        m_repo.return_value.commits.return_value.total_count = AsyncMock(
            return_value=count)()
        m_release.return_value.timestamp_commit = AsyncMock(
            return_value="TIMESTAMP")()
        result = await dependency.commits_since_current
        assert (
            result
            == (count and count - 1 or count))

    assert (
        m_repo.return_value.commits.call_args
        == [(), dict(since="TIMESTAMP")])
    assert (
        getattr(
            dependency,
            ADependency.commits_since_current.cache_name)[
                "commits_since_current"]
        == result)


@pytest.mark.parametrize(
    "metadata", [dict(), dict(cpe="N/A"), dict(cpe="CPE")])
def test_dependency_cpe(metadata):
    dependency = DummyDependency2("ID", metadata, "GITHUB")
    expected = (
        metadata["cpe"]
        if "cpe" in metadata and not metadata["cpe"] == "N/A"
        else None)
    assert dependency.cpe == expected
    assert "cpe" in dependency.__dict__


def test_dependency_display_sha(patches):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.release_sha",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_sha, ):
        assert (
            dependency.display_sha
            == m_sha.return_value.__getitem__.return_value)

    assert (
        m_sha.return_value.__getitem__.call_args
        == [(slice(None, 10), )])
    assert "display_sha" in dependency.__dict__


@pytest.mark.parametrize("tagged", [True, False])
def test_dependency_display_version(patches, tagged):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.release",
         dict(new_callable=PropertyMock)),
        ("ADependency.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_release, m_version):
        m_release.return_value.tagged = tagged
        assert (
            dependency.display_version
            == (m_version.return_value.__getitem__.return_value
                if not tagged
                else m_version.return_value))

    if tagged:
        assert not m_version.return_value.__getitem__.called
    else:
        assert (
            m_version.return_value.__getitem__.call_args
            == [(slice(None, 10), )])
    assert "display_version" in dependency.__dict__


@pytest.mark.parametrize(
    "urls",
    [[False, False, True],
     [False, False, False],
     [False, True, True]])
def test_dependency_github_url(patches, urls):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.urls",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    mock_urls = []
    expected_url = ""
    for url in urls:
        mock_url = MagicMock()
        mock_url.startswith.return_value = url
        if url and not expected_url:
            expected_url = mock_url
        mock_urls.append(mock_url)

    with patched as (m_urls, ):
        m_urls.return_value = mock_urls
        assert dependency.github_url == expected_url

    for i, url in enumerate(urls):
        mock_url = mock_urls[i]
        assert (
            mock_url.startswith.call_args
            == [('https://github.com/',), {}])
        if url:
            for other_url in mock_urls[i + 1:]:
                assert not other_url.startswith.called
            break
    assert "github_url" in dependency.__dict__


@pytest.mark.parametrize("archive", [True, False])
@pytest.mark.parametrize("release", [True, False])
@pytest.mark.parametrize(
    "filetypes",
    [[], ["A", "B", "C"], ["A", "B", "Z"], ["X", "Y", "Z"]])
@pytest.mark.parametrize("endswith", ["X", "Y", "Z"])
def test_dependency_github_version(
        patches, archive, release, filetypes, endswith):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        "len",
        ("ADependency.github_filetypes",
         dict(new_callable=PropertyMock)),
        ("ADependency.url_components",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")
    component = MagicMock()
    component.endswith.side_effect = lambda x: x == endswith
    result = None

    def get_component(item):
        if item == 5:
            if archive:
                return "archive"
            if release:
                return "releases"
        return component

    with patched as (m_len, m_filetypes, m_components):
        m_filetypes.return_value = filetypes
        m_components.return_value.__getitem__.side_effect = get_component
        m_len.return_value = 73

        if not archive and not release:
            with pytest.raises(exceptions.BadGithubURL) as e:
                dependency.github_version
            assert (
                e.value.args[0]
                == ("Unable to parse github URL components: "
                    f"{component}"))
        elif archive and (endswith not in filetypes):
            with pytest.raises(exceptions.BadGithubURL) as e:
                dependency.github_version
            assert (
                e.value.args[0]
                == ("Unrecognized Github release asset: "
                    f"{component}"))
        else:
            result = dependency.github_version

    if result:
        assert "github_version" in dependency.__dict__

    assert (
        m_components.return_value.__getitem__.call_args_list[0]
        == [(5, ), {}])
    if not archive:
        assert not m_filetypes.called
        assert not component.endswith.called
        assert (
            m_components.return_value.__getitem__.call_args_list[1]
            == [(5, ), {}])
        if not release:
            assert (
                m_components.return_value.__getitem__.call_args_list[2]
                == [(slice(3, None, None), ), {}])
            assert not result
        else:
            assert (
                len(m_components.return_value.__getitem__.call_args_list)
                == 3)
            assert (
                m_components.return_value.__getitem__.call_args_list[2]
                == [(7, ), {}])
            assert result == component
        return
    if endswith not in filetypes:
        assert (
            m_components.return_value.__getitem__.call_args_list[1:-1]
            == [[(-1, ), {}]] * len(filetypes))
        assert (
            m_components.return_value.__getitem__.call_args_list[-1]
            == [(slice(3, None, None), ), {}])
        assert not result
        return
    assert (
        m_components.return_value.__getitem__.call_args_list[1:]
        == [[(-1, ), {}]] * (len(filetypes[:filetypes.index(endswith)]) + 2))
    assert (
        component.endswith.call_args_list
        == [[(filetype, ), {}]
            for filetype in filetypes[:filetypes.index(endswith) + 1]])
    assert (
        result
        == component.__getitem__.return_value)
    assert (
        component.__getitem__.call_args
        == [(slice(None, -73), ), {}])
    assert (
        m_len.call_args
        == [(endswith, ), {}])


@pytest.mark.parametrize("tagged", [True, False])
def test_dependency_github_version_name(patches, tagged):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.github_version",
         dict(new_callable=PropertyMock)),
        ("ADependency.release",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_version, m_release):
        m_release.return_value.tagged = tagged
        assert (
            dependency.github_version_name
            == (m_version.return_value.__getitem__.return_value
                if not tagged
                else m_version.return_value))

    assert "github_version_name" not in dependency.__dict__
    if tagged:
        assert not m_version.return_value.__getitem__.called
        return
    assert (
        m_version.return_value.__getitem__.call_args
        == [(slice(0, 7), ), {}])


@pytest.mark.parametrize("commits", range(0, 5))
async def test_dependency_has_recent_commits(patches, commits):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.recent_commits",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_recent, ):
        m_recent.return_value = AsyncMock(return_value=commits)()
        assert await dependency.has_recent_commits == (commits > 1)

    assert not getattr(
        dependency,
        ADependency.has_recent_commits.cache_name,
        None)


@pytest.mark.parametrize("newest", [None, "BINGO", "BLOOP"])
async def test_dependency_newer_release(patches, newest):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        "version",
        ("ADependency.release",
         dict(new_callable=PropertyMock)),
        ("ADependency.release_class",
         dict(new_callable=PropertyMock)),
        ("ADependency.repo",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    if newest:
        newer_release = MagicMock()
        newer_release.tag_name = newest
    else:
        newer_release = None

    with patched as (m_version, m_release, m_class, m_repo):
        m_version.parse.side_effect = lambda x: x
        m_release.return_value.version = "BLOOP"
        timestamp = AsyncMock()
        m_release.return_value.timestamp = timestamp()
        m_repo.return_value.highest_release = AsyncMock(
            return_value=newer_release)
        result = await dependency.newer_release
        assert (
            result
            == (m_class.return_value.return_value
                if newest and newest != "BLOOP"
                else None))

    if newest and newest != "BLOOP":
        assert (
            m_class.return_value.call_args
            == [(m_repo.return_value, newest),
                dict(release=newer_release)])
    else:
        assert not m_class.called
    assert (
        m_repo.return_value.highest_release.call_args
        == [(), dict(since=timestamp.return_value)])
    assert (
        getattr(
            dependency,
            ADependency.newer_release.cache_name)[
                "newer_release"]
        == result)


def test_dependency_organization(patches):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.url_components",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_components, ):
        assert (
            dependency.organization
            == m_components.return_value.__getitem__.return_value)

    assert (
        m_components.return_value.__getitem__.call_args
        == [(3, ), {}])
    assert "organization" not in dependency.__dict__


def test_dependency_project(patches):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.url_components",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_components, ):
        assert (
            dependency.project
            == m_components.return_value.__getitem__.return_value)

    assert (
        m_components.return_value.__getitem__.call_args
        == [(4, ), {}])
    assert "project" not in dependency.__dict__


@pytest.mark.parametrize("tagged", [True, False])
async def test_dependency_recent_commits(patches, tagged):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.commits_since_current",
         dict(new_callable=PropertyMock)),
        ("ADependency.release",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_commits, m_release):
        m_release.return_value.tagged = tagged
        commits = AsyncMock()
        m_commits.side_effect = commits
        result = await dependency.recent_commits
        assert (
            result
            == (commits.return_value
                if not tagged
                else 0))

    assert (
        getattr(
            dependency,
            ADependency.recent_commits.cache_name)[
                "recent_commits"]
        == result)


def test_dependency_release(patches):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.github_version",
         dict(new_callable=PropertyMock)),
        ("ADependency.github_url",
         dict(new_callable=PropertyMock)),
        ("ADependency.loop",
         dict(new_callable=PropertyMock)),
        ("ADependency.pool",
         dict(new_callable=PropertyMock)),
        ("ADependency.release_class",
         dict(new_callable=PropertyMock)),
        ("ADependency.repo",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_version, m_url, m_loop, m_pool, m_class, m_repo):
        assert dependency.release == m_class.return_value.return_value

    assert (
        m_class.return_value.call_args
        == [(m_repo.return_value,
             m_version.return_value),
            dict(asset_url=m_url.return_value,
                 loop=m_loop.return_value,
                 pool=m_pool.return_value)])
    assert "release" in dependency.__dict__


def test_dependency_release_date():
    metadata = MagicMock()
    dependency = DummyDependency2("ID", metadata, "GITHUB")
    assert dependency.release_date == metadata.__getitem__.return_value
    assert "release_date" not in dependency.__dict__


@pytest.mark.parametrize("date1", range(0, 5))
@pytest.mark.parametrize("date2", range(0, 5))
async def test_dependency_release_date_mismatch(patches, date1, date2):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.release",
         dict(new_callable=PropertyMock)),
        ("ADependency.release_date",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_release, m_date):
        m_date.return_value = date1
        m_release.return_value.date = AsyncMock(return_value=date2)()
        assert await dependency.release_date_mismatch == (date1 != date2)

    assert not getattr(
        dependency,
        ADependency.release_date_mismatch.cache_name,
        None)


def test_dependency_sha():
    metadata = MagicMock()
    dependency = DummyDependency2("ID", metadata, "GITHUB")
    assert dependency.release_sha == metadata.__getitem__.return_value


@pytest.mark.parametrize("sha1", range(0, 5))
@pytest.mark.parametrize("sha2", range(0, 5))
async def test_dependency_sha_mismatch(patches, sha1, sha2):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.release",
         dict(new_callable=PropertyMock)),
        ("ADependency.release_sha",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_release, m_sha):
        m_sha.return_value = sha1
        m_release.return_value.sha = AsyncMock(return_value=sha2)()
        assert await dependency.release_sha_mismatch == (sha1 != sha2)

    assert not getattr(
        dependency,
        ADependency.release_sha_mismatch.cache_name,
        None)


@pytest.mark.parametrize("raises", [None, version.InvalidVersion, Exception])
def test_dependency_release_version(patches, raises):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        "version.Version",
        ("ADependency.version", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_version, m_dep_version):
        if raises:
            m_version.side_effect = raises
        if raises == Exception:
            with pytest.raises(Exception):
                dependency.release_version
        else:
            assert (
                dependency.release_version
                == (m_version.return_value if not raises else None))

    assert (
        m_version.call_args
        == [(m_dep_version.return_value, ), {}])
    if raises != Exception:
        assert "release_version" in dependency.__dict__


def test_dependency_repo(patches):
    github = MagicMock()
    dependency = DummyDependency2("ID", "METADATA", github)
    patched = patches(
        ("ADependency.organization",
         dict(new_callable=PropertyMock)),
        ("ADependency.project",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_org, m_project):
        assert (
            dependency.repo
            == github.__getitem__.return_value)

    assert (
        github.__getitem__.call_args
        == [(f"{m_org.return_value}/{m_project.return_value}", ), {}])
    assert "repo" in dependency.__dict__


@pytest.mark.parametrize("github_url", [True, False])
def test_dependency_url_components(iters, patches, github_url):
    dependency = DummyDependency2("ID", "METADATA", "GITHUB")
    patched = patches(
        ("ADependency.github_url",
         dict(new_callable=PropertyMock)),
        ("ADependency.urls",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")
    urls = iters()

    with patched as (m_url, m_urls):
        if not github_url:
            m_url.return_value = None
        m_urls.return_value = urls

        if not github_url:
            with pytest.raises(exceptions.NotGithubDependency) as e:
                dependency.url_components
            urls = "\n".join(urls)
            assert (
                e.value.args[0]
                == f'ID is not a GitHub repository\n{urls}')
        else:
            assert (
                dependency.url_components
                == m_url.return_value.split.return_value)

    if github_url:
        assert (
            m_url.return_value.split.call_args
            == [("/", ), {}])
        assert "url_components" in dependency.__dict__


def test_dependency_urls():
    metadata = MagicMock()
    dependency = DummyDependency2("ID", metadata, "GITHUB")
    assert dependency.urls == metadata.__getitem__.return_value
    assert "release_date" not in dependency.__dict__


def test_dependency_version():
    metadata = MagicMock()
    dependency = DummyDependency2("ID", metadata, "GITHUB")
    assert dependency.version == metadata.__getitem__.return_value
    assert "version" not in dependency.__dict__
