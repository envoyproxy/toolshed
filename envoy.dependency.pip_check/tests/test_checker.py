
from unittest.mock import PropertyMock

from envoy.dependency import pip_check


def test_abstract_pip_checker_path(patches):
    checker = pip_check.PipChecker("path1", "path2", "path3")
    patched = patches(
        ("APipChecker.path", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.pip_check.abstract")

    with patched as (m_super, ):
        assert checker.path == m_super.return_value
