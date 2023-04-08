
from unittest.mock import PropertyMock

import dependatool


def test_abstract_dependatool_path(patches):
    checker = dependatool.Dependatool("path1", "path2", "path3")
    patched = patches(
        ("ADependatool.path", dict(new_callable=PropertyMock)),
        prefix="dependatool.abstract")

    with patched as (m_super, ):
        assert checker.path == m_super.return_value
