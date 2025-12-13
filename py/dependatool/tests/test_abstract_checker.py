from unittest.mock import AsyncMock, PropertyMock

import pytest

import dependatool


class DummyDependatoolChecker(dependatool.ADependatoolChecker):

    @property
    def directory_class(self):
        return super().directory_class

    @property
    def path(self):
        return super().path


def test_abstract_checker_dependatool_constructor():
    checker = DummyDependatoolChecker("path1", "path2", "path3")
    assert checker.checks == ("docker", "gomod", "npm", "pip")
    assert (
        checker.config_path
        == dependatool.abstract.checker.DEPENDABOT_CONFIG
        == ".github/dependabot.yml")
    assert checker.args.paths == ['path1', 'path2', 'path3']


@pytest.mark.parametrize("isdict", [True, False])
def test_abstract_checker_dependatool_config(patches, isdict):
    checker = DummyDependatoolChecker("path1", "path2", "path3")
    patched = patches(
        "utils",
        ("ADependatoolChecker.path", dict(new_callable=PropertyMock)),
        prefix="dependatool.abstract.checker")

    with patched as (m_utils, m_path):
        if isdict:
            m_utils.from_yaml.return_value = {}

        if isdict:
            assert checker.config == m_utils.from_yaml.return_value
        else:
            with pytest.raises(dependatool.PipConfigurationError) as e:
                checker.config

            assert (
                e.value.args[0]
                == ("Unable to parse dependabot config: "
                    f"{checker.config_path}"))

    assert (
        m_path.return_value.joinpath.call_args
        == [(checker._config, ), {}])
    assert (
        m_utils.from_yaml.call_args
        == [(m_path.return_value.joinpath.return_value,), {}])


def test_abstract_checker_dependatool_directory(patches):
    checker = DummyDependatoolChecker("path1", "path2", "path3")
    patched = patches(
        ("ADependatoolChecker.directory_class",
         dict(new_callable=PropertyMock)),
        ("ADependatoolChecker.directory_kwargs",
         dict(new_callable=PropertyMock)),
        ("ADependatoolChecker.path",
         dict(new_callable=PropertyMock)),
        prefix="dependatool.abstract.checker")

    with patched as (m_class, m_kwargs, m_path):
        m_kwargs.return_value = dict(foo="BAR")
        assert (
            checker.directory
            == m_class.return_value.return_value)

    assert (
        m_class.return_value.call_args
        == [(m_path.return_value, ), dict(foo="BAR")])
    assert "directory" in checker.__dict__


def test_abstract_checker_dependatool_directory_kwargs(patches):
    checker = DummyDependatoolChecker("path1", "path2", "path3")
    patched = patches(
        "dict",
        ("ADependatoolChecker.loop",
         dict(new_callable=PropertyMock)),
        ("ADependatoolChecker.pool",
         dict(new_callable=PropertyMock)),
        prefix="dependatool.abstract.checker")

    with patched as (m_dict, m_loop, m_pool):
        assert (
            checker.directory_kwargs
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(),
            dict(loop=m_loop.return_value,
                 pool=m_pool.return_value,
                 text_only=False)])
    assert "directory_kwargs" not in checker.__dict__


def test_abstract_checker_dependatool_ignored_dirs(patches):
    checker = DummyDependatoolChecker("path1", "path2", "path3")
    patched = patches(
        "re",
        prefix="dependatool.abstract.checker")

    with patched as (m_re, ):
        assert (
            checker.ignored_dirs
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [("|".join(dependatool.abstract.checker.IGNORED_DIRS), ), {}])
    assert "ignored_dirs" in checker.__dict__


def test_abstract_checker_dependatool_path(patches):
    checker = DummyDependatoolChecker("path1", "path2", "path3")
    patched = patches(
        ("checker.Checker.path", dict(new_callable=PropertyMock)),
        prefix="dependatool.abstract.checker")

    with patched as (m_super, ):
        assert checker.path == m_super.return_value


async def test_abstract_checker__run_check(patches):
    checker = DummyDependatoolChecker("path1", "path2", "path3")
    patched = patches(
        ("ADependatoolChecker.check_tools", dict(new_callable=PropertyMock)),
        prefix="dependatool.abstract.checker")

    with patched as (m_check_tools, ):
        mock_check = AsyncMock()
        (m_check_tools.return_value
                      .__getitem__.return_value
                      .check.side_effect) = mock_check
        assert not await checker._run_check("CHECK")

    assert (
        m_check_tools.return_value.__getitem__.call_args
        == [("CHECK", ), {}])
    assert mock_check.call_args == [(), {}]
