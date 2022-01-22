
from unittest.mock import PropertyMock

import pytest

from packaging import version

import abstracts

from envoy.dependency.cve_scan import ADependency


@abstracts.implementer(ADependency)
class DummyDependency:
    pass


def test_dependency_constructor():
    dependency = DummyDependency("ID", "METADATA")
    assert dependency.id == "ID"
    assert dependency.metadata == "METADATA"


@pytest.mark.parametrize(
    "metadata", [dict(), dict(cpe="N/A"), dict(cpe="CPE")])
def test_dependency_cpe(metadata):
    dependency = DummyDependency("ID", metadata)
    expected = (
        metadata["cpe"]
        if "cpe" in metadata and not metadata["cpe"] == "N/A"
        else None)
    assert dependency.cpe == expected
    assert "cpe" in dependency.__dict__


def test_dependency_release_date():
    metadata = dict(release_date="RELEASE_DATE")
    dependency = DummyDependency("ID", metadata)
    assert dependency.release_date == "RELEASE_DATE"
    assert "release_date" not in dependency.__dict__


@pytest.mark.parametrize("raises", [None, version.InvalidVersion, Exception])
def test_dependency_release_version(patches, raises):
    dependency = DummyDependency("ID", "METADATA")
    patched = patches(
        "version.Version",
        ("ADependency.version", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.cve_scan.abstract.dependency")

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
    metadata = dict(version="VERSION")
    dependency = DummyDependency("ID", metadata)
    assert dependency.version == "VERSION"
    assert "version" not in dependency.__dict__
