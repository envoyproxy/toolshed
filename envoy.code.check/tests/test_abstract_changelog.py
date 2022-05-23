
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from envoy.base import utils
from envoy.code import check


class _DummyChangelogCheck(check.AChangelogCheck):

    @property
    def changelog_status_class(self):
        return super().changelog_status_class

    @property
    def changes_checker_class(self):
        return super().changes_checker_class


class DummyChangelogCheck(_DummyChangelogCheck):

    def __init__(self):
        pass


def test_changelogcheck_constructor(patches):
    patched = patches(
        "abstract.AProjectCodeCheck.__init__",
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_super, ):
        m_super.return_value = None
        with pytest.raises(TypeError):
            check.AChangelogCheck("PROJECT", "DIRECTORY")

        changelog = _DummyChangelogCheck("PROJECT", "DIRECTORY")

    assert isinstance(changelog, check.AProjectCodeCheck)
    assert (
        m_super.call_args
        == [("PROJECT", "DIRECTORY"), {}])

    iface_props = ["changelog_status_class", "changes_checker_class"]
    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(changelog, prop)


def test_changelogcheck_dunder_iter(patches):
    changelog = DummyChangelogCheck()
    patched = patches(
        ("AChangelogCheck.changelogs",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")
    clogs = [f"C{i}" for i in range(0, 5)]

    with patched as (m_clogs, ):
        m_clogs.return_value = clogs
        genresult = changelog.__iter__()
        genlist = list(genresult)

    assert isinstance(genresult, types.GeneratorType)
    assert genlist == clogs


def test_changelogcheck_changes_checker(patches):
    project = MagicMock()
    changelog = DummyChangelogCheck()
    changelog.project = project
    patched = patches(
        ("AChangelogCheck.changes_checker_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_class, ):
        assert (
            changelog.changes_checker
            == m_class.return_value.return_value)

    assert (
        m_class.return_value.call_args
        == [(project.changelogs.sections, ), {}])
    assert "changes_checker" in changelog.__dict__


def test_changelogcheck_changelogs(patches):
    project = MagicMock()
    clogs = {f"K{i}": f"V{i}" for i in range(0, 5)}
    project.changelogs.values.return_value = clogs.values()
    changelog = DummyChangelogCheck()
    changelog.project = project
    patched = patches(
        "tuple",
        ("AChangelogCheck.changelog_status_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_tuple, m_class):
        assert (
            changelog.changelogs
            == m_tuple.return_value)
        genresult = m_tuple.call_args[0][0]
        genlist = list(genresult)

    assert isinstance(genresult, types.GeneratorType)
    assert (
        genlist
        == [m_class.return_value.return_value
            for c in clogs])
    assert (
        m_class.return_value.call_args_list
        == [[(changelog,
              c), {}]
            for c in clogs.values()])


def test_changelogstatus_constructor():
    _check = MagicMock()
    changelog = MagicMock()
    status = check.AChangelogStatus(_check, changelog)
    assert status._check == _check
    assert status.changelog == changelog
    assert status.project == _check.project
    assert "project" not in status.__dict__
    assert status.checker == _check.changes_checker
    assert "checker" not in status.__dict__
    assert status.version == changelog.version
    assert "version" not in status.__dict__


async def test_changelogstatus_data():
    clog = MagicMock()
    data = AsyncMock()
    clog.data = data()
    status = check.AChangelogStatus(MagicMock(), clog)
    assert (
        await status.data
        == data.return_value)
    assert not hasattr(
        status,
        check.AChangelogStatus.data.cache_name)


async def test_changelogstatus_date(patches):
    status = check.AChangelogStatus(MagicMock(), MagicMock())
    patched = patches(
        ("AChangelogStatus.data",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_data, ):
        data = AsyncMock()
        m_data.side_effect = data
        assert (
            await status.date
            == data.return_value.__getitem__.return_value)

    assert (
        data.return_value.__getitem__.call_args
        == [("date", ), {}])
    assert not hasattr(
        status,
        check.AChangelogStatus.date.cache_name)


def test_changelogstatus_date_format(patches):
    status = check.AChangelogStatus(MagicMock(), MagicMock())
    patched = patches(
        ("AChangelogStatus.project",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_project, ):
        assert (
            status.date_format
            == (m_project.return_value.changelogs.date_format
                         .replace.return_value))

    assert (
        m_project.return_value.changelogs.date_format.replace.call_args
        == [("-", ""), {}])
    assert "date_format" in status.__dict__


@pytest.mark.parametrize("is_current", [True, False])
@pytest.mark.parametrize("is_dev", [True, False])
@pytest.mark.parametrize("is_pending", [True, False])
async def test_changelogstatus_dev_not_pending(
        patches, is_current, is_dev, is_pending):
    status = check.AChangelogStatus(MagicMock(), MagicMock())
    patched = patches(
        ("AChangelogStatus.is_current",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.is_pending",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.project",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_current, m_pending, m_project):
        m_current.return_value = is_current
        m_project.return_value.is_dev = is_dev
        m_pending.side_effect = AsyncMock(return_value=is_pending)
        assert (
            await status.dev_not_pending
            == (is_current and is_dev and not is_pending))

    assert not hasattr(
        status,
        check.AChangelogStatus.dev_not_pending.cache_name)


@pytest.mark.parametrize("is_current", [True, False])
@pytest.mark.parametrize("exists", [True, False])
def test_changelogstatus_duplicate_current(patches, is_current, exists):
    status = check.AChangelogStatus(MagicMock(), MagicMock())
    patched = patches(
        ("AChangelogStatus.is_current",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.project",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_current, m_project, m_version):
        m_current.return_value = is_current
        (m_project.return_value.changelogs
                  .changelog_path.return_value
                  .exists.return_value) = exists
        assert (
            status.duplicate_current
            == (is_current and exists))

    if not is_current:
        assert not m_project.called
        assert not m_version.called
        return
    assert (
        m_project.return_value.changelogs.changelog_path.call_args
        == [(m_version.return_value, ), {}])
    assert (
        (m_project.return_value.changelogs.changelog_path
                  .return_value.exists.call_args)
        == [(), {}])
    assert "duplicate_current" not in status.__dict__


@pytest.mark.parametrize(
    "raises",
    [None, BaseException, utils.exceptions.ChangelogParseError])
async def test_changelogstatus_errors(patches, raises):
    status = check.AChangelogStatus(MagicMock(), MagicMock())
    patched = patches(
        ("AChangelogStatus.version",
         dict(new_callable=PropertyMock)),
        "AChangelogStatus.check_date",
        "AChangelogStatus.check_sections",
        "AChangelogStatus.check_version",
        prefix="envoy.code.check.abstract.changelog")
    version_errors = [f"V{i}" for i in range(0, 5)]
    date_errors = [f"D{i}" for i in range(0, 5)]
    sections_errors = [f"S{i}" for i in range(0, 5)]

    with patched as (m_version, m_date, m_sections, m_versions):
        if raises:
            error = raises("AN ERROR OCCURRED")
            m_date.side_effect = error
        m_date.return_value = date_errors
        m_sections.return_value = sections_errors
        m_versions.return_value = version_errors
        if raises == BaseException:
            with pytest.raises(raises):
                await status.errors
            return
        assert (
            await status.errors
            == ((*version_errors, *date_errors, *sections_errors)
                if not raises
                else (f"{m_version.return_value}: {error}", ))
            == getattr(
                status,
                check.AChangelogStatus.errors.cache_name)["errors"])

    for provider in [m_versions, m_date]:
        assert (
            provider.call_args
            == [(), {}])
    if not raises:
        assert (
            m_sections.call_args
            == [(), {}])
    else:
        assert not m_sections.called


@pytest.mark.parametrize("raises", [None, Exception, ValueError])
@pytest.mark.parametrize("is_pending", [True, False])
async def test_changelogstatus_invalid_date(patches, raises, is_pending):
    status = check.AChangelogStatus(MagicMock(), MagicMock())
    patched = patches(
        "datetime",
        ("AChangelogStatus.date",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.date_format",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.is_pending",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_dt, m_date, m_fmt, m_pending):
        adate = AsyncMock()
        m_date.side_effect = adate
        m_pending.side_effect = AsyncMock(return_value=is_pending)
        if raises:
            m_dt.strptime.side_effect = raises("BOOM")
        if not is_pending and raises == Exception:
            with pytest.raises(Exception):
                await status.invalid_date
        else:
            assert (
                await status.invalid_date
                == (None if is_pending or not raises
                    else adate.return_value))

    assert not hasattr(
        status,
        check.AChangelogStatus.invalid_date.cache_name)
    if is_pending:
        assert not m_date.called
        assert not m_dt.strptime.called
        assert not m_fmt.called
        return
    assert (
        m_dt.strptime.call_args
        == [(adate.return_value, m_fmt.return_value), {}])


def test_changelogstatus_is_current(patches):
    status = check.AChangelogStatus(MagicMock(), "CHANGELOG")
    patched = patches(
        ("AChangelogStatus.project",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_project, m_version):
        assert (
            status.is_current
            == m_project.return_value.is_current.return_value)

    assert (
        m_project.return_value.is_current.call_args
        == [(m_version.return_value, ), {}])
    assert "is_current" in status.__dict__


@pytest.mark.parametrize("date", [None, "cabbage", "Pending"])
async def test_changelogstatus_is_pending(patches, date):
    status = check.AChangelogStatus(MagicMock(), "CHANGELOG")
    patched = patches(
        ("AChangelogStatus.date",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_date, ):
        adate = AsyncMock(return_value=date)
        m_date.side_effect = adate
        assert (
            await status.is_pending
            == (date == "Pending"))

    assert not hasattr(
        status,
        check.AChangelogStatus.date.cache_name)


@pytest.mark.parametrize("is_current", [True, False])
@pytest.mark.parametrize("is_dev", [True, False])
@pytest.mark.parametrize("is_pending", [True, False])
async def test_changelogstatus_pending_not_dev(
        patches, is_current, is_dev, is_pending):
    status = check.AChangelogStatus(MagicMock(), MagicMock())
    patched = patches(
        ("AChangelogStatus.is_current",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.is_pending",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.project",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_current, m_pending, m_project):
        m_current.return_value = is_current
        m_project.return_value.is_dev = is_dev
        m_pending.side_effect = AsyncMock(return_value=is_pending)
        assert (
            await status.pending_not_dev
            == (is_pending and (not is_dev or not is_current)))

    assert not hasattr(
        status,
        check.AChangelogStatus.pending_not_dev.cache_name)


async def test_changelogstatus_sections(patches):
    status = check.AChangelogStatus(MagicMock(), "CHANGELOG")
    patched = patches(
        "utils",
        ("AChangelogStatus.data",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")
    section_data = {f"K{i}": f"V{i}" for i in range(0, 5)}
    section_data["date"] = MagicMock()

    with patched as (m_utils, m_data):
        data = AsyncMock()
        data.return_value.items = MagicMock(return_value=section_data.items())
        m_data.side_effect = data
        assert (
            await status.sections
            == m_utils.typed.return_value)

    expected = {k: v for k, v in section_data.items() if k != "date"}
    assert (
        m_utils.typed.call_args
        == [(m_utils.typing.ChangelogChangeSectionsDict,
             expected), {}])
    assert not hasattr(
        status,
        check.AChangelogStatus.sections.cache_name)


@pytest.mark.parametrize("version", range(0, 5))
@pytest.mark.parametrize("project_version", range(0, 5))
def test_changelogstatus_version_higher_than_current(
        patches, version, project_version):
    status = check.AChangelogStatus(MagicMock(), MagicMock())
    patched = patches(
        "_version",
        ("AChangelogStatus.project",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_verlib, m_project, m_version):
        m_verlib.Version.return_value = project_version
        m_version.return_value = version
        assert (
            status.version_higher_than_current
            == (version > project_version))

    assert (
        m_verlib.Version.call_args
        == [(m_project.return_value.version.base_version, ), {}])
    assert "version_higher_than_current" not in status.__dict__


@pytest.mark.parametrize("invalid_date", [None, False, "INVALID"])
@pytest.mark.parametrize("dev_not_pending", [True, False])
@pytest.mark.parametrize("pending_not_dev", [True, False])
async def test_changelogstatus_check_date(
        patches, invalid_date, dev_not_pending, pending_not_dev):
    status = check.AChangelogStatus(MagicMock(), MagicMock())
    patched = patches(
        "tuple",
        ("AChangelogStatus.dev_not_pending",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.invalid_date",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.pending_not_dev",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")
    expected = []
    if invalid_date:
        expected.append(f"Format not recognized \"{invalid_date}\"")
    if dev_not_pending:
        expected.append("Should be set to `Pending`")
    elif pending_not_dev:
        expected.append("Should not be set to `Pending`")

    with patched as (m_tuple, m_dev, m_invalid, m_pending, m_version):
        m_invalid.side_effect = AsyncMock(return_value=invalid_date)
        m_dev.side_effect = AsyncMock(return_value=dev_not_pending)
        m_pending.side_effect = AsyncMock(return_value=pending_not_dev)
        assert (
            await status.check_date()
            == m_tuple.return_value)
        resultgen = m_tuple.call_args[0][0]
        resultlist = list(resultgen)

    assert isinstance(resultgen, types.GeneratorType)
    assert (
        resultlist
        == [f"{m_version.return_value}/date: {e}"
            for e
            in expected])


@pytest.mark.parametrize("duplicate_current", [True, False])
@pytest.mark.parametrize("version_higher_than_current", [True, False])
def test_changelogstatus_check_version(
        patches, duplicate_current, version_higher_than_current):
    status = check.AChangelogStatus(MagicMock(), MagicMock())
    patched = patches(
        "tuple",
        ("AChangelogStatus.duplicate_current",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.project",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.version",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.version_higher_than_current",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_tuple, m_dupe, m_project, m_version, m_higher):
        m_dupe.return_value = duplicate_current
        m_higher.return_value = version_higher_than_current
        assert (
            status.check_version()
            == m_tuple.return_value)
        resultgen = m_tuple.call_args[0][0]
        resultlist = list(resultgen)

    expected = []
    if duplicate_current:
        expected.append(
            "Duplicate current version file. "
            "Only `current.yaml` should exist for the current version "
            f"({m_project.return_value.version.base_version})")
    elif version_higher_than_current:
        expected.append(
            "Changelog version is higher than "
            "the current version "
            f"({m_project.return_value.version.base_version})")
    assert isinstance(resultgen, types.GeneratorType)
    assert (
        resultlist
        == [f"{m_version.return_value}: {e}"
            for e
            in expected])
    if not duplicate_current and not version_higher_than_current:
        assert not m_version.called
        assert not m_project.called


async def test_changelogstatus_check_sections(patches):
    checker = MagicMock()
    status = check.AChangelogStatus(checker, MagicMock())
    patched = patches(
        ("AChangelogStatus.project",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.sections",
         dict(new_callable=PropertyMock)),
        ("AChangelogStatus.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_project, m_sections, m_version):
        sections = AsyncMock()
        m_sections.side_effect = sections
        m_project.return_value.execute = AsyncMock()
        assert (
            await status.check_sections()
            == m_project.return_value.execute.return_value)

    assert (
        m_project.return_value.execute.call_args
        == [(status.checker.check_sections,
             m_version.return_value,
             sections.return_value), {}])


class DummyChangelogChangesChecker(check.AChangelogChangesChecker):

    @property
    def change_checkers(self):
        return super().change_checkers


def test_changeschecker_constructor():
    with pytest.raises(TypeError):
        check.AChangelogChangesChecker("SECTIONS")

    changelog = DummyChangelogChangesChecker("SECTIONS")
    assert changelog.sections == "SECTIONS"
    with pytest.raises(NotImplementedError):
        changelog.change_checkers


def test_changeschecker_max_version_for_changes_section(patches):
    changelog = DummyChangelogChangesChecker("SECTIONS")
    patched = patches(
        "_version",
        "MAX_VERSION_FOR_CHANGES_SECTION",
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_version, m_max):
        assert (
            changelog.max_version_for_changes_section
            == m_version.Version.return_value)

    assert (
        m_version.Version.call_args
        == [(m_max, ), {}])
    assert "max_version_for_changes_section" in changelog.__dict__


def test_changeschecker_check_entry(patches):
    changelog = DummyChangelogChangesChecker("SECTIONS")
    patched = patches(
        "tuple",
        ("AChangelogChangesChecker.change_checkers",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")
    version = MagicMock()
    section = MagicMock()
    entry = MagicMock()
    checkers = [MagicMock() for i in range(0, 5)]
    changelog.error_message = MagicMock()

    with patched as (m_tuple, m_checkers):
        m_checkers.return_value = checkers
        assert (
            changelog.check_entry(version, section, entry)
            == m_tuple.return_value)
        resultgen = m_tuple.call_args[0][0]
        resultlist = list(resultgen)

    assert isinstance(resultgen, types.GeneratorType)
    assert (
        resultlist
        == [changelog.error_message.format.return_value
            for c in checkers])
    assert (
        m_tuple.call_args
        == [(resultgen, ), {}])
    assert (
        changelog.error_message.format.call_args_list
        == [[(),
             dict(version=version,
                  section=section,
                  entry=entry,
                  error=c.return_value)]
            for c in checkers])
    for c in checkers:
        assert (
            c.call_args
            == [(entry.__getitem__.return_value.strip.return_value, ),
                {}])
    assert (
        entry.__getitem__.call_args
        == [("change", ), {}])
    assert (
        entry.__getitem__.return_value.strip.call_args
        == [(), {}])


@pytest.mark.parametrize("name_error", [None, False, "ERROR"])
@pytest.mark.parametrize(
    "data",
    [None,
     [],
     [f"D{i}" for i in range(0, 5)]])
def test_changeschecker_check_section(patches, name_error, data):
    changelog = DummyChangelogChangesChecker("SECTIONS")
    patched = patches(
        "itertools",
        "AChangelogChangesChecker.check_entry",
        "AChangelogChangesChecker.check_section_name",
        prefix="envoy.code.check.abstract.changelog")
    version = MagicMock()
    section = MagicMock()
    errors = [f"E{i}" for i in range(0, 5)]
    expected = []
    if name_error:
        expected.append(name_error)
    expected += errors

    with patched as (m_iter, m_entry, m_name):
        m_name.return_value = name_error
        m_iter.chain.from_iterable.return_value = errors
        assert (
            changelog.check_section(version, section, data)
            == tuple(expected))
        resultgen = m_iter.chain.from_iterable.call_args[0][0]
        resultlist = list(resultgen)

    assert isinstance(resultgen, types.GeneratorType)
    assert (
        resultlist
        == [m_entry.return_value
            for d in data or []])
    assert (
        m_entry.call_args_list
        == [[(version, section, d), {}]
            for d in data or []])
    assert (
        m_iter.chain.from_iterable.call_args
        == [(resultgen, ), {}])


def test_changeschecker_check_sections(patches):
    changelog = DummyChangelogChangesChecker("SECTIONS")
    patched = patches(
        "itertools",
        "tuple",
        "AChangelogChangesChecker.check_section",
        prefix="envoy.code.check.abstract.changelog")
    version = MagicMock()
    sections = {f"K{i}": f"V{i}" for i in range(0, 5)}

    with patched as (m_iter, m_tuple, m_check):
        assert (
            changelog.check_sections(version, sections)
            == m_tuple.return_value)
        resultgen = m_iter.chain.from_iterable.call_args[0][0]
        resultlist = list(resultgen)

    assert (
        m_tuple.call_args
        == [(m_iter.chain.from_iterable.return_value, ), {}])
    assert isinstance(resultgen, types.GeneratorType)
    assert (
        resultlist
        == [m_check.return_value for x in sections])
    assert (
        m_check.call_args_list
        == [[(version, section, data), {}]
            for section, data in sections.items()])


@pytest.mark.parametrize("version", range(0, 5))
@pytest.mark.parametrize("max_version", range(0, 5))
@pytest.mark.parametrize("section", [None, "cabbage", "changes"])
def test_changeschecker_check_section_name(
        patches, version, max_version, section):
    changelog = DummyChangelogChangesChecker("SECTIONS")
    patched = patches(
        ("AChangelogChangesChecker.max_version_for_changes_section",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.changelog")

    with patched as (m_max, ):
        m_max.return_value = max_version
        assert (
            changelog.check_section_name(version, section)
            == (None
                if (not section == "changes"
                    or version <= max_version)
                else (
                    f"{version}/changes: Invalid `changes` section "
                    "(this is no longer used)")))
