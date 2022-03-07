
from unittest.mock import PropertyMock

import pytest

from aio.core import directory

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
    assert checker.flake8_class == check.Flake8Check
    assert "flake8_class" not in directory.__dict__
    assert checker.git_directory_class == directory.GitDirectory
    assert "git_directory_class" not in directory.__dict__
    assert checker.glint_class == check.GlintCheck
    assert "glint_class" not in directory.__dict__
    assert checker.shellcheck_class == check.ShellcheckCheck
    assert "shellcheck_class" not in directory.__dict__
    assert checker.glint_class == check.GlintCheck
    assert "glint_class" not in directory.__dict__
    assert checker.yapf_class == check.YapfCheck
    assert "yapf_class" not in directory.__dict__


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
    [check.Flake8Check,
     check.GlintCheck,
     check.ShellcheckCheck,
     check.GlintCheck,
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
