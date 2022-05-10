
import json
import pathlib
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import yaml

import abstracts

from envoy.base.utils import abstract, exceptions, interface, typing


@abstracts.implementer(interface.IChangelogs)
class DummyChangelogs(abstract.AChangelogs):

    @property
    def changelog_class(self):
        return super().changelog_class


def test_abstract_changelogs_constructor():

    with pytest.raises(TypeError):
        abstract.AChangelogs("PROJECT")

    changelogs = DummyChangelogs("PROJECT")
    assert changelogs.project == "PROJECT"

    with pytest.raises(NotImplementedError):
        changelogs.changelog_class


def test_abstract_changelogs_dunder_contains(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.changelogs",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_clogs, ):
        assert (
            changelogs.__contains__("KEY")
            == m_clogs.return_value.__contains__.return_value)

    assert (
        m_clogs.return_value.__contains__.call_args
        == [("KEY",), {}])


def test_abstract_changelogs_dunder_getitem(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.changelogs",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_clogs, ):
        assert (
            changelogs.__getitem__("KEY")
            == m_clogs.return_value.__getitem__.return_value)

    assert (
        m_clogs.return_value.__getitem__.call_args
        == [("KEY",), {}])


def test_abstract_changelogs_dunder_iter(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.changelogs",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    clogs = [f"CLOG{c}" for c in range(0, 5)]

    with patched as (m_clogs, ):
        m_clogs.return_value = clogs
        result = changelogs.__iter__()
        assert isinstance(result, types.GeneratorType)
        assert (
            list(result)
            == clogs)


def test_abstract_changelogs_changelog_paths(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.paths",
         dict(new_callable=PropertyMock)),
        "AChangelogs._version_from_path",
        prefix="envoy.base.utils.abstract.project.changelog")
    paths = [f"P{p}" for p in range(0, 5)]

    with patched as (m_paths, m_version):
        m_paths.return_value = paths
        m_version.side_effect = lambda x: f"P{x}"
        assert (
            changelogs.changelog_paths
            == {f"P{p}": p
                for p in paths})

    assert (
        m_version.call_args_list
        == [[(p, ), {}] for p in paths])
    assert "changelog_paths" in changelogs.__dict__


def test_abstract_changelogs_changelogs(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "reversed",
        "sorted",
        ("AChangelogs.changelog_class",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.changelog_paths",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    paths = [f"P{p}" for p in range(0, 5)]

    with patched as (m_rev, m_sort, m_class, m_paths):
        m_rev.return_value = paths
        assert (
            changelogs.changelogs
            == {p: m_class.return_value.return_value
                for p in paths})

    assert (
        m_class.return_value.call_args_list
        == [[(p, m_paths.return_value.__getitem__.return_value), {}]
            for p in paths])
    assert (
        m_paths.return_value.__getitem__.call_args_list
        == [[(p, ), {}]
            for p in paths])
    assert (
        m_rev.call_args
        == [(m_sort.return_value, ), {}])
    assert (
        m_sort.call_args
        == [(m_paths.return_value.keys.return_value, ), {}])
    assert (
        m_paths.return_value.keys.call_args
        == [(), {}])
    assert "changelogs" in changelogs.__dict__


def test_abstract_changelogs_current(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "next",
        "iter",
        ("AChangelogs.changelogs",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_next, m_iter, m_clogs):
        assert (
            changelogs.current
            == m_next.return_value)

    assert (
        m_next.call_args
        == [(m_iter.return_value, ), {}])
    assert (
        m_iter.call_args
        == [(m_clogs.return_value, ), {}])
    assert "current" in changelogs.__dict__


def test_abstract_changelogs_current_path():
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    assert (
        changelogs.current_path
        == project.path.joinpath.return_value)
    assert (
        project.path.joinpath.call_args
        == [(abstract.project.changelog.CHANGELOG_CURRENT_PATH, ),
            {}])
    assert "current_path" not in changelogs.__dict__


def test_abstract_changelogs_current_tpl(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "jinja2",
        "CHANGELOG_CURRENT_TPL",
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_jinja, m_tpl):
        assert (
            changelogs.current_tpl
            == m_jinja.Template.return_value)

    assert (
        m_jinja.Template.call_args
        == [(m_tpl, ), {}])


@pytest.mark.parametrize("pending", [None, "Pending", "cabbage"])
def test_abstract_changelogs_is_pending(patches, pending):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "AChangelogs.__getitem__",
        ("AChangelogs.current",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_get, m_current):
        m_get.return_value.release_date = pending
        assert (
            changelogs.is_pending
            == (pending == "Pending"))

    assert (
        m_get.call_args
        == [(m_current.return_value, ), {}])
    assert "is_pending" not in changelogs.__dict__


def test_abstract_changelogs_paths(patches):
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    patched = patches(
        ("AChangelogs.current_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    paths = [f"P{p}" for p in range(0, 5)]
    project.path.glob.return_value = paths

    with patched as (m_path, ):
        assert (
            changelogs.paths
            == (*paths, m_path.return_value))
    assert (
        project.path.glob.call_args
        == [(abstract.project.changelog.CHANGELOG_PATH_GLOB, ), {}])
    assert "paths" not in changelogs.__dict__


@pytest.mark.parametrize(
    "raises",
    [None, Exception, yaml.reader.ReaderError, exceptions.TypeCastingError])
def test_abstract_changelogs_sections(patches, raises):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "utils.from_yaml",
        ("AChangelogs.sections_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_yaml, m_path):
        if raises:
            error = raises("AN ERROR OCCURRED", 7, 23, "Y", "Z")
            m_yaml.side_effect = error
        if raises == Exception:
            with pytest.raises(Exception):
                changelogs.sections
        elif raises:
            with pytest.raises(exceptions.ChangelogError) as e:
                changelogs.sections
        else:
            assert (
                changelogs.sections
                == m_yaml.return_value)

    assert (
        m_yaml.call_args
        == [(m_path.return_value, typing.ChangelogSectionsDict), {}])
    assert (
        ("sections" in changelogs.__dict__)
        == (not raises))
    if not raises or raises == Exception:
        return
    assert (
        e.value.args[0]
        == ("Failed to parse changelog sections "
            f"({m_path.return_value}): {str(error)}"))


def test_abstract_changelogs_sections_path():
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    assert (
        changelogs.sections_path
        == project.path.joinpath.return_value)
    assert (
        project.path.joinpath.call_args
        == [(abstract.project.changelog.CHANGELOG_SECTIONS_PATH, ), {}])
    assert "sections_path" not in changelogs.__dict__


def test_abstract_changelogs_section_re(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "re",
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_re, ):
        assert (
            changelogs.section_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [(r"\n[a-z_]*:", ), {}])
    assert "section_re" in changelogs.__dict__


def test_abstract_changelogs_yaml(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "_yaml",
        "typing",
        "AChangelogs.yaml_change_presenter",
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_yaml, m_typing, m_pres):
        assert (
            changelogs.yaml
            == m_yaml)

    assert (
        m_yaml.add_representer.call_args
        == [(m_typing.Change,
             m_pres),
            {}])
    assert "yaml" in changelogs.__dict__


def test_abstract_changelogs_changelog_path(patches):
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    patched = patches(
        "AChangelogs.rel_changelog_path",
        prefix="envoy.base.utils.abstract.project.changelog")
    version = MagicMock()

    with patched as (m_path, ):
        assert (
            changelogs.changelog_path(version)
            == project.path.joinpath.return_value)

    assert (
        project.path.joinpath.call_args
        == [(m_path.return_value, ), {}])
    assert (
        m_path.call_args
        == [(version, ), {}])


@pytest.mark.parametrize("is_rst", [True, False])
def test_abstract_changelogs_changelog_url(patches, is_rst):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "CHANGELOG_URL_TPL",
        "RST_CHANGELOG_URL_TPL",
        "AChangelogs._is_rst_changelog",
        prefix="envoy.base.utils.abstract.project.changelog")
    version = MagicMock()

    with patched as (m_tpl, m_rst_tpl, m_is_rst):
        m_is_rst.return_value = is_rst
        tpl = (
            m_tpl
            if not is_rst
            else m_rst_tpl)
        not_tpl = (
            m_tpl
            if is_rst
            else m_rst_tpl)
        assert (
            changelogs.changelog_url(version)
            == tpl.format.return_value)

    assert (
        tpl.format.call_args
        == [(), dict(version=version.base_version)])
    assert not not_tpl.called


@pytest.mark.parametrize("current", [True, False])
@pytest.mark.parametrize("dev", [True, False])
@pytest.mark.parametrize(
    "items",
    [{},
     {i: True for i in range(0, 10)},
     {i: False for i in range(0, 10)},
     {i: (i % 2) for i in range(0, 10)}])
def test_abstract_changelogs_changes_for_commit(patches, current, dev, items):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "any",
        "set",
        "CHANGELOG_CURRENT_PATH",
        "AChangelogs.rel_changelog_path",
        prefix="envoy.base.utils.abstract.project.changelog")
    change = MagicMock()
    change.get.return_value.get.return_value = items

    def contains(k):
        if k == "dev":
            return dev
        return True

    change.__contains__.side_effect = contains

    with patched as (m_any, m_set, m_path, m_rel):
        m_any.return_value = current
        assert (
            changelogs.changes_for_commit(change)
            == m_set.return_value)
        anygen = m_any.call_args[0][0]
        anylist = list(anygen)

    assert isinstance(anygen, types.GeneratorType)
    assert anylist == [True, dev]
    expected_add = []
    expected_rel = []
    if current:
        expected_add.append(m_path)
    if dev:
        expected_add.append(m_rel.return_value)
        expected_rel.append(
            change.__getitem__.return_value.__getitem__.return_value)
        assert (
            change.__getitem__.call_args
            == [("dev", ), {}])
        assert (
            change.__getitem__.return_value.__getitem__.call_args
            == [("old_version", ), {}])
    assert (
        change.get.call_args
        == [("sync", {}), {}])
    assert (
        change.get.return_value.get.call_args
        == [("changelog", {}), {}])
    for k, v in items.items():
        if v:
            expected_add.append(m_rel.return_value)
            expected_rel.append(k)
    assert (
        m_set.return_value.add.call_args_list
        == [[(add, ), {}]
            for add in expected_add])
    assert (
        m_rel.call_args_list
        == [[(p, ), {}]
            for p in expected_rel])


def test_abstract_changelogs_dump_yaml(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.section_re",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.yaml",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    data = MagicMock()
    sections = [f"S{s}" for s in range(0, 3)]

    with patched as (m_re, m_yaml):
        m_re.return_value.findall.return_value = sections
        output = (
            m_yaml.return_value.dump
                  .return_value.replace
                  .return_value.replace
                  .return_value.replace.return_value)
        assert (
            changelogs.dump_yaml(data)
            == f"{output}\n")

    assert (
        m_yaml.return_value.dump.call_args
        == [(data, ),
            dict(default_flow_style=False,
                 default_style=None,
                 sort_keys=False)])
    assert (
        (m_yaml.return_value.dump.return_value
                            .replace.call_args)
        == [("S0", "\nS0"), {}])
    assert (
        (m_yaml.return_value.dump.return_value
                            .replace.return_value
                            .replace.call_args)
        == [("S1", "\nS1"), {}])
    assert (
        (m_yaml.return_value.dump.return_value
                            .replace.return_value
                            .replace.return_value
                            .replace.call_args)
        == [("S2", "\nS2"), {}])


async def test_abstract_changelogs_fetch(patches):
    project = MagicMock()
    project.session.get = AsyncMock()
    project.session.get.return_value.text = AsyncMock()
    changelogs = DummyChangelogs(project)
    patched = patches(
        "AChangelogs.changelog_url",
        prefix="envoy.base.utils.abstract.project.changelog")
    version = MagicMock()

    with patched as (m_url, ):
        assert (
            await changelogs.fetch(version)
            == project.session.get.return_value.text.return_value)

    assert (
        project.session.get.call_args
        == [(m_url.return_value, ), {}])
    assert (
        m_url.call_args
        == [(version, ), {}])
    assert (
        project.session.get.return_value.text.call_args
        == [(), {}])


@pytest.mark.parametrize("is_rst", [True, False])
def test_abstract_changelogs_normalize_changelog(patches, is_rst):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "LegacyChangelog",
        "AChangelogs.dump_yaml",
        "AChangelogs._is_rst_changelog",
        prefix="envoy.base.utils.abstract.project.changelog")
    version = MagicMock()
    changelog = MagicMock()

    with patched as (m_legacy, m_dump, m_is_rst):
        m_is_rst.return_value = is_rst
        assert (
            changelogs.normalize_changelog(version, changelog)
            == (changelog
                if not is_rst
                else m_dump.return_value))

    assert (
        m_is_rst.call_args
        == [(version, ), {}])
    if not is_rst:
        assert not m_dump.called
        return
    assert (
        m_dump.call_args
        == [(m_legacy.return_value.data, ), {}])
    assert (
        m_legacy.call_args
        == [(changelog, ), {}])


def test_abstract_changelogs_rel_changelog_path(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "CHANGELOG_PATH_FMT",
        prefix="envoy.base.utils.abstract.project.changelog")
    version = MagicMock()

    with patched as (m_fmt, ):
        assert (
            changelogs.rel_changelog_path(version)
            == m_fmt.format.return_value)

    assert (
        m_fmt.format.call_args
        == [(), dict(version=version.base_version)])


@pytest.mark.parametrize("version", range(0, 5))
@pytest.mark.parametrize("project_version", range(0, 5))
@pytest.mark.parametrize("first_stable", range(0, 5))
@pytest.mark.parametrize("exists", [True, False])
def test_abstract_changelogs_should_sync(
        patches, version, project_version, first_stable, exists):
    project = MagicMock()
    project.version = project_version
    project.stable_versions.__getitem__.return_value = first_stable
    changelogs = DummyChangelogs(project)
    patched = patches(
        "AChangelogs.__contains__",
        prefix="envoy.base.utils.abstract.project.changelog")
    should = True
    if project_version <= version:
        should = False
    if version < first_stable:
        should = False
    if exists:
        should = False

    with patched as (m_contains, ):
        m_contains.return_value = exists
        assert (
            changelogs.should_sync(version)
            == should)

    if version < project_version:
        assert (
            project.stable_versions.__getitem__.call_args
            == [(-1, ), {}])
    else:
        assert not project.stable_versions.__getitem__.called
        assert not m_contains.called
        return
    if version >= first_stable:
        assert (
            m_contains.call_args
            == [(version, ), {}])
    else:
        assert not m_contains.called


async def test_abstract_changelogs_sync(patches):
    releases = []
    for i in range(0, 10):
        release = MagicMock()
        release.version = i
        releases.append(release)

    async def repo_releases():
        for release in releases:
            yield release

    project = MagicMock()
    project.repo.releases.side_effect = repo_releases
    changelogs = DummyChangelogs(project)
    patched = patches(
        "AChangelogs.fetch",
        "AChangelogs.should_sync",
        "AChangelogs.write_changelog",
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_fetch, m_should, m_write):
        m_should.side_effect = lambda x: x % 2
        assert (
            await changelogs.sync()
            == {release.version: True
                for release
                in releases
                if release.version % 2})

    assert (
        m_should.call_args_list
        == [[(release.version, ), {}]
            for release
            in releases])
    assert (
        m_write.call_args_list
        == [[(release.version, m_fetch.return_value), {}]
            for release
            in releases
            if release.version % 2])
    assert (
        m_fetch.call_args_list
        == [[(release.version, ), {}]
            for release
            in releases
            if release.version % 2])


def test_abstract_changelogs_write_changelog(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "AChangelogs.changelog_path",
        "AChangelogs.normalize_changelog",
        prefix="envoy.base.utils.abstract.project.changelog")
    version = MagicMock()
    text = MagicMock()

    with patched as (m_path, m_norm):
        assert not changelogs.write_changelog(version, text)

    assert (
        m_path.call_args
        == [(version, ), {}])
    assert (
        m_path.return_value.write_text.call_args
        == [(m_norm.return_value, ), {}])
    assert (
        m_norm.call_args
        == [(version, text), {}])


def test_abstract_changelogs_write_current(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.current_path",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_tpl",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.sections",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    sections = {f"K{s}": MagicMock() for s in range(0, 10)}
    sections["changes"] = MagicMock()

    with patched as (m_path, m_tpl, m_sections):
        m_sections.return_value.items.return_value = sections.items()
        assert not changelogs.write_current()

    assert (
        m_path.return_value.write_text.call_args
        == [(m_tpl.return_value.render.return_value.lstrip.return_value, ),
            {}])
    assert (
        m_tpl.return_value.render.call_args
        == [(),
            dict(sections={
                k: v.get.return_value
                for k, v
                in sections.items()
                if k != "changes"})])
    assert (
        m_tpl.return_value.render.return_value.lstrip.call_args
        == [(), {}])
    for k, v in sections.items():
        if k == "changes":
            assert not v.get.called
        else:
            assert (
                v.get.call_args
                == [("description", ), {}])


@pytest.mark.parametrize("pending", [True, False])
def test_abstract_changelogs_write_date(patches, pending):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "AChangelogs.__getitem__",
        ("AChangelogs.current",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_path",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.is_pending",
         dict(new_callable=PropertyMock)),
        "AChangelogs.dump_yaml",
        prefix="envoy.base.utils.abstract.project.changelog")
    date = MagicMock()

    with patched as (m_get, m_current, m_path, m_pending, m_yaml):
        m_pending.return_value = pending
        if not pending:
            with pytest.raises(exceptions.ReleaseError) as e:
                changelogs.write_date(date)
        else:
            assert not changelogs.write_date(date)

    if not pending:
        assert (
            e.value.args[0]
            == "Current changelog date is not set to `Pending`")
        assert not m_current.called
        assert not m_get.called
        assert not m_path.called
        assert not m_yaml.called
        return

    assert (
        m_get.call_args
        == [(m_current.return_value, ), {}])
    assert (
        m_get.return_value.data.copy.call_args
        == [(), {}])
    assert (
        m_path.return_value.write_text.call_args
        == [(m_yaml.return_value, ), {}])
    assert (
        m_yaml.call_args
        == [(m_get.return_value.data.copy.return_value, ), {}])


@pytest.mark.parametrize("exists", [True, False])
def test_abstract_changelogs_write_version(patches, exists):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.current_path",
         dict(new_callable=PropertyMock)),
        "AChangelogs.changelog_path",
        prefix="envoy.base.utils.abstract.project.changelog")
    version = MagicMock()

    with patched as (m_path, m_clog_path):
        m_clog_path.return_value.exists.return_value = exists
        if exists:
            with pytest.raises(exceptions.DevError) as e:
                changelogs.write_version(version)
        else:
            assert not changelogs.write_version(version)

    assert (
        m_clog_path.call_args
        == [(version, ), {}])
    assert (
        m_clog_path.return_value.exists.call_args
        == [(), {}])
    if exists:
        assert (
            e.value.args[0]
            == f"Version file ({m_clog_path.return_value}) already exists")
        assert not m_clog_path.return_value.write_text.called
        assert not m_path.called
        return
    assert (
        m_clog_path.return_value.write_text.call_args
        == [(m_path.return_value.read_text.return_value, ), {}])
    assert (
        m_path.return_value.read_text.call_args
        == [(), {}])


def test_abstract_changelogs_yaml_change_presenter():
    changelogs = DummyChangelogs("PROJECT")
    dumper = MagicMock()
    data = MagicMock()
    assert (
        changelogs.yaml_change_presenter(dumper, data)
        == dumper.represent_scalar.return_value)
    assert (
        dumper.represent_scalar.call_args
        == [('tag:yaml.org,2002:str', data),
            dict(style="|")])


@pytest.mark.parametrize("method", ["keys", "items", "values"])
def test_abstract_changelogs_changelogs_methods(patches, method):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.changelogs",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_clogs, ):
        assert (
            getattr(changelogs, method)()
            == getattr(m_clogs.return_value, method).return_value)

    assert (
        getattr(m_clogs.return_value, method).call_args
        == [(), {}])


def test_abstract_changelogs__yaml_changelogs_version(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "YAML_CHANGELOGS_VERSION",
        "_version",
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_clogs, m_version):
        assert (
            changelogs._yaml_changelogs_version
            == m_version.Version.return_value)

    assert (
        m_version.Version.call_args
        == [(m_clogs, ), {}])
    assert "_yaml_changelogs_version" in changelogs.__dict__


@pytest.mark.parametrize("clogs_version", range(0, 5))
@pytest.mark.parametrize("version", range(0, 5))
def test_abstract_changelogs__is_rst_changelog(
        patches, clogs_version, version):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs._yaml_changelogs_version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_version, ):
        m_version.return_value = clogs_version
        assert (
            changelogs._is_rst_changelog(version)
            == (version < clogs_version))


@pytest.mark.parametrize("stem", ["curent", "NOTCURRENT"])
def test_abstract_changelogs__version_from_path(patches, stem):
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    patched = patches(
        "_version",
        prefix="envoy.base.utils.abstract.project.changelog")
    path = MagicMock()
    path.stem = stem

    with patched as (m_version, ):
        assert (
            changelogs._version_from_path(path)
            == m_version.Version.return_value)

    assert (
        m_version.Version.call_args
        == [(stem
             if stem != "current"
             else project.version.base_version, ),
            {}])


@abstracts.implementer(interface.IChangelog)
class DummyChangelog(abstract.AChangelog):

    @property
    def entry_class(self):
        return super().entry_class


def test_abstract_changelog_constructor():

    with pytest.raises(TypeError):
        abstract.AChangelog("VERSION", "PATH")

    changelog = DummyChangelog("VERSION", "PATH")
    assert changelog._version == "VERSION"
    assert changelog.path == "PATH"

    with pytest.raises(NotImplementedError):
        changelog.entry_class


@pytest.mark.parametrize(
    "raises",
    [None, Exception, yaml.reader.ReaderError, exceptions.TypeCastingError])
def test_abstract_changelog_data(patches, raises):
    changelog = DummyChangelog("VERSION", "PATH")
    patched = patches(
        "utils.from_yaml",
        "utils.typed",
        "typing",
        prefix="envoy.base.utils.abstract.project.changelog")

    changes = {f"K{c}": c for c in range(0, 10)}
    for k, v in changes.items():
        if v % 2:
            changes[k] = [MagicMock() for i in range(0, 7)]
        else:
            changes[k] = None
    changes["date"] = "NOTCHANGE"

    with patched as (m_yaml, m_typed, m_typing):
        m_yaml.return_value.items.return_value = changes.items()
        if raises:
            error = raises("AN ERROR OCCURRED", 7, 23, "Y", "Z")
            m_yaml.side_effect = error
        if raises == Exception:
            with pytest.raises(Exception):
                changelog.data
        elif raises:
            with pytest.raises(exceptions.ChangelogError) as e:
                changelog.data
        else:
            assert (
                changelog.data
                == m_typed.return_value)

    assert (
        m_yaml.call_args
        == [("PATH", m_typing.ChangelogSourceDict), {}])
    if raises == Exception:
        return
    elif raises:
        assert (
            e.value.args[0]
            == ("Failed to parse changelog "
                f"(PATH): {str(error)}"))
        return

    expected = {
        k: (v
            if k == "date"
            else [dict(area=c.__getitem__.return_value,
                       change=m_typing.Change.return_value)
                  for c
                  in v])
        for k, v
        in changes.items()
        if v}
    assert (
        m_typed.call_args
        == [(m_typing.ChangelogDict, expected), {}])
    assert "data" in changelog.__dict__


def test_abstract_changelog_release_date(patches):
    changelog = DummyChangelog("VERSION", "PATH")
    patched = patches(
        ("AChangelog.data",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_data, ):
        assert (
            changelog.release_date
            == m_data.return_value.__getitem__.return_value)

    assert (
        m_data.return_value.__getitem__.call_args
        == [("date", ), {}])
    assert "release_date" not in changelog.__dict__


def test_abstract_changelog_version():
    version = MagicMock()
    changelog = DummyChangelog(version, "PATH")
    assert (
        changelog.version
        == version.base_version)
    assert "version" not in changelog.__dict__


def test_abstract_changelog_entries(patches):
    changelog = DummyChangelog("VERSION", "PATH")
    patched = patches(
        "sorted",
        ("AChangelog.data",
         dict(new_callable=PropertyMock)),
        ("AChangelog.entry_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    entries = [f"E{e}" for e in range(0, 5)]

    with patched as (m_sort, m_data, m_entry):
        m_data.return_value.__getitem__.return_value = entries
        assert (
            changelog.entries("SECTION")
            == m_sort.return_value)
        result = m_sort.call_args[0][0]
        assert isinstance(result, types.GeneratorType)
        assert (
            list(result)
            == [m_entry.return_value.return_value
                for e
                in entries])

    assert (
        m_entry.return_value.call_args_list
        == [[("SECTION", e), {}] for e in entries])
    assert (
        m_data.return_value.__getitem__.call_args
        == [("SECTION", ), {}])


@abstracts.implementer(interface.IChangelogEntry)
class DummyChangelogEntry(abstract.AChangelogEntry):
    pass


def test_abstract_changelogentry_constructor():
    changelogentry = DummyChangelogEntry("SECTION", "ENTRY")
    assert changelogentry.section == "SECTION"
    assert changelogentry.entry == "ENTRY"


@pytest.mark.parametrize("prop", ["area", "change"])
def test_abstract_changelogentry_props(prop):
    entry = MagicMock()
    changelogentry = DummyChangelogEntry("SECTION", entry)
    assert (
        getattr(changelogentry, prop)
        == entry.__getitem__.return_value)
    assert (
        entry.__getitem__.call_args
        == [(prop, ), {}])
    assert prop not in changelogentry.__dict__


@pytest.mark.parametrize("area", range(0, 3))
@pytest.mark.parametrize("change", range(0, 3))
@pytest.mark.parametrize("other_area", range(0, 3))
@pytest.mark.parametrize("other_change", range(0, 3))
def test_abstract_changelogentry_dunder_gt(
        patches, area, change, other_area, other_change):
    changelogentry = DummyChangelogEntry("SECTION", "ENTRY")
    patched = patches(
        ("AChangelogEntry.area",
         dict(new_callable=PropertyMock)),
        ("AChangelogEntry.change",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    other_entry = MagicMock()
    other_entry.area = other_area
    other_entry.change = other_change
    expected = (
        (area > other_area)
        or (change > other_change))

    with patched as (m_area, m_change):
        m_area.return_value = area
        m_change.return_value = change
        assert (
            changelogentry.__gt__(other_entry)
            == expected)


@pytest.mark.parametrize("gt", [True, False])
def test_abstract_changelogentry_dunder_lt(patches, gt):
    changelogentry = DummyChangelogEntry("SECTION", "ENTRY")
    patched = patches(
        "AChangelogEntry.__gt__",
        prefix="envoy.base.utils.abstract.project.changelog")
    other_entry = MagicMock()

    with patched as (m_gt, ):
        m_gt.return_value = gt
        assert (
            changelogentry.__lt__(other_entry)
            == (not gt))

    assert (
        m_gt.call_args
        == [(other_entry, ), {}])


def test_legacy_changelog_constructor():
    legacy = abstract.project.changelog.LegacyChangelog("CONTENT")
    assert legacy.content == "CONTENT"


@pytest.mark.parametrize(
    "changelog",
    [("source1.rst", "result1.json"),
     ("source2.rst", "result2.json")])
def test_legacy_changelog_changelog(changelog):
    source, result = changelog
    cwd = pathlib.Path(__file__).parent
    source = cwd.joinpath(
        f"integration/changelogs/source/{source}").read_text()
    result = json.loads(
        cwd.joinpath(f"integration/changelogs/result/{result}").read_text())
    legacy_changelog = abstract.project.changelog.LegacyChangelog(
        source).changelog
    assert legacy_changelog == result
    for k, group in legacy_changelog.items():
        for log in group:
            assert isinstance(log["change"], typing.Change)


def test_legacy_changelog_data(patches):
    legacy = abstract.project.changelog.LegacyChangelog("CONTENT")
    patched = patches(
        "dict",
        "utils",
        "typing",
        ("LegacyChangelog.changelog",
         dict(new_callable=PropertyMock)),
        ("LegacyChangelog.date",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    clog = {f"K{c}": c for c in range(0, 10)}

    with patched as (m_dict, m_utils, m_typing, m_clog, m_date):
        m_clog.return_value = clog
        assert (
            legacy.data
            == m_utils.typed.return_value)

    assert (
        m_utils.typed.call_args
        == [(m_typing.ChangelogDict, m_dict.return_value), {}])
    assert (
        m_dict.call_args
        == [(),
            dict(date=m_date.return_value,
                 **clog)])
    assert "data" not in legacy.__dict__


def test_legacy_changelog_date(patches):
    legacy = abstract.project.changelog.LegacyChangelog("CONTENT")
    patched = patches(
        ("LegacyChangelog.lines",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_lines, ):
        assert (
            legacy.date
            == (m_lines.return_value.__getitem__
                       .return_value.split
                       .return_value.__getitem__
                       .return_value.strip
                       .return_value))

    assert (
        m_lines.return_value.__getitem__.call_args
        == [(0, ), {}])
    assert (
        m_lines.return_value.__getitem__.return_value.split.call_args
        == [("(", ), {}])
    assert (
        (m_lines.return_value.__getitem__
                .return_value.split
                .return_value.__getitem__.call_args)
        == [(1, ), {}])
    assert (
        (m_lines.return_value.__getitem__
                .return_value.split
                .return_value.__getitem__
                .return_value.strip.call_args)
        == [(")", ), {}])
    assert "date" not in legacy.__dict__


def test_legacy_changelog_lines():
    content = MagicMock()
    legacy = abstract.project.changelog.LegacyChangelog(content)
    assert (
        legacy.lines
        == content.split.return_value)
    assert (
        content.split.call_args
        == [("\n", ), {}])
    assert "lines" in legacy.__dict__


def test_legacy_changelog__parse_line(patches):
    legacy = abstract.project.changelog.LegacyChangelog("CONTENT")
    patched = patches(
        "dict",
        "typing",
        prefix="envoy.base.utils.abstract.project.changelog")
    line = MagicMock()
    area = MagicMock()
    change = MagicMock()
    line.__getitem__.return_value.split.return_value = [area, change]

    with patched as (m_dict, m_typing):
        assert (
            legacy._parse_line(line)
            == m_dict.return_value)

    assert (
        line.__getitem__.call_args
        == [(slice(2, None), ), {}])
    assert (
        line.__getitem__.return_value.split.call_args
        == [(":", 1), {}])
    assert (
        m_dict.call_args
        == [(), dict(area=area, change=m_typing.Change.return_value)])
    assert (
        m_typing.Change.call_args
        == [(change.lstrip.return_value, ), {}])
    assert (
        change.lstrip.call_args
        == [(" ", ), {}])
