
import json
import pathlib
import types
from datetime import datetime, timezone
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
    assert (
        changelogs.date_format
        == abstract.project.changelog.DATE_FORMAT)
    assert "date_format" not in changelogs.__dict__

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


def test_abstract_changelogs_dunder_iter(iters, patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.changelogs",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    clogs = iters()

    with patched as (m_clogs, ):
        m_clogs.return_value = clogs
        result = changelogs.__iter__()
        assert isinstance(result, types.GeneratorType)
        assert (
            list(result)
            == clogs)


@pytest.mark.parametrize("entries_layout", [True, False])
def test_abstract_changelogs_changelog_paths(iters, patches, entries_layout):
    project = MagicMock()
    project.version.base_version = "1.2.3"
    changelogs = DummyChangelogs(project)
    patched = patches(
        ("AChangelogs.entries_layout",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_dir_path",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.paths",
         dict(new_callable=PropertyMock)),
        "AChangelogs._version_from_path",
        prefix="envoy.base.utils.abstract.project.changelog")
    paths = iters(cb=lambda x: f"P{x}")

    with patched as (m_entries, m_current_dir_path, m_paths, m_version):
        m_entries.return_value = entries_layout
        m_version.side_effect = lambda x: f"P{x}"
        if entries_layout:
            project.path.glob.return_value = paths
            assert (
                changelogs.changelog_paths
                == {
                    **{
                        f"P{p}": p
                        for p
                        in paths},
                    abstract.project.changelog._version.Version(
                        project.version.base_version):
                    m_current_dir_path.return_value})
            assert not m_paths.called
            assert (
                project.path.glob.call_args
                == [(abstract.project.changelog.CHANGELOG_PATH_GLOB, ), {}])
        else:
            m_paths.return_value = paths
            assert (
                changelogs.changelog_paths
                == {f"P{p}": p
                    for p in paths})
            assert not project.path.glob.called

    assert (
        m_version.call_args_list
        == [[(p, ), {}] for p in paths])
    assert "changelog_paths" in changelogs.__dict__


def test_abstract_changelogs_changelogs(iters, patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "reversed",
        "sorted",
        ("AChangelogs.entries_layout",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.changelog_class",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.changelog_paths",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    paths = iters(cb=lambda x: f"P{x}")

    with patched as (m_rev, m_sort, m_entries, m_class, m_paths):
        m_rev.return_value = paths
        m_entries.return_value = False
        assert (
            changelogs.changelogs
            == {p: m_class.return_value.return_value
                for p in paths})

    assert (
        m_class.return_value.call_args_list
        == [[("PROJECT", p, m_paths.return_value.__getitem__.return_value), {}]
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


def test_abstract_changelogs_entries_layout_current_path(patches):
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    current_version = abstract.project.changelog._version.Version("1.2.3")
    historical_version = abstract.project.changelog._version.Version("1.2.2")
    patched = patches(
        "reversed",
        "sorted",
        ("AChangelogs.entries_layout",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.changelog_class",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.changelog_paths",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (
            m_reversed, m_sorted, m_entries, m_class, m_paths,
            m_current_path):
        m_entries.return_value = True
        project.is_current.side_effect = (
            lambda version: version == current_version)
        m_paths.return_value = {
            current_version: MagicMock(name="CURRENT_DIR_PATH"),
            historical_version: MagicMock(name="HISTORICAL_PATH")}
        m_reversed.return_value = [current_version, historical_version]
        assert (
            changelogs.changelogs
            == {
                current_version: m_class.return_value.return_value,
                historical_version: m_class.return_value.return_value})

    assert (
        m_class.return_value.call_args_list
        == [[(project, current_version, m_current_path.return_value), {}],
            [(project,
              historical_version,
              m_paths.return_value[historical_version]), {}]])
    assert (
        project.is_current.call_args_list
        == [[(current_version, ), {}],
            [(historical_version, ), {}]])
    assert (
        m_sorted.call_args
        == [(m_paths.return_value.keys(), ), {}])
    assert (
        m_reversed.call_args
        == [(m_sorted.return_value, ), {}])


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


def test_abstract_changelogs_current_path(patches):
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    patched = patches(
        ("AChangelogs.rel_current_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_rel, ):
        assert (
            changelogs.current_path
            == project.path.joinpath.return_value)
    assert (
        project.path.joinpath.call_args
        == [(m_rel.return_value, ), {}])
    assert "current_path" not in changelogs.__dict__


def test_abstract_changelogs_current_dir_path(patches):
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    patched = patches(
        ("AChangelogs.rel_current_dir_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_rel, ):
        assert (
            changelogs.current_dir_path
            == project.path.joinpath.return_value)
    assert (
        project.path.joinpath.call_args
        == [(m_rel.return_value, ), {}])
    assert "current_dir_path" not in changelogs.__dict__


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


def test_abstract_project_datestamp(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "datetime",
        "timezone",
        ("AChangelogs.date_format",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_dt, m_tz, m_fmt):
        assert (
            changelogs.datestamp
            == (m_dt.now.return_value
                    .date.return_value
                    .strftime.return_value))

    assert (
        m_dt.now.call_args
        == [(), dict(tz=m_tz.utc)])
    assert (
        m_dt.now.return_value.date.call_args
        == [(), {}])
    assert (
        m_dt.now.return_value.date.return_value.strftime.call_args
        == [(m_fmt.return_value, ), {}])
    assert "datestamp" not in changelogs.__dict__


@pytest.mark.parametrize("pending", [None, "Pending", "cabbage"])
async def test_abstract_changelogs_is_pending(patches, pending):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "AChangelogs.__getitem__",
        ("AChangelogs.entries_layout",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_get, m_entries, m_current):
        m_entries.return_value = False
        m_get.return_value.release_date = AsyncMock(
            return_value=pending)()
        assert (
            await changelogs.is_pending
            == (pending == "Pending"))

    assert (
        m_get.call_args
        == [(m_current.return_value, ), {}])
    assert "is_pending" not in changelogs.__dict__


@pytest.mark.parametrize("yaml_exists", [True, False])
async def test_abstract_changelogs_is_pending_entries_layout(
        patches, yaml_exists):
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    patched = patches(
        "AChangelogs.__getitem__",
        ("AChangelogs.entries_layout",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current",
         dict(new_callable=PropertyMock)),
        "AChangelogs.changelog_path",
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_get, m_entries, m_current, m_clog_path):
        m_entries.return_value = True
        m_clog_path.return_value.exists.return_value = yaml_exists
        assert await changelogs.is_pending == (not yaml_exists)

    assert not m_current.called
    assert not m_get.called
    assert (
        m_clog_path.call_args
        == [(project.version, ), {}])
    assert (
        m_clog_path.return_value.exists.call_args
        == [(), {}])
    assert "is_pending" not in changelogs.__dict__


@pytest.mark.parametrize("entries_layout", [True, False])
def test_abstract_changelogs_paths(iters, patches, entries_layout):
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    patched = patches(
        ("AChangelogs.entries_layout",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_dir_path",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    paths = iters()
    project.path.glob.return_value = paths

    with patched as (m_entries, m_dir_path, m_path):
        m_entries.return_value = entries_layout
        assert (
            changelogs.paths
            == (*paths, (
                m_dir_path.return_value
                if entries_layout
                else m_path.return_value)))
    assert (
        project.path.glob.call_args
        == [(abstract.project.changelog.CHANGELOG_PATH_GLOB, ), {}])
    assert "paths" not in changelogs.__dict__


def test_abstract_changelogs_rel_current_path(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "pathlib",
        "CHANGELOG_CURRENT_PATH",
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_plib, m_path):
        assert (
            changelogs.rel_current_path
            == m_plib.Path.return_value)

    assert (
        m_plib.Path.call_args
        == [(m_path, ), {}])


def test_abstract_changelogs_rel_current_dir_path(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "pathlib",
        "CHANGELOG_CURRENT_DIR_PATH",
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_plib, m_path):
        assert (
            changelogs.rel_current_dir_path
            == m_plib.Path.return_value)

    assert (
        m_plib.Path.call_args
        == [(m_path, ), {}])
    assert "rel_current_dir_path" not in changelogs.__dict__


@pytest.mark.parametrize(
    "raises",
    [None, Exception, yaml.reader.ReaderError, exceptions.TypeCastingError])
def test_abstract_changelogs_config(patches, raises):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "cast",
        "utils.from_yaml",
        "logger",
        ("AChangelogs.config_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_cast, m_yaml, m_logger, m_path):
        if raises:
            error = raises("AN ERROR OCCURRED", 7, 23, "Y", "Z")
            m_yaml.side_effect = error
        if raises == Exception:
            with pytest.raises(Exception):
                changelogs.config
        elif raises == yaml.reader.ReaderError:
            with pytest.raises(exceptions.ChangelogError) as e:
                changelogs.config
        else:
            assert (
                changelogs.config
                == (m_yaml.return_value
                    if not raises
                    else m_cast.return_value))

    if raises == exceptions.TypeCastingError:
        assert (
            m_cast.call_args
            == [(typing.ChangelogConfigDict, error.value), {}])
        assert (
            m_logger.warning.call_args
            == [("Changelog config parsing error: "
                f"({m_path.return_value})\n{error}", ), {}])
    else:
        assert not m_logger.called
        assert not m_cast.called

    assert (
        m_yaml.call_args
        == [(m_path.return_value, typing.ChangelogConfigDict), {}])
    assert (
        ("config" in changelogs.__dict__)
        == (not raises or raises == exceptions.TypeCastingError))
    if raises != yaml.reader.ReaderError:
        return
    assert (
        e.value.args[0]
        == ("Failed to parse changelog config "
            f"({m_path.return_value}): {str(error)}"))


def test_abstract_changelogs_sections(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.config",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_config, ):
        assert (
            changelogs.sections
            == m_config.return_value.__getitem__.return_value)

    assert (
        m_config.return_value.__getitem__.call_args
        == [("sections", ), {}])
    assert "sections" in changelogs.__dict__


def test_abstract_changelogs_areas(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.config",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_config, ):
        assert (
            changelogs.areas
            == m_config.return_value.__getitem__.return_value)

    assert (
        m_config.return_value.__getitem__.call_args
        == [("areas", ), {}])
    assert "areas" in changelogs.__dict__


def test_abstract_changelogs_config_path():
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    assert (
        changelogs.config_path
        == project.path.joinpath.return_value)
    assert (
        project.path.joinpath.call_args
        == [(abstract.project.changelog.CHANGELOG_CONFIG_PATH, ), {}])
    assert "config_path" not in changelogs.__dict__


def test_abstract_changelogs_validate_sections():
    changelogs = DummyChangelogs("PROJECT")
    changelogs.sections = {"known": {"title": "Known"}}
    valid = {
        "date": "Pending",
        "known": [{"area": "api", "change": "updated"}]}
    date_only = {"date": "Pending"}
    assert changelogs.validate_sections(valid) is valid
    assert changelogs.validate_sections(date_only) is date_only


@pytest.mark.parametrize(
    "path",
    [None, pathlib.Path("changelogs/current.yaml")])
def test_abstract_changelogs_validate_sections_unknown(path):
    changelogs = DummyChangelogs("PROJECT")
    changelogs.sections = {"known": {"title": "Known"}}
    with pytest.raises(exceptions.ChangelogParseError) as e:
        changelogs.validate_sections(
            {"date": "Pending", "unknown": []},
            path)

    message = e.value.args[0]
    assert "unknown" in message
    assert abstract.project.changelog.CHANGELOG_CONFIG_PATH in message
    if path is None:
        assert "changelogs/current.yaml" not in message
        assert "(None)" not in message
    else:
        assert f"({path})" in message


def test_abstract_changelogs_validate_sections_unknown_sorted():
    changelogs = DummyChangelogs("PROJECT")
    changelogs.sections = {"known": {"title": "Known"}}
    with pytest.raises(exceptions.ChangelogParseError) as e:
        changelogs.validate_sections(
            {"date": "Pending", "zeta": [], "alpha": [], "beta": []})

    assert "alpha, beta, zeta" in e.value.args[0]


def test_abstract_changelogs_summary_path():
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    assert (
        changelogs.summary_path
        == project.path.joinpath.return_value)
    assert (
        project.path.joinpath.call_args
        == [(abstract.project.changelog.CHANGELOG_SUMMARY_PATH, ), {}])
    assert "summary_path" not in changelogs.__dict__


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


def test_abstract_changelogs_blank_summary(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.summary_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_path, ):
        assert not changelogs.blank_summary()

    assert (
        m_path.return_value.write_text.call_args
        == [("", ), {}])


@pytest.mark.parametrize("entries_layout", [True, False])
@pytest.mark.parametrize("current", [True, False])
@pytest.mark.parametrize("dev", [True, False])
@pytest.mark.parametrize(
    "items",
    [{},
     {i: True for i in range(0, 10)},
     {i: False for i in range(0, 10)},
     {i: (i % 2) for i in range(0, 10)}])
def test_abstract_changelogs_changes_for_commit(
        patches, current, dev, items, entries_layout):
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    patched = patches(
        "any",
        "set",
        "str",
        "CHANGELOG_CURRENT_DIR_PATH",
        "CHANGELOG_CURRENT_PATH",
        ("AChangelogs.entries_layout",
         dict(new_callable=PropertyMock)),
        "AChangelogs.rel_changelog_path",
        ("AChangelogs.summary_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    change = MagicMock()
    change.get.return_value.get.return_value = items

    def contains(k):
        if k == "dev":
            return dev
        return True

    change.__contains__.side_effect = contains

    with patched as (m_any, m_set, m_str, m_dir_path, m_path,
                     m_entries, m_rel, m_summary):
        m_any.return_value = current
        m_entries.return_value = entries_layout
        assert (
            changelogs.changes_for_commit(change)
            == m_set.return_value)
        anygen = m_any.call_args[0][0]
        anylist = list(anygen)

    assert isinstance(anygen, types.GeneratorType)
    assert anylist == [True, dev]
    expected_add = []
    expected_rel = []
    if current and not entries_layout:
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
        expected_add.append(m_str.return_value)
        assert (
            m_str.call_args
            == [(m_summary.return_value, ), {}])
    if entries_layout:
        # release is always in change (contains returns True for non-dev keys)
        expected_add.append(m_rel.return_value)
        expected_rel.append(project.version)
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
    if entries_layout:
        expected_add.append(m_dir_path)
    assert (
        m_set.return_value.add.call_args_list
        == [[(add, ), {}]
            for add in expected_add])
    assert (
        m_rel.call_args_list
        == [[(p, ), {}]
            for p in expected_rel])


def test_abstract_changelogs_dump_yaml(iters, patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.section_re",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.yaml",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    data = MagicMock()
    items = iters(dict, cb=lambda i: (f"K{i}", (i % 2)), count=10)
    filtered = {k: v for k, v in items.items() if v}
    data.items.return_value = items.items()
    sections = iters(cb=lambda x: f"S{x}", count=3)

    with patched as (m_re, m_yaml):
        m_re.return_value.findall.return_value = sections
        output = (
            m_yaml.return_value.dump
                  .return_value.replace
                  .return_value.replace
                  .return_value.replace.return_value)
        assert (
            changelogs.dump_yaml(data)
            == (f"{output}\n"
                if not output.endswith("\n")
                else output))

    assert (
        m_yaml.return_value.dump.call_args
        == [(filtered, ),
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
        "LegacyChangelog",
        "RST_CHANGELOG_URL_TPL",
        "AChangelogs._is_rst_changelog",
        "AChangelogs.dump_yaml",
        prefix="envoy.base.utils.abstract.project.changelog")
    release = MagicMock()
    release.version = MagicMock()

    with patched as (m_legacy, m_tpl, m_is_rst, m_dump):
        m_is_rst.return_value = True
        assert (
            await changelogs.fetch(release)
            == m_dump.return_value)

    assert (
        project.session.get.call_args
        == [(m_tpl.format.return_value, ), {}])
    assert (
        m_tpl.format.call_args
        == [(), dict(version=release.version.base_version)])
    assert (
        project.session.get.return_value.text.call_args
        == [(), {}])
    assert (
        m_legacy.call_args
        == [(project.session.get.return_value.text.return_value, ), {}])
    assert (
        m_dump.call_args
        == [(m_legacy.return_value.data, ), {}])


async def test_abstract_changelogs_fetch_entries_layout(patches):
    project = MagicMock()
    project.session.get = AsyncMock()
    changelogs = DummyChangelogs(project)
    patched = patches(
        ("AChangelogs.changelog_class",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.date_format",
         dict(new_callable=PropertyMock)),
        "AChangelogs._is_rst_changelog",
        "AChangelogs._fetch_entries",
        "AChangelogs.dump_yaml",
        prefix="envoy.base.utils.abstract.project.changelog")
    release = MagicMock()
    release.version = MagicMock()
    release.published_at = datetime(2026, 6, 3, tzinfo=timezone.utc)

    with patched as (m_class, m_date, m_is_rst, m_entries, m_dump):
        m_is_rst.return_value = False
        m_date.return_value = "%B %-d, %Y"
        m_class.return_value.data_from_entry_map.return_value = dict(
            date="Pending")
        assert (
            await changelogs.fetch(release)
            == m_dump.return_value)

    assert (
        m_entries.call_args
        == [(release.version, ), {}])
    assert (
        m_class.return_value.data_from_entry_map.call_args
        == [(m_entries.return_value, ), {}])
    assert not project.session.get.called
    assert (
        m_dump.call_args
        == [(dict(
            date=release.published_at.date().strftime(m_date.return_value)),
            ), {}])


async def test_abstract_changelogs_fetch_entries_layout_empty_entries(patches):
    changelogs = DummyChangelogs(MagicMock())
    patched = patches(
        ("AChangelogs.changelog_class",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.date_format",
         dict(new_callable=PropertyMock)),
        "AChangelogs._is_rst_changelog",
        "AChangelogs._fetch_entries",
        "AChangelogs.dump_yaml",
        prefix="envoy.base.utils.abstract.project.changelog")
    release = MagicMock()
    release.version = MagicMock()
    release.published_at = datetime(2026, 6, 3, tzinfo=timezone.utc)

    with patched as (m_class, m_date, m_is_rst, m_entries, m_dump):
        m_is_rst.return_value = False
        m_date.return_value = "%B %-d, %Y"
        m_entries.return_value = {}
        m_class.return_value.data_from_entry_map.return_value = dict(
            date="Pending")
        assert (
            await changelogs.fetch(release)
            == m_dump.return_value)

    assert (
        m_dump.call_args
        == [(dict(
            date=release.published_at.date().strftime(m_date.return_value)),
            ), {}])


async def test_abstract_changelogs__fetch_entries():
    project = MagicMock()
    project.repo.getitem = AsyncMock(return_value={
        "tree": [
            {"type": "blob", "path": "bug_fixes/jwt__foo.rst"},
            {"type": "blob", "path": "new_features/grpc__cool.rst"},
            {"type": "blob", "path": "new_features/ignore.txt"},
            {"type": "tree", "path": "bug_fixes"}]})
    response_0 = MagicMock()
    response_0.text = AsyncMock(return_value="Fixed jwt.\n")
    response_1 = MagicMock()
    response_1.text = AsyncMock(return_value="New feature.\n")
    project.session.get = AsyncMock(side_effect=[response_0, response_1])
    changelogs = DummyChangelogs(project)
    version = abstract.project.changelog._version.Version("1.35.11")

    assert (
        await changelogs._fetch_entries(version)
        == {
            "bug_fixes/jwt__foo.rst": "Fixed jwt.\n",
            "new_features/grpc__cool.rst": "New feature.\n"})
    assert (
        project.repo.getitem.call_args
        == [(
            f"git/trees/v{version.base_version}:"
            f"{abstract.project.changelog.CHANGELOG_CURRENT_DIR_PATH}"
            "?recursive=1",
            ), {}])
    assert (
        project.session.get.call_args_list
        == [[(
            abstract.project.changelog.CHANGELOG_ENTRY_URL_TPL.format(
                version=version.base_version,
                path="bug_fixes/jwt__foo.rst"),
            ), {}],
            [(
                abstract.project.changelog.CHANGELOG_ENTRY_URL_TPL.format(
                    version=version.base_version,
                    path="new_features/grpc__cool.rst"),
                ), {}]])


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


async def test_abstract_changelogs_sync(iters, patches):

    def mock_release(i):
        release = MagicMock()
        release.version = i
        return release

    releases = iters(cb=mock_release, count=10)

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
        == [[(release, ), {}]
            for release
            in releases
            if release.version % 2])


async def test_abstract_changelogs_sync_entries_layout_regression(
        tmp_path, patches):
    class ConcreteChangelogs(DummyChangelogs):

        @property
        def changelog_class(self):
            return DummyChangelog

    changelog_dir = tmp_path.joinpath("changelogs")
    changelog_dir.mkdir()
    project = MagicMock()
    project.path = tmp_path
    project.repo.getitem = AsyncMock(return_value={
        "tree": [
            {"type": "blob", "path": "bug_fixes/jwt__foo.rst"},
            {"type": "blob", "path": "new_features/grpc__cool.rst"}]})
    response_0 = MagicMock()
    response_0.text = AsyncMock(return_value="Fixed jwt.\n")
    response_1 = MagicMock()
    response_1.text = AsyncMock(return_value="New feature.\n")
    project.session.get = AsyncMock(side_effect=[response_0, response_1])
    release = MagicMock()
    release.version = abstract.project.changelog._version.Version("1.35.11")
    release.published_at = datetime(2026, 6, 3, tzinfo=timezone.utc)

    async def repo_releases():
        yield release

    project.repo.releases.side_effect = repo_releases
    changelogs = ConcreteChangelogs(project)
    patched = patches(
        "AChangelogs.should_sync",
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_should, ):
        m_should.return_value = True
        assert await changelogs.sync() == {release.version: True}

    assert (
        yaml.safe_load(changelog_dir.joinpath("1.35.11.yaml").read_text())
        == dict(
            date="June 3, 2026",
            bug_fixes=[dict(area="jwt", change="Fixed jwt.\n")],
            new_features=[dict(area="grpc", change="New feature.\n")]))


async def test_abstract_changelogs_sync_entries_layout_zero_entries(
        tmp_path, patches):
    class ConcreteChangelogs(DummyChangelogs):

        @property
        def changelog_class(self):
            return DummyChangelog

    changelog_dir = tmp_path.joinpath("changelogs")
    changelog_dir.mkdir()
    project = MagicMock()
    project.path = tmp_path
    project.repo.getitem = AsyncMock(return_value={"tree": []})
    project.session.get = AsyncMock()
    release = MagicMock()
    release.version = abstract.project.changelog._version.Version("1.35.11")
    release.published_at = datetime(2026, 6, 3, tzinfo=timezone.utc)

    async def repo_releases():
        yield release

    project.repo.releases.side_effect = repo_releases
    changelogs = ConcreteChangelogs(project)
    patched = patches(
        "AChangelogs.should_sync",
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_should, ):
        m_should.return_value = True
        assert await changelogs.sync() == {release.version: True}

    assert (
        yaml.safe_load(changelog_dir.joinpath("1.35.11.yaml").read_text())
        == dict(date="June 3, 2026"))


def test_abstract_changelogs_write_changelog(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "AChangelogs.changelog_path",
        prefix="envoy.base.utils.abstract.project.changelog")
    version = MagicMock()
    text = MagicMock()

    with patched as (m_path, ):
        assert not changelogs.write_changelog(version, text)

    assert (
        m_path.call_args
        == [(version, ), {}])
    assert (
        m_path.return_value.write_text.call_args
        == [(text, ), {}])


@pytest.mark.parametrize("entries_layout", [True, False])
def test_abstract_changelogs_write_current(iters, patches, entries_layout):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "AChangelogs._write_current_placeholder",
        ("AChangelogs.entries_layout",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_dir_path",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_path",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_tpl",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.sections",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    sections = iters(dict, cb=lambda x: (f"K{x}", MagicMock()), count=10)
    sections["changes"] = MagicMock()

    with patched as patchy:
        (m_placeholder, m_entries,
         m_dir_path, m_path, m_tpl, m_sections) = patchy
        m_entries.return_value = entries_layout
        m_sections.return_value.items.return_value = sections.items()
        assert not changelogs.write_current()

    if entries_layout:
        assert (
            m_dir_path.return_value.mkdir.call_args
            == [(), dict(parents=True, exist_ok=True)])
        assert (
            m_placeholder.call_args
            == [(), {}])
        assert not m_path.return_value.write_text.called
        assert not m_dir_path.return_value.__truediv__.called
        assert not m_tpl.called
        assert not m_sections.called
    else:
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
        assert not m_placeholder.called
        for k, v in sections.items():
            if k == "changes":
                assert not v.get.called
            else:
                assert (
                    v.get.call_args
                    == [("description", ), {}])


def test_abstract_changelogs__write_current_placeholder(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        ("AChangelogs.current_dir_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_dir_path, ):
        assert not changelogs._write_current_placeholder()

    assert (
        m_dir_path.return_value.joinpath.call_args
        == [(
            abstract.project.changelog.CHANGELOG_CURRENT_PLACEHOLDER, ),
            {}])
    assert (
        m_dir_path.return_value.joinpath.return_value.write_text.call_args
        == [("", ), {}])


@pytest.mark.parametrize("entries_layout", [True, False])
@pytest.mark.parametrize("pending", [True, False])
async def test_abstract_changelogs_write_date(
        patches, pending, entries_layout):
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    patched = patches(
        "AChangelogs.__getitem__",
        ("AChangelogs.changelog_class",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.entries_layout",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_dir_path",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_path",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.is_pending",
         dict(new_callable=PropertyMock)),
        "AChangelogs.changelog_path",
        "AChangelogs.dump_yaml",
        "AChangelogs.validate_sections",
        prefix="envoy.base.utils.abstract.project.changelog")
    date = MagicMock()

    with patched as (m_get, m_clogclass, m_entries, m_current, m_dir_path,
                     m_path, m_pending, m_clog_path, m_yaml, m_validate):
        m_pending.side_effect = AsyncMock(return_value=pending)
        m_entries.return_value = entries_layout
        if not entries_layout:
            # Only set up the async data mock for the legacy branch; creating
            # an unawaited coroutine on the entries branch causes
            # PytestUnraisableExceptionWarning on the next test.
            data = AsyncMock()
            data.return_value.copy = MagicMock()
            m_get.return_value.data = data()
        if not pending:
            with pytest.raises(exceptions.ReleaseError) as e:
                await changelogs.write_date(date)
        else:
            assert not await changelogs.write_date(date)

    if not pending:
        assert (
            e.value.args[0]
            == "Current changelog date is not set to `Pending`")
        assert not m_current.called
        assert not m_get.called
        assert not m_path.called
        assert not m_yaml.called
        assert not m_clog_path.called
        assert not m_validate.called
        if not entries_layout:
            await m_get.return_value.data
        return

    if entries_layout:
        assert not m_path.called
        assert not m_get.called
        entries_data = (
            m_clogclass.return_value.get_data_from_entries.return_value)
        assert (
            m_clogclass.return_value.get_data_from_entries.call_args
            == [(m_dir_path.return_value, ), {}])
        assert (
            entries_data.__setitem__.call_args
            == [("date", date), {}])
        assert (
            m_validate.call_args
            == [(entries_data, ), {}])
        assert (
            m_clog_path.call_args
            == [(project.version, ), {}])
        assert (
            m_clog_path.return_value.write_text.call_args
            == [(m_yaml.return_value, ), {}])
        assert (
            m_yaml.call_args
            == [(entries_data, ), {}])
    else:
        assert (
            m_get.call_args
            == [(m_current.return_value, ), {}])
        assert (
            data.return_value.copy.call_args
            == [(), {}])
        assert (
            m_path.return_value.write_text.call_args
            == [(m_yaml.return_value, ), {}])
        assert (
            m_yaml.call_args
            == [(data.return_value.copy.return_value, ), {}])


@pytest.mark.parametrize("entries_layout", [True, False])
@pytest.mark.parametrize("exists", [True, False])
def test_abstract_changelogs_write_version(patches, exists, entries_layout):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "shutil",
        "AChangelogs._write_current_placeholder",
        ("AChangelogs.entries_layout",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.changelog_class",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_dir_path",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.datestamp",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_path",
         dict(new_callable=PropertyMock)),
        "AChangelogs.changelog_path",
        "AChangelogs.dump_yaml",
        prefix="envoy.base.utils.abstract.project.changelog")
    version = MagicMock()

    with patched as (
            m_shutil, m_placeholder, m_entries, m_clogclass, m_dir_path,
            m_datestamp, m_path, m_clog_path, m_dump):
        m_entries.return_value = entries_layout
        m_clog_path.return_value.exists.return_value = exists
        entries_data = {}
        m_clogclass.return_value.get_data_from_entries.return_value = (
            entries_data)
        if entries_layout and exists:
            # Simulate yaml exists but with Pending date (DevError path)
            m_clogclass.return_value.get_data.return_value = {
                "date": "Pending"}
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
        if entries_layout:
            assert (
                m_clogclass.return_value.get_data.call_args
                == [(m_clog_path.return_value, ), {}])
        else:
            assert not m_clogclass.return_value.get_data.called
        assert not m_placeholder.called
        return
    if entries_layout:
        assert (
            m_clogclass.return_value.get_data_from_entries.call_args
            == [(m_dir_path.return_value, ), {}])
        assert entries_data == {"date": m_datestamp.return_value}
        assert (
            m_dump.call_args
            == [(entries_data, ), {}])
        assert (
            m_clog_path.return_value.write_text.call_args
            == [(m_dump.return_value, ), {}])
        assert not m_path.called
        assert (
            m_shutil.rmtree.call_args
            == [(m_dir_path.return_value, ), {}])
        assert (
            m_dir_path.return_value.mkdir.call_args
            == [(), {}])
        assert (
            m_placeholder.call_args
            == [(), {}])
    else:
        assert not m_placeholder.called
        assert (
            m_clog_path.return_value.write_text.call_args
            == [(m_path.return_value.read_text.return_value, ), {}])
        assert (
            m_path.return_value.read_text.call_args
            == [(), {}])
        assert not m_shutil.rmtree.called


def test_abstract_changelogs_write_version_entries_layout_predated(patches):
    """write_version tolerates a pre-existing dated yaml from write_date."""
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "shutil",
        "AChangelogs._write_current_placeholder",
        ("AChangelogs.entries_layout",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.changelog_class",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_dir_path",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_path",
         dict(new_callable=PropertyMock)),
        "AChangelogs.changelog_path",
        prefix="envoy.base.utils.abstract.project.changelog")
    version = MagicMock()

    with patched as (
            m_shutil, m_placeholder, m_entries, m_clogclass, m_dir_path,
            m_path, m_clog_path):
        m_entries.return_value = True
        m_clog_path.return_value.exists.return_value = True
        m_clogclass.return_value.get_data.return_value = {
            "date": "June 10, 2026"}
        assert not changelogs.write_version(version)

    assert (
        m_clog_path.call_args
        == [(version, ), {}])
    assert (
        m_clogclass.return_value.get_data.call_args
        == [(m_clog_path.return_value, ), {}])
    assert not m_clogclass.return_value.get_data_from_entries.called
    assert not m_clog_path.return_value.write_text.called
    assert (
        m_shutil.rmtree.call_args
        == [(m_dir_path.return_value, ), {}])
    assert (
        m_dir_path.return_value.mkdir.call_args
        == [(), {}])
    assert (
        m_placeholder.call_args
        == [(), {}])


def test_abstract_changelogs_write_version_entries_parse_error(patches):
    changelogs = DummyChangelogs("PROJECT")
    patched = patches(
        "shutil",
        ("AChangelogs.entries_layout",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.changelog_class",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_dir_path",
         dict(new_callable=PropertyMock)),
        ("AChangelogs.current_path",
         dict(new_callable=PropertyMock)),
        "AChangelogs.changelog_path",
        "AChangelogs.dump_yaml",
        prefix="envoy.base.utils.abstract.project.changelog")
    version = MagicMock()

    with patched as (m_shutil, m_entries, m_clogclass, m_dir_path,
                     m_path, m_clog_path, m_dump):
        m_entries.return_value = True
        m_clog_path.return_value.exists.return_value = False
        m_clogclass.return_value.get_data_from_entries.side_effect = (
            exceptions.ChangelogParseError("parse error"))
        with pytest.raises(exceptions.ChangelogParseError):
            changelogs.write_version(version)

    assert not m_clog_path.return_value.write_text.called
    assert not m_path.return_value.write_text.called
    assert not m_shutil.rmtree.called
    assert not m_dir_path.return_value.mkdir.called


def test_abstract_changelogs_yaml_change_presenter():
    changelogs = DummyChangelogs("PROJECT")
    dumper = MagicMock()
    data = MagicMock()
    normal = data.rstrip.return_value
    assert (
        changelogs.yaml_change_presenter(dumper, data)
        == dumper.represent_scalar.return_value)
    assert (
        data.rstrip.call_args
        == [("\n", ), {}])
    assert (
        dumper.represent_scalar.call_args
        == [('tag:yaml.org,2002:str', f"{normal}\n"),
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


@pytest.mark.parametrize("is_dir", [True, False])
def test_abstract_changelogs_entries_layout(patches, is_dir):
    project = MagicMock()
    changelogs = DummyChangelogs(project)
    patched = patches(
        "CHANGELOG_CURRENT_DIR_PATH",
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_dir_path, ):
        project.path.joinpath.return_value.is_dir.return_value = is_dir
        assert changelogs.entries_layout == is_dir

    assert (
        project.path.joinpath.call_args
        == [(m_dir_path, ), {}])
    assert (
        project.path.joinpath.return_value.is_dir.call_args
        == [(), {}])
    assert "entries_layout" not in changelogs.__dict__


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


@pytest.mark.parametrize(
    "raises",
    [None, Exception, yaml.reader.ReaderError, exceptions.TypeCastingError])
def test_abstract_changelog_get_data(iters, patches, raises):
    patched = patches(
        "cast",
        "utils.from_yaml",
        "typing",
        prefix="envoy.base.utils.abstract.project.changelog")

    changes = iters(dict, count=10, cb=lambda c: (f"K{c}", c))
    for k, v in changes.items():
        if v % 2:
            changes[k] = iters(cb=lambda i: MagicMock(), count=7)
        else:
            changes[k] = None
    changes["date"] = "NOTCHANGE"
    path = MagicMock()

    with patched as (m_cast, m_yaml, m_typing):
        m_yaml.return_value.items.return_value = changes.items()
        if raises:
            error = raises("AN ERROR OCCURRED", 7, 23, "Y", "Z")
            m_yaml.side_effect = error
        if raises == Exception:
            with pytest.raises(Exception):
                abstract.AChangelog.get_data(path)
        elif raises:
            with pytest.raises(exceptions.ChangelogParseError) as e:
                abstract.AChangelog.get_data(path)
        else:
            assert (
                abstract.AChangelog.get_data(path)
                == m_cast.return_value)

    assert (
        m_yaml.call_args
        == [(path, m_typing.ChangelogSourceDict), {}])
    if raises == Exception:
        return
    elif raises:
        assert (
            e.value.args[0]
            == ("Failed to parse: "
                f"{path}\n{str(error)}"))
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
        m_cast.call_args
        == [(m_typing.ChangelogDict, expected), {}])


def test_abstract_changelog_data_from_entry_map_happy_path():
    entries = {
        "new_features/grpc__cool.rst": "New feature.\n",
        "bug_fixes/oauth2__foo_fix.rst": "Fixed oauth2.\n",
        "bug_fixes/jwt__bar_fix.rst": "Fixed jwt.\n"}

    assert (
        abstract.AChangelog.data_from_entry_map(entries)
        == dict(
            date="Pending",
            bug_fixes=[
                dict(area="jwt", change="Fixed jwt.\n"),
                dict(area="oauth2", change="Fixed oauth2.\n")],
            new_features=[
                dict(area="grpc", change="New feature.\n")]))


@pytest.mark.parametrize(
    "entry",
    ["bug_fixes/no_separator.rst",
     "bug_fixes/a__b__c.rst"])
def test_abstract_changelog_data_from_entry_map_separator_validation(entry):
    with pytest.raises(exceptions.ChangelogParseError) as e:
        abstract.AChangelog.data_from_entry_map({entry: "content\n"})
    assert (
        e.value.args[0]
        == ("Invalid entry filename "
            "(expected exactly one '__'): "
            f"{entry}"))


def test_abstract_changelog_get_data_from_entries(patches):
    patched = patches(
        "sorted",
        "AChangelog.data_from_entry_map",
        prefix="envoy.base.utils.abstract.project.changelog")
    entry_dir = MagicMock()
    first = MagicMock()
    first.parent.name = "bug_fixes"
    first.name = "jwt__foo.rst"
    first.read_text.return_value = "Fixed jwt.\n"
    second = MagicMock()
    second.parent.name = "new_features"
    second.name = "grpc__cool.rst"
    second.read_text.return_value = "New feature.\n"
    paths = [second, first]

    with patched as (m_sorted, m_data):
        entry_dir.glob.return_value = paths
        m_sorted.return_value = [first, second]
        assert (
            abstract.AChangelog.get_data_from_entries(entry_dir)
            == m_data.return_value)

    assert (
        entry_dir.glob.call_args
        == [(abstract.project.changelog.CHANGELOG_ENTRY_GLOB, ), {}])
    assert (
        m_sorted.call_args
        == [(paths, ), {}])
    assert (
        m_data.call_args
        == [({
            "bug_fixes/jwt__foo.rst": first.read_text.return_value,
            "new_features/grpc__cool.rst": second.read_text.return_value},
            ), {}])


def test_abstract_changelog_get_data_from_entries_empty_dir():
    entry_dir = MagicMock()
    entry_dir.glob.return_value = []
    assert (
        abstract.AChangelog.get_data_from_entries(entry_dir)
        == dict(date="Pending"))


def test_abstract_changelog_constructor():

    with pytest.raises(TypeError):
        abstract.AChangelog("PROECT", "VERSION", "PATH")

    changelog = DummyChangelog("PROECT", "VERSION", "PATH")
    assert changelog._version == "VERSION"
    assert changelog.version == "VERSION"
    assert "version" not in changelog.__dict__
    assert changelog.path == "PATH"

    with pytest.raises(NotImplementedError):
        changelog.entry_class


def test_abstract_changelog_base_version(patches):
    changelog = DummyChangelog("PROECT", "VERSION", "PATH")
    patched = patches(
        ("AChangelog.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_version, ):
        assert (
            changelog.base_version
            == m_version.return_value.base_version)

    assert "base_version" not in changelog.__dict__


@pytest.mark.parametrize("match", [True, False])
def test_abstract_changelog__is_current(match):
    project = MagicMock()
    version = "VERSION"
    changelog = DummyChangelog(project, version, "PATH")
    project.changelogs.current = version if match else MagicMock()
    assert changelog._is_current == match
    assert "_is_current" not in changelog.__dict__


@pytest.mark.parametrize("yaml_exists", [True, False])
@pytest.mark.parametrize("entries_layout", [True, False])
@pytest.mark.parametrize("is_current", [True, False])
async def test_abstract_changelog_data(
        patches, entries_layout, is_current, yaml_exists):
    project = MagicMock()
    project.execute = AsyncMock()
    project.changelogs.validate_sections.return_value = "VALIDATED"
    project.changelogs.entries_layout = entries_layout
    project.changelogs.changelog_path.return_value.is_file.return_value = (
        yaml_exists)
    changelog = DummyChangelog(project, "VERSION", "PATH")
    patched = patches(
        ("AChangelog._is_current",
         dict(new_callable=PropertyMock)),
        "AChangelog.get_data",
        "AChangelog.get_data_from_entries",
        ("AChangelog.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_is_current, m_get, m_get_entries, m_path):
        m_is_current.return_value = is_current
        assert (
            await changelog.data
            == project.changelogs.validate_sections.return_value
            == getattr(
                changelog,
                abstract.AChangelog.data.cache_name)["data"])

    use_entries = is_current and entries_layout
    if use_entries and not yaml_exists:
        assert (
            project.execute.call_args
            == [(m_get_entries,
                 project.changelogs.current_dir_path), {}])
        assert not m_get.called
    elif use_entries and yaml_exists:
        assert (
            project.execute.call_args
            == [(m_get,
                 project.changelogs.changelog_path.return_value), {}])
        assert not m_get_entries.called
        assert (
            project.changelogs.changelog_path.call_args
            == [("VERSION", ), {}])
    else:
        assert (
            project.execute.call_args
            == [(m_get, m_path.return_value), {}])
        assert not m_get_entries.called
    assert (
        project.changelogs.validate_sections.call_args
        == [(project.execute.return_value, m_path.return_value), {}])


async def test_abstract_changelog_data_unknown_section(tmp_path):
    changelog_path = tmp_path.joinpath("changelogs/current.yaml")
    changelog_path.parent.mkdir()
    changelog_path.write_text(
        "date: Pending\n"
        "unknown:\n"
        "  - area: api\n"
        "    change: changed\n")
    tmp_path.joinpath("changelogs/changelogs.yaml").write_text(
        "sections:\n"
        "  known:\n"
        "    title: Known\n")

    project = MagicMock()
    project.path = tmp_path

    async def execute(func, path):
        return func(path)

    project.execute = AsyncMock(side_effect=execute)
    project.changelogs = DummyChangelogs(project)
    changelog = DummyChangelog(project, "VERSION", changelog_path)

    with pytest.raises(exceptions.ChangelogParseError) as e:
        await changelog.data

    assert "unknown" in e.value.args[0]
    assert f"({changelog_path})" in e.value.args[0]


async def test_abstract_changelog_entries_layout_no_current_yaml(tmp_path):

    class ConcreteChangelogs(DummyChangelogs):

        @property
        def changelog_class(self):
            return DummyChangelog

    current_dir = tmp_path.joinpath("changelogs/current/bug_fixes")
    current_dir.mkdir(parents=True)
    current_dir.joinpath("jwt__foo_fix.rst").write_text("Fixed jwt.\n")
    tmp_path.joinpath("changelogs/changelogs.yaml").write_text(
        "sections:\n"
        "  bug_fixes:\n"
        "    title: Bug fixes\n"
        "areas:\n"
        "  jwt:\n"
        "    title: JWT\n")

    project = MagicMock()
    project.path = tmp_path
    project.is_dev = True
    project.version = abstract.project.changelog._version.Version("1.2.4-dev")

    async def execute(func, *args):
        return func(*args)

    project.execute = AsyncMock(side_effect=execute)
    changelogs = ConcreteChangelogs(project)
    project.changelogs = changelogs
    current_changelog = changelogs[changelogs.current]

    assert not changelogs.current_path.exists()
    assert (await current_changelog.data)["date"] == "Pending"
    assert await changelogs.is_pending

    # write_date now freezes entries into changelogs/1.2.4.yaml
    assert not await changelogs.write_date("June 1, 2026")
    assert not changelogs.current_path.exists()

    version_yaml = tmp_path.joinpath("changelogs/1.2.4.yaml")
    assert version_yaml.exists()
    version_data = yaml.safe_load(version_yaml.read_text())
    assert version_data["date"] == "June 1, 2026"
    assert (
        version_data["bug_fixes"]
        == [{"area": "jwt", "change": "Fixed jwt.\n"}])

    # current/ entries are NOT removed by write_date
    assert changelogs.current_dir_path.exists()
    assert list(changelogs.current_dir_path.rglob("*.rst"))

    # write_version for the old previous version (dev-flow path): creates yaml
    # from entries and cleans up current/
    version = abstract.project.changelog._version.Version("1.2.3")
    changelogs.write_version(version)
    old_version_data = yaml.safe_load(
        tmp_path.joinpath("changelogs/1.2.3.yaml").read_text())
    assert old_version_data["date"] == changelogs.datestamp
    assert (
        old_version_data["bug_fixes"]
        == [{"area": "jwt", "change": "Fixed jwt.\n"}])
    assert changelogs.current_dir_path.exists()
    assert not list(changelogs.current_dir_path.rglob("*.rst"))
    assert changelogs.current_dir_path.joinpath("PLACEHOLDER").is_file()


async def test_abstract_changelog_release_flow_regression(tmp_path):
    """write_version tolerates the dated yaml created by write_date.

    Simulates the full release → dev cycle:
    1.  write_date writes changelogs/{version}.yaml with the release date.
    2.  write_version (next dev cycle) cleans up current/ without error.
    """

    class ConcreteChangelogs(DummyChangelogs):

        @property
        def changelog_class(self):
            return DummyChangelog

    current_dir = tmp_path.joinpath("changelogs/current/bug_fixes")
    current_dir.mkdir(parents=True)
    current_dir.joinpath("runtime__rtds_fix.rst").write_text(
        "Fixed RTDS.\n")
    tmp_path.joinpath("changelogs/changelogs.yaml").write_text(
        "sections:\n"
        "  bug_fixes:\n"
        "    title: Bug fixes\n"
        "areas:\n"
        "  runtime:\n"
        "    title: Runtime\n")

    project = MagicMock()
    project.path = tmp_path
    project.version = abstract.project.changelog._version.Version("1.38.2-dev")

    async def execute(func, *args):
        return func(*args)

    project.execute = AsyncMock(side_effect=execute)
    changelogs = ConcreteChangelogs(project)
    project.changelogs = changelogs

    # Release flow: write_date creates changelogs/1.38.2.yaml with date
    assert await changelogs.is_pending
    await changelogs.write_date("June 10, 2026")

    version_yaml = tmp_path.joinpath("changelogs/1.38.2.yaml")
    assert version_yaml.exists()
    version_data = yaml.safe_load(version_yaml.read_text())
    assert version_data["date"] == "June 10, 2026"
    assert (
        version_data["bug_fixes"]
        == [{"area": "runtime", "change": "Fixed RTDS.\n"}])

    # current/ entries are still present (not cleaned up by write_date)
    assert changelogs.current_dir_path.exists()
    assert list(changelogs.current_dir_path.rglob("*.rst"))

    # Docs build reads the correct date from the version yaml (not "Pending")
    current_changelog = changelogs[changelogs.current]
    assert (await current_changelog.data)["date"] == "June 10, 2026"

    # Dev cycle: write_version tolerates existing yaml and cleans current/
    release_version = abstract.project.changelog._version.Version("1.38.2")
    changelogs.write_version(release_version)

    # version yaml unchanged
    assert version_yaml.exists()
    assert yaml.safe_load(version_yaml.read_text())["date"] == "June 10, 2026"

    # current/ wiped
    assert changelogs.current_dir_path.exists()
    assert not list(changelogs.current_dir_path.rglob("*.rst"))
    assert changelogs.current_dir_path.joinpath("PLACEHOLDER").is_file()


async def test_abstract_changelog_release_date(patches):
    changelog = DummyChangelog("PROECT", "VERSION", "PATH")
    patched = patches(
        ("AChangelog.data",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")

    with patched as (m_data, ):
        data = AsyncMock()
        m_data.side_effect = data
        assert (
            await changelog.release_date
            == data.return_value.__getitem__.return_value)

    assert (
        data.return_value.__getitem__.call_args
        == [("date", ), {}])
    assert "release_date" not in changelog.__dict__


async def test_abstract_changelog_entries(iters, patches):
    changelog = DummyChangelog("PROECT", "VERSION", "PATH")
    patched = patches(
        "sorted",
        ("AChangelog.data",
         dict(new_callable=PropertyMock)),
        ("AChangelog.entry_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.changelog")
    entries = iters()

    with patched as (m_sort, m_data, m_entry):
        data = MagicMock()
        data.__getitem__.return_value = entries
        m_data.side_effect = AsyncMock(return_value=data)
        assert (
            await changelog.entries("SECTION")
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
        data.__getitem__.call_args
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


def test_legacy_changelog_data(iters, patches):
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
    clog = iters(dict, cb=lambda i: (f"K{i}", i), count=10)

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
