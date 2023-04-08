
from unittest.mock import PropertyMock

from aio.core import directory

import dependatool


def test_abstract_dependatool_path(patches):
    checker = dependatool.DependatoolChecker("path1", "path2", "path3")
    patched = patches(
        ("ADependatoolChecker.path", dict(new_callable=PropertyMock)),
        prefix="dependatool.checker")

    with patched as (m_super, ):
        assert checker.path == m_super.return_value


def test_abstract_dependatool_check_tools(patches):
    checker = dependatool.DependatoolChecker("path1", "path2", "path3")
    patched = patches(
        "DependatoolDockerCheck",
        "DependatoolPipCheck",
        prefix="dependatool.checker")

    with patched as (m_docker, m_pip):
        assert (
            checker.check_tools
            == dict(
                docker=m_docker.return_value,
                pip=m_pip.return_value))

    assert m_docker.call_args == [(checker, ), {}]
    assert m_pip.call_args == [(checker, ), {}]
    assert "check_tools" in checker.__dict__


def test_abstract_dependatool_directory_class(patches):
    checker = dependatool.DependatoolChecker("path1", "path2", "path3")
    assert checker.directory_class == directory.GitDirectory
    assert "directory_class" not in checker.__dict__
