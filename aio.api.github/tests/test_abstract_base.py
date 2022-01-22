
from unittest.mock import MagicMock, PropertyMock

import pytest

from aio.api.github.abstract import base


def test_abstract_base_githubentity_constructor():
    entity = base.GithubEntity("GITHUB", "DATA")
    assert entity._github == "GITHUB"
    assert entity.data == "DATA"

    assert entity.github == "GITHUB"
    assert "github" not in entity.__dict__
    assert entity.__data__ == {}
    assert "__data__" not in entity.__dict__


@pytest.mark.parametrize("k", ["A", "B", "C"])
@pytest.mark.parametrize("default", ["UNSET", None, True, False, "SOMESTRING"])
@pytest.mark.parametrize("mangle", ["A", "B", "C"])
def test_abstract_base_githubentity_dunder_getattr(
        patches, k, default, mangle):
    data = dict(B=MagicMock(), C=MagicMock())
    entity = base.GithubEntity("GITHUB", data)
    patched = patches(
        ("GithubEntity.__data__",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.base")
    if default == "UNSET":
        args = ()
    else:
        args = (default, )

    with patched as (m_data, ):
        if k not in data and default == "UNSET":
            with pytest.raises(AttributeError):
                entity.__getattr__(k, *args)
        else:
            result = entity.__getattr__(k, *args)

    if k in data:
        assert (
            result
            == m_data.return_value.get.return_value.return_value)
        call_args = m_data.return_value.get.call_args
        assert call_args[0][0] == k
        marker = MagicMock()
        assert call_args[0][1](marker) is marker
        assert call_args[1] == {}
        assert (
            m_data.return_value.get.return_value.call_args
            == [(data[k], ), {}])
        return
    elif default != "UNSET":
        assert result == default
    assert not m_data.called


def test_abstract_base_githubrepoentity_constructor():
    entity = base.GithubRepoEntity("REPO", "DATA")
    assert entity.repo == "REPO"
    assert entity.data == "DATA"
    assert isinstance(entity, base.GithubEntity)


def test_abstract_base_githubrepoentity_github():
    repo = MagicMock()
    entity = base.GithubRepoEntity(repo, "DATA")
    assert entity.github == repo.github
    assert "github" not in repo.__dict__
