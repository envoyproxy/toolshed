
from aio.core import directory

from envoy.base import utils


def test_project_constructor(patches):
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}
    patched = patches(
        "abstract.AProject.__init__",
        prefix="envoy.base.utils.project")

    with patched as (m_super, ):
        m_super.return_value = None
        project = utils.Project(*args, **kwargs)

    assert isinstance(project, utils.Project)
    assert isinstance(project, utils.interface.IProject)
    assert (
        m_super.call_args
        == [args, kwargs])
    assert project.changelogs_class == utils.project.Changelogs
    assert project.directory_class == directory.GitDirectory
    assert project.inventories_class == utils.project.Inventories


def test_changelogs_constructor(patches):
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}
    patched = patches(
        "abstract.AChangelogs.__init__",
        prefix="envoy.base.utils.project")

    with patched as (m_super, ):
        m_super.return_value = None
        changelogs = utils.Changelogs(*args, **kwargs)

    assert isinstance(changelogs, utils.interface.IChangelogs)
    assert (
        m_super.call_args
        == [args, kwargs])
    assert changelogs.changelog_class == utils.project.Changelog


def test_changelog_constructor(patches):
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}
    patched = patches(
        "abstract.AChangelog.__init__",
        prefix="envoy.base.utils.project")

    with patched as (m_super, ):
        m_super.return_value = None
        changelog = utils.Changelog(*args, **kwargs)

    assert isinstance(changelog, utils.interface.IChangelog)
    assert (
        m_super.call_args
        == [args, kwargs])
    assert changelog.entry_class == utils.project.ChangelogEntry


def test_changelog_entry_constructor(patches):
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}
    patched = patches(
        "abstract.AChangelogEntry.__init__",
        prefix="envoy.base.utils.project")

    with patched as (m_super, ):
        m_super.return_value = None
        changelog_entry = utils.ChangelogEntry(*args, **kwargs)

    assert isinstance(changelog_entry, utils.interface.IChangelogEntry)
    assert (
        m_super.call_args
        == [args, kwargs])
