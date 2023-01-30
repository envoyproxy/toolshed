
from unittest.mock import MagicMock, PropertyMock

import pytest

from packaging import version

import abstracts

from aio.api import github


@abstracts.implementer(github.AGithubRelease)
class DummyGithubRelease:
    pass


def test_abstract_release_constructor(iters, patches):
    args = iters(tuple, count=3)
    kwargs = iters(dict, count=3)
    patched = patches(
        "GithubRepoEntity.__init__",
        prefix="aio.api.github.abstract.release")

    with patched as (m_super, ):
        m_super.return_value = None
        release = DummyGithubRelease(*args, **kwargs)

    assert isinstance(release, github.abstract.base.GithubRepoEntity)
    assert (
        m_super.call_args
        == [args, kwargs])


def test_abstract_release_dunder_str(patches):
    release = DummyGithubRelease("REPO", "DATA")
    patched = patches(
        ("AGithubRelease.tag_name",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.release")

    with patched as (m_tag, ):
        release.repo = MagicMock()
        assert (
            str(release)
            == (f"<{release.__class__.__name__} "
                f"{release.repo.name}@{m_tag.return_value}>"))


def test_abstract_release_dunder_data(patches):
    release = DummyGithubRelease("REPO", "DATA")
    patched = patches(
        "dict",
        "utils",
        prefix="aio.api.github.abstract.release")

    with patched as (m_dict, m_utils):
        assert release.__data__ == m_dict.return_value

    assert (
        m_dict.call_args
        == [(),
            dict(created_at=m_utils.dt_from_js_isoformat,
                 published_at=m_utils.dt_from_js_isoformat)])

    assert "__data__" in release.__dict__


def test_abstract_release_tag_name(patches):
    release = DummyGithubRelease("REPO", "DATA")
    release.data = MagicMock()
    assert (
        release.tag_name
        == release.data.__getitem__.return_value)

    assert "tag_name" not in release.__dict__


@pytest.mark.parametrize("raises", [None, Exception, version.InvalidVersion])
def test_abstract_release_version(patches, raises):
    release = DummyGithubRelease("REPO", "DATA")
    patched = patches(
        "version.parse",
        ("AGithubRelease.tag_name",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.release")

    with patched as (m_version, m_tag):
        if raises:
            m_version.side_effect = raises("AN ERROR OCCURRED")
        if raises == Exception:
            with pytest.raises(Exception):
                release.version
        elif not raises:
            assert release.version == m_version.return_value
        else:
            assert not release.version

    assert (
        m_version.call_args
        == [(m_tag.return_value, ), {}])

    if raises != Exception:
        assert "version" in release.__dict__
    else:
        assert "version" not in release.__dict__
