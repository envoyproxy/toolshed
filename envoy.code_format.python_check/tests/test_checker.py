
from unittest.mock import PropertyMock

from envoy.code_format import python_check


def test_abstract_python_checker_path(patches):
    checker = python_check.PythonChecker("path1", "path2", "path3")
    patched = patches(
        ("APythonChecker.path", dict(new_callable=PropertyMock)),
        prefix="envoy.code_format.python_check.abstract")

    with patched as (m_super, ):
        assert checker.path == m_super.return_value
