
from unittest.mock import PropertyMock

import pytest

from aio.core import directory

from envoy.base import utils
from envoy.code import check


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_checker_constructor(patches, args, kwargs):
    patched = patches(
        "check.ACodeChecker.__init__",
        prefix="envoy.code.check.checker")

    with patched as (m_super, ):
        m_super.return_value = None
        checker = check.CodeChecker(*args, **kwargs)

    assert isinstance(checker, check.ACodeChecker)
    assert (
        m_super.call_args
        == [tuple(args), kwargs])

    assert checker.fs_directory_class == directory.Directory
    assert "fs_directory_class" not in directory.__dict__
    assert checker.extensions_class == check.ExtensionsCheck
    assert "extensions_class" not in directory.__dict__
    assert checker.flake8_class == check.Flake8Check
    assert "flake8_class" not in directory.__dict__
    assert checker.git_directory_class == directory.GitDirectory
    assert "git_directory_class" not in directory.__dict__
    assert checker.glint_class == check.GlintCheck
    assert "glint_class" not in directory.__dict__
    assert checker.project_class == utils.Project
    assert "project_class" not in directory.__dict__
    assert checker.runtime_guards_class == check.RuntimeGuardsCheck
    assert "runtime_guards_class" not in directory.__dict__
    assert checker.shellcheck_class == check.ShellcheckCheck
    assert "shellcheck_class" not in directory.__dict__
    assert checker.yapf_class == check.YapfCheck
    assert "yapf_class" not in directory.__dict__
    assert checker.changelog_class == check.ChangelogCheck
    assert "changelog_class" not in directory.__dict__


def test_checker_path(patches):
    checker = check.CodeChecker()
    patched = patches(
        ("check.ACodeChecker.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.checker")

    with patched as (m_super, ):
        assert (
            checker.path
            == m_super.return_value)


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
@pytest.mark.parametrize(
    "sub",
    [check.ChangelogChangesChecker,
     check.ChangelogCheck,
     check.ChangelogStatus,
     check.ExtensionsCheck,
     check.Flake8Check,
     check.GlintCheck,
     check.ShellcheckCheck,
     check.YapfCheck])
def test_checker_constructors(patches, args, kwargs, sub):
    patched = patches(
        f"check.A{sub.__name__}.__init__",
        prefix="envoy.code.check.checker")

    with patched as (m_super, ):
        m_super.return_value = None
        sub(*args, **kwargs)

    assert (
        m_super.call_args
        == [tuple(args), kwargs])


def test_changelog_check_constructor(patches):
    patched = patches(
        "check.AChangelogCheck.__init__",
        prefix="envoy.code.check.checker")

    with patched as (m_super, ):
        m_super.return_value = None
        checker = check.ChangelogCheck("PROJECT", "DIRECTORY")

    assert (
        m_super.call_args
        == [("PROJECT", "DIRECTORY"), {}])
    assert checker.changes_checker_class == check.ChangelogChangesChecker
    assert checker.changelog_status_class == check.ChangelogStatus


def test_changeschecker_checkers(patches):
    checker = check.ChangelogChangesChecker("SECTIONS")
    patched = patches(
        "BackticksCheck",
        "PunctuationCheck",
        "ReflinksCheck",
        prefix="envoy.code.check.checker")

    with patched as (m_bticks, m_punc, m_refs):
        assert (
            checker.change_checkers
            == (m_bticks.return_value,
                m_punc.return_value,
                m_refs.return_value))

    for _check in m_bticks, m_punc, m_refs:
        assert (
            _check.call_args
            == [(), {}])
    assert "change_checkers" in checker.__dict__
