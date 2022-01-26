
from unittest.mock import MagicMock, PropertyMock

from packaging import version

import pytest

import abstracts

from envoy.dependency.check import ADependency


@abstracts.implementer(ADependency)
class DummyDependency:
    pass


class DummyDependency2(DummyDependency):

    def __init__(self, id, metadata):
        self.id = id
        self.metadata = metadata


def test_dependency_constructor(patches):
    dependency = DummyDependency("ID", "METADATA")
    assert dependency.id == "ID"
    assert dependency.metadata == "METADATA"


@pytest.mark.parametrize("id", range(0, 3))
@pytest.mark.parametrize("other_id", range(0, 3))
def test_dependency_dunder_gt(id, other_id):
    dependency1 = DummyDependency2(id, "METADATA")
    dependency2 = DummyDependency2(other_id, "METADATA")
    assert (dependency1 > dependency2) == (id > other_id)


@pytest.mark.parametrize("id", range(0, 3))
@pytest.mark.parametrize("other_id", range(0, 3))
def test_dependency_dunder_lt(id, other_id):
    dependency1 = DummyDependency2(id, "METADATA")
    dependency2 = DummyDependency2(other_id, "METADATA")
    assert (dependency1 < dependency2) == (id < other_id)


def test_dependency_dunder_str(patches):
    dependency = DummyDependency2("ID", "METADATA")
    patched = patches(
        ("ADependency.version",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_version, ):
        assert (
            str(dependency)
            == f"ID@{m_version.return_value}")


@pytest.mark.parametrize(
    "metadata", [dict(), dict(cpe="N/A"), dict(cpe="CPE")])
def test_dependency_cpe(metadata):
    dependency = DummyDependency2("ID", metadata)
    expected = (
        metadata["cpe"]
        if "cpe" in metadata and not metadata["cpe"] == "N/A"
        else None)
    assert dependency.cpe == expected
    assert "cpe" in dependency.__dict__


@pytest.mark.parametrize("raises", [None, version.InvalidVersion, Exception])
def test_dependency_release_version(patches, raises):
    dependency = DummyDependency2("ID", "METADATA")
    patched = patches(
        "version.Version",
        ("ADependency.version", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.check.abstract.dependency")

    with patched as (m_version, m_dep_version):
        if raises:
            m_version.side_effect = raises
        if raises == Exception:
            with pytest.raises(Exception):
                dependency.release_version
        else:
            assert (
                dependency.release_version
                == (m_version.return_value if not raises else None))

    assert (
        m_version.call_args
        == [(m_dep_version.return_value, ), {}])
    if raises != Exception:
        assert "release_version" in dependency.__dict__


def test_dependency_version():
    metadata = MagicMock()
    dependency = DummyDependency2("ID", metadata)
    assert dependency.version == metadata.__getitem__.return_value
    assert "version" not in dependency.__dict__
