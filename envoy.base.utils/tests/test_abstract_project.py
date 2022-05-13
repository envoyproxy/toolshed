
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from envoy.base.utils import abstract, exceptions, interface


@abstracts.implementer(interface.IProject)
class DummyProject(abstract.AProject):

    @property
    def changelogs_class(self):
        return super().changelogs_class

    @property
    def inventories_class(self):
        return super().inventories_class


@pytest.mark.parametrize("path", [None, "PATH"])
def test_abstract_project_constructor(path):
    args = (
        (path, )
        if path is not None
        else ())

    with pytest.raises(TypeError):
        abstract.AProject(*args)

    project = DummyProject(*args)
    assert project._path == (path or ".")

    iface_props = ["changelogs_class", "inventories_class"]

    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(project, prop)


@pytest.mark.parametrize("main_dev", [True, False])
def test_abstract_project_archived_versions(patches, main_dev):
    project = DummyProject()
    patched = patches(
        "tuple",
        "reversed",
        "sorted",
        ("AProject.is_main_dev",
         dict(new_callable=PropertyMock)),
        ("AProject.minor_versions",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")
    offset = (
        5
        if main_dev
        else 4)

    with patched as (m_tuple, m_rev, m_sort, m_mdev, m_versions):
        m_mdev.return_value = main_dev
        assert (
            project.archived_versions
            == m_tuple.return_value.__getitem__.return_value)

    assert (
        m_tuple.call_args
        == [(m_rev.return_value, ), {}])
    assert (
        m_rev.call_args
        == [(m_sort.return_value, ), {}])
    assert (
        m_sort.call_args
        == [(m_versions.return_value.keys.return_value, ), {}])
    assert (
        m_versions.return_value.keys.call_args
        == [(), {}])
    assert (
        m_tuple.return_value.__getitem__.call_args
        == [(slice(offset, None),), {}])

    assert "archived_versions" in project.__dict__


def test_abstract_project_changelogs(patches):
    project = DummyProject()
    patched = patches(
        ("AProject.changelogs_class",
         dict(new_callable=PropertyMock)),
        ("AProject.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_class, m_version):
        assert (
            project.changelogs
            == m_class.return_value.return_value)

    assert (
        m_class.return_value.call_args
        == [(project, ), {}])
    assert "changelogs" in project.__dict__


def test_abstract_project_datestamp(patches):
    project = DummyProject()
    patched = patches(
        "datetime",
        "DATE_FORMAT",
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_dt, m_fmt):
        assert (
            project.datestamp
            == (m_dt.utcnow.return_value
                    .date.return_value
                    .strftime.return_value))

    assert (
        m_dt.utcnow.call_args
        == [(), {}])
    assert (
        m_dt.utcnow.return_value.date.call_args
        == [(), {}])
    assert (
        m_dt.utcnow.return_value.date.return_value.strftime.call_args
        == [(m_fmt, ), {}])
    assert "datestamp" not in project.__dict__


@pytest.mark.parametrize("is_dev", [True, False])
def test_abstract_project_dev_version(patches, is_dev):
    project = DummyProject()
    patched = patches(
        ("AProject.changelogs",
         dict(new_callable=PropertyMock)),
        ("AProject.is_dev",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_clogs, m_dev):
        m_dev.return_value = is_dev
        assert (
            project.dev_version
            == (m_clogs.return_value.current
                if is_dev
                else None))

    assert "dev_version" in project.__dict__


@pytest.mark.parametrize("github", [None, "GITHUB"])
def test_abstract_project_github(patches, github):
    kwargs = (
        dict(github=github)
        if github is not None
        else {})
    kwargs["github_token"] = MagicMock()
    project = DummyProject(**kwargs)
    patched = patches(
        "_github",
        ("AProject.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_github, m_session):
        assert (
            project.github
            == (m_github.GithubAPI.return_value
                if not github
                else github))
    if github:
        assert not m_github.GithubAPI.called
    else:
        assert (
            m_github.GithubAPI.call_args
            == [(m_session.return_value, ""),
                dict(oauth_token=kwargs["github_token"])])
    assert "github" in project.__dict__


def test_abstract_project_inventories(patches):
    project = DummyProject()
    patched = patches(
        ("AProject.inventories_class",
         dict(new_callable=PropertyMock)),
        ("AProject.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_class, m_version):
        assert (
            project.inventories
            == m_class.return_value.return_value)

    assert (
        m_class.return_value.call_args
        == [(project, ), {}])
    assert "inventories" in project.__dict__


def test_abstract_project_is_dev(patches):
    project = DummyProject()
    patched = patches(
        ("AProject.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_version, ):
        assert (
            project.is_dev
            == m_version.return_value.is_devrelease)

    assert "is_dev" not in project.__dict__


@pytest.mark.parametrize("is_dev", [True, False])
@pytest.mark.parametrize("micro", [None, 0, 1, "cabbage"])
def test_abstract_project_is_main_dev(patches, is_dev, micro):
    project = DummyProject()
    patched = patches(
        ("AProject.is_dev",
         dict(new_callable=PropertyMock)),
        ("AProject.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_dev, m_version):
        m_dev.return_value = is_dev
        m_version.return_value.micro = micro
        assert (
            project.is_main_dev
            == (is_dev and micro == 0))

    assert "is_main_dev" not in project.__dict__


def test_abstract_project_minor_version(patches):
    project = DummyProject()
    patched = patches(
        "utils",
        ("AProject.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_utils, m_version):
        assert (
            project.minor_version
            == m_utils.minor_version_for.return_value)

    assert (
        m_utils.minor_version_for.call_args
        == [(m_version.return_value, ), {}])
    assert "minor_version" in project.__dict__


def test_abstract_project_minor_versions(patches):
    project = DummyProject()
    patched = patches(
        "utils",
        ("AProject.changelogs",
         dict(new_callable=PropertyMock)),
        "AProject._patch_versions",
        prefix="envoy.base.utils.abstract.project.project")

    def version_for(version):
        return version[:2]

    changelogs = []
    minors = {}
    for minor in range(0, 5):
        key = f"M{minor}"
        minors[key] = []
        for patch in range(0, 5):
            version = f"{key}P{patch}"
            changelogs.append(version)
            minors[key].append(version)

    with patched as (m_utils, m_clogs, m_patch):
        m_clogs.return_value = changelogs
        m_utils.minor_version_for.side_effect = version_for
        assert (
            project.minor_versions
            == {k: m_patch.return_value
                for k
                in minors})

    assert (
        m_patch.call_args_list
        == [[(p, ), {}]
            for p in minors.values()])
    assert "minor_versions" in project.__dict__


def test_abstract_project_path(patches):
    project = DummyProject()
    patched = patches(
        "pathlib",
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_plib, ):
        assert (
            project.path
            == m_plib.Path.return_value)

    assert (
        m_plib.Path.call_args
        == [(".", ), {}])
    assert "path" in project.__dict__


def test_abstract_project_rel_version_path(patches):
    project = DummyProject()
    patched = patches(
        "pathlib",
        "VERSION_PATH",
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_plib, m_path):
        assert (
            project.rel_version_path
            == m_plib.Path.return_value)

    assert (
        m_plib.Path.call_args
        == [(m_path, ), {}])


@pytest.mark.parametrize("repo", [None, "REPO"])
def test_abstract_project_repo(patches, repo):
    kwargs = (
        dict(repo=repo)
        if repo is not None
        else {})
    project = DummyProject(**kwargs)
    patched = patches(
        ("AProject.github",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_github, ):
        assert (
            project.repo
            == (m_github.return_value.__getitem__.return_value
                if not repo
                else repo))
    if repo:
        assert not m_github.called
    else:
        assert (
            m_github.return_value.__getitem__.call_args
            == [(abstract.project.project.ENVOY_REPO, ), {}])
    assert "repo" in project.__dict__


@pytest.mark.parametrize("session", [None, "SESSION"])
def test_abstract_project_session(patches, session):
    kwargs = (
        dict(session=session)
        if session is not None
        else {})
    project = DummyProject(**kwargs)
    patched = patches(
        "aiohttp",
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_aiohttp, ):
        assert (
            project.session
            == (m_aiohttp.ClientSession.return_value
                if not session
                else session))
    if session:
        assert not m_aiohttp.ClientSession.called
    else:
        assert (
            m_aiohttp.ClientSession.call_args
            == [(), {}])
    assert "session" in project.__dict__


@pytest.mark.parametrize("main_dev", [True, False])
def test_abstract_project_stable_versions(patches, main_dev):
    project = DummyProject()
    patched = patches(
        "reversed",
        "sorted",
        "tuple",
        ("AProject.archived_versions",
         dict(new_callable=PropertyMock)),
        ("AProject.is_main_dev",
         dict(new_callable=PropertyMock)),
        ("AProject.minor_version",
         dict(new_callable=PropertyMock)),
        ("AProject.minor_versions",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")
    archived_versions = list(range(0, 5))
    minor_version = 7
    minor_versions = range(0, 10)

    expected = set(minor_versions) - set(archived_versions)
    if main_dev:
        expected.remove(minor_version)

    with patched as patchy:
        (m_rev, m_sort, m_tuple, m_archive,
         m_dev, m_minor, m_versions) = patchy
        m_dev.return_value = main_dev
        m_versions.return_value.keys.return_value = minor_versions
        m_minor.return_value = minor_version
        m_archive.return_value = archived_versions
        assert (
            project.stable_versions
            == m_tuple.return_value)

    assert (
        m_tuple.call_args
        == [(m_rev.return_value, ), {}])
    assert (
        m_rev.call_args
        == [(m_sort.return_value, ), {}])
    assert (
        m_sort.call_args
        == [(expected, ), {}])
    assert (
        m_versions.return_value.keys.call_args
        == [(), {}])


@pytest.mark.parametrize("version", [None, 0, "VERSION"])
def test_abstract_project_version(patches, version):
    kwargs = (
        dict(version=version)
        if version is not None
        else {})
    project = DummyProject(**kwargs)
    patched = patches(
        "_version",
        ("AProject.version_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_version, m_path):
        assert (
            project.version
            == (m_version.Version.return_value
                if version is None
                else version))

    if version is not None:
        assert not m_version.Version.called
        assert not m_path.called
    else:
        assert (
            m_version.Version.call_args
            == [((m_path.return_value.read_text
                        .return_value.strip
                        .return_value), ),
                {}])
    assert "version" in project.__dict__


def test_abstract_project_version_path(patches):
    project = DummyProject()
    patched = patches(
        ("AProject.path",
         dict(new_callable=PropertyMock)),
        ("AProject.rel_version_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_path, m_rel):
        assert (
            project.version_path
            == m_path.return_value.joinpath.return_value)

    assert (
        m_path.return_value.joinpath.call_args
        == [(m_rel.return_value, ), {}])
    assert "version_path" in project.__dict__


@pytest.mark.parametrize("version", [True, False])
def test_abstract_project_changes_for_commit(patches, version):
    project = DummyProject()
    patched = patches(
        "any",
        "sorted",
        "tuple",
        "VERSION_PATH",
        ("AProject.changelogs",
         dict(new_callable=PropertyMock)),
        ("AProject.inventories",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")
    clogs = set([f"C{i}" for i in range(0, 7)])
    inv = set([f"C{i}" for i in range(3, 10)])
    update = MagicMock()
    expected = clogs | inv

    with patched as (m_any, m_sort, m_tuple, m_path, m_clogs, m_inv):
        m_clogs.return_value.changes_for_commit.return_value = clogs
        m_inv.return_value.changes_for_commit.return_value = inv
        m_any.return_value = version
        if version:
            expected.add(m_path)
        assert (
            project.changes_for_commit(update)
            == m_tuple.return_value)
        anygen = m_any.call_args[0][0]
        anylist = list(anygen)

    assert (
        m_tuple.call_args
        == [(m_sort.return_value, ), {}])
    assert (
        m_sort.call_args
        == [(expected, ), {}])
    assert (
        m_clogs.return_value.changes_for_commit.call_args
        == [(update, ), {}])
    assert (
        m_inv.return_value.changes_for_commit.call_args
        == [(update, ), {}])
    assert isinstance(anygen, types.GeneratorType)
    assert anylist == [False, False]
    assert (
        update.__contains__.call_args_list
        == [[("dev", ), {}], [("release", ), {}]])


async def test_abstract_project_commit(patches):
    project = DummyProject()
    patched = patches(
        "AProject.changes_for_commit",
        "AProject._git_commit",
        prefix="envoy.base.utils.abstract.project.project")
    update = MagicMock()
    changes = [f"C{i}" for i in range(0, 7)]
    results = []
    msg = MagicMock()

    with patched as (m_changes, m_commit):
        m_changes.return_value = changes
        async for result in project.commit(update, msg):
            results.append(result)

    assert results == changes
    assert (
        m_changes.call_args
        == [(update, ), {}])
    assert (
        m_commit.call_args
        == [(changes, msg), {}])


@pytest.mark.parametrize("dev", [True, False])
@pytest.mark.parametrize("pending", [True, False])
@pytest.mark.parametrize("patch", [None, True, False])
async def test_abstract_project_dev(patches, dev, pending, patch):
    project = DummyProject()
    patched = patches(
        "utils",
        ("AProject.changelogs",
         dict(new_callable=PropertyMock)),
        ("AProject.is_dev",
         dict(new_callable=PropertyMock)),
        ("AProject.version",
         dict(new_callable=PropertyMock)),
        "AProject.version_string",
        "AProject.write_version",
        prefix="envoy.base.utils.abstract.project.project")
    kwargs = (
        {}
        if patch is None
        else dict(patch=patch))

    with patched as (m_utils, m_clogs, m_dev, m_version, m_str, m_write):
        m_dev.return_value = dev
        m_clogs.return_value.is_pending = pending

        if dev or pending:
            with pytest.raises(exceptions.DevError) as e:
                await project.dev(**kwargs)
        else:
            assert (
                await project.dev(**kwargs)
                == dict(
                    date="Pending",
                    version=m_str.return_value,
                    old_version=m_version.return_value))

    if dev or pending:
        assert not m_utils.increment_version.called
        assert not m_version.called
        assert not m_clogs.return_value.write_version.called
        assert not m_clogs.return_value.write_current.called
        assert not m_str.called
        assert not m_write.called
        assert (
            e.value.args[0]
            == ("Project is already set to dev"
                if dev
                else "Current changelog date is already set to `Pending`"))
        return
    assert (
        m_utils.increment_version.call_args
        == [(m_version.return_value, ), dict(patch=patch or False)])
    assert (
        m_write.call_args
        == [(m_utils.increment_version.return_value, ),
            dict(dev=True)])
    assert (
        m_clogs.return_value.write_version.call_args
        == [(m_version.return_value, ), {}])
    assert (
        m_clogs.return_value.write_current.call_args
        == [(), {}])
    assert (
        m_str.call_args
        == [(m_utils.increment_version.return_value, ),
            dict(dev=True)])


@pytest.mark.parametrize("self_version", range(0, 3))
@pytest.mark.parametrize("other_version", range(0, 3))
def test_abstract_project_is_current(patches, self_version, other_version):
    project = DummyProject()
    patched = patches(
        ("AProject.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")
    _other_version = MagicMock()
    _other_version.base_version = other_version

    with patched as (m_version, ):
        m_version.return_value.base_version = self_version
        assert (
            project.is_current(_other_version)
            == (self_version == other_version))


@pytest.mark.parametrize("is_dev", [True, False])
async def test_abstract_project_release(patches, is_dev):
    project = DummyProject()
    patched = patches(
        ("AProject.changelogs",
         dict(new_callable=PropertyMock)),
        ("AProject.datestamp",
         dict(new_callable=PropertyMock)),
        ("AProject.is_dev",
         dict(new_callable=PropertyMock)),
        ("AProject.version",
         dict(new_callable=PropertyMock)),
        "AProject.write_version",
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_clogs, m_stamp, m_dev, m_version, m_write):
        m_dev.return_value = is_dev
        if not is_dev:
            with pytest.raises(exceptions.ReleaseError) as e:
                await project.release()
        else:
            assert (
                await project.release()
                == dict(date=m_stamp.return_value,
                        version=m_version.return_value.base_version))

    if not is_dev:
        assert not m_clogs.called
        assert not m_write.called
        assert e.value.args[0] == "Project is not set to dev"
        return
    assert (
        m_clogs.return_value.write_date.call_args
        == [(m_stamp.return_value, ), {}])
    assert (
        m_write.call_args
        == [(m_version.return_value, ), {}])


async def test_abstract_project_sync(patches):
    project = DummyProject()
    patched = patches(
        "asyncio",
        ("AProject.changelogs",
         dict(new_callable=PropertyMock)),
        ("AProject.inventories",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")

    with patched as (m_aio, m_clogs, m_inv):
        gather = AsyncMock()
        m_aio.gather.side_effect = gather
        assert (
            await project.sync()
            == dict(
                changelog=gather.return_value.__getitem__.return_value,
                inventory=gather.return_value.__getitem__.return_value))

    assert (
        m_aio.gather.call_args
        == [(m_clogs.return_value.sync.return_value,
             m_inv.return_value.sync.return_value), {}])
    assert (
        m_clogs.return_value.sync.call_args
        == [(), {}])
    assert (
        m_inv.return_value.sync.call_args
        == [(), {}])
    assert (
        gather.return_value.__getitem__.call_args_list
        == [[(0, ), {}], [(1, ), {}]])


@pytest.mark.parametrize("dev", [None, True, False])
def test_abstract_project_version_string(dev):
    project = DummyProject()
    kwargs = (
        dict(dev=dev)
        if dev is not None
        else {})
    dev_str = "-dev" if dev else ""
    version = MagicMock()
    assert (
        project.version_string(version, **kwargs)
        == f"{version.base_version}{dev_str}")


@pytest.mark.parametrize("dev", [True, False])
def test_abstract_project_write_version(patches, dev):
    project = DummyProject()
    patched = patches(
        ("AProject.version_path",
         dict(new_callable=PropertyMock)),
        "AProject.version_string",
        prefix="envoy.base.utils.abstract.project.project")
    kwargs = (
        dict(dev=dev)
        if dev
        else {})
    version = MagicMock()

    with patched as (m_path, m_string):
        assert not project.write_version(version, **kwargs)

    assert (
        m_path.return_value.write_text.call_args
        == [(f"{m_string.return_value}\n", ), {}])
    assert (
        m_string.call_args
        == [(version, ),
            dict(dev=dev)])


async def test_abstract_project__git_commit(patches):
    project = DummyProject()
    patched = patches(
        "AProject._exec",
        prefix="envoy.base.utils.abstract.project.project")
    changed = tuple(f"C{i}" for i in range(0, 5))
    msg = MagicMock()

    with patched as (m_exec, ):
        assert not await project._git_commit(changed, msg)

    assert (
        m_exec.call_args_list
        == [[(" ".join(["git", "add", *changed]), ),
             {}],
            [(" ".join(["git", "commit", *changed, "-m", f"'{msg}'"]), ),
             {}]])


@pytest.mark.parametrize("returns", [None, 0, 23, "cabbage"])
async def test_abstract_project__exec(patches, returns):
    project = DummyProject()
    patched = patches(
        "asyncio",
        ("AProject.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.project")
    command = MagicMock()

    with patched as (m_aio, m_path):
        shell = AsyncMock()
        comm = AsyncMock()
        stdout = MagicMock()
        stdout.decode.return_value = "STDOUT"
        stderr = MagicMock()
        stderr.decode.return_value = "STDERR"
        comm.return_value = [stdout, stderr]
        shell.return_value.communicate = comm
        shell.return_value.returncode = returns
        m_aio.subprocess.create_subprocess_shell = shell
        if returns != 0:
            with pytest.raises(exceptions.CommitError) as e:
                await project._exec(command)
        else:
            assert not await project._exec(command)

    assert (
        shell.call_args
        == [(command, ),
            dict(stdout=m_aio.subprocess.PIPE,
                 stderr=m_aio.subprocess.PIPE,
                 cwd=m_path.return_value)])
    assert (
        comm.call_args
        == [(), {}])
    if returns == 0:
        assert not stdout.decode.called
        assert not stderr.decode.called
        return
    assert e.value.args[0] == 'STDOUT\nSTDERR'
    assert (
        stdout.decode.call_args
        == [("utf-8", ), {}])
    assert (
        stderr.decode.call_args
        == [("utf-8", ), {}])


@pytest.mark.parametrize("is_dev", [True, False])
def test_abstract_project__patch_versions(patches, is_dev):
    project = DummyProject()
    patched = patches(
        "reversed",
        "sorted",
        "tuple",
        ("AProject.is_dev",
         dict(new_callable=PropertyMock)),
        "AProject.is_current",
        prefix="envoy.base.utils.abstract.project.project")
    current_version = 7
    versions = range(0, 10)

    with patched as (m_rev, m_sort, m_tuple, m_dev, m_current):
        m_dev.return_value = is_dev
        m_current.side_effect = lambda x: x == current_version
        assert (
            project._patch_versions(versions)
            == m_tuple.return_value)
        to_sort = m_sort.call_args[0][0]
        result = list(to_sort)

    assert (
        m_tuple.call_args
        == [(m_rev.return_value, ), {}])
    assert (
        m_rev.call_args
        == [(m_sort.return_value, ), {}])
    assert (
        m_sort.call_args
        == [(to_sort, ), {}])
    if is_dev:
        assert isinstance(to_sort, types.GeneratorType)
        assert (
            result
            == [x for x in versions if x != current_version])
    else:
        assert to_sort is versions
