
from unittest.mock import MagicMock

import abstracts

from aio.api import github


@abstracts.implementer(github.AGithubRelease)
class DummyGithubRelease:
    pass


def test_abstract_release_constructor(patches):
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}
    patched = patches(
        "GithubRepoEntity.__init__",
        prefix="aio.api.github.abstract.release")

    with patched as (m_super, ):
        m_super.return_value = None
        release = DummyGithubRelease(*args, **kwargs)

    assert isinstance(release, github.abstract.base.GithubRepoEntity)
    assert (
        list(m_super.call_args)
        == [args, kwargs])
    release.repo = MagicMock()
    release.tag_name = "RELEASE_NAME"
    assert (
        str(release)
        == f"<{release.__class__.__name__} {release.repo.name}@RELEASE_NAME>")


def test_abstract_release_dunder_data(patches):
    release = DummyGithubRelease("REPO", "DATA")
    patched = patches(
        "dict",
        "utils",
        prefix="aio.api.github.abstract.release")

    with patched as (m_dict, m_utils):
        assert release.__data__ == m_dict.return_value

    assert (
        list(m_dict.call_args)
        == [(),
            dict(created_at=m_utils.dt_from_js_isoformat,
                 published_at=m_utils.dt_from_js_isoformat)])

    assert "__data__" in release.__dict__


def test_abstract_release_version(patches):
    release = DummyGithubRelease("REPO", "DATA")
    patched = patches(
        "version",
        prefix="aio.api.github.abstract.release")
    release.tag_name = "TAG_NAME"

    with patched as (m_version, ):
        assert release.version == m_version.parse.return_value

    assert (
        list(m_version.parse.call_args)
        == [("TAG_NAME", ), {}])

    assert "version" in release.__dict__
