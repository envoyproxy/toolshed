
import itertools
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from envoy.base.utils import abstract, interface, typing


@abstracts.implementer(interface.IInventories)
class DummyInventories(abstract.AInventories):
    pass


def test_abstract_inventories_constructor():
    inventories = DummyInventories("PROJECT")
    assert inventories.project == "PROJECT"


def test_abstract_inventories_dunder_contains(patches):
    inventories = DummyInventories("PROJECT")
    patched = patches(
        ("AInventories.inventories",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.inventory")

    with patched as (m_inv, ):
        assert (
            inventories.__contains__("KEY")
            == m_inv.return_value.__contains__.return_value)

    assert (
        m_inv.return_value.__contains__.call_args
        == [("KEY",), {}])


def test_abstract_inventories_dunder_getitem(patches):
    inventories = DummyInventories("PROJECT")
    patched = patches(
        ("AInventories.inventories",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.inventory")

    with patched as (m_inv, ):
        assert (
            inventories.__getitem__("KEY")
            == m_inv.return_value.__getitem__.return_value)

    assert (
        m_inv.return_value.__getitem__.call_args
        == [("KEY",), {}])


def test_abstract_inventories_dunder_iter(patches):
    inventories = DummyInventories("PROJECT")
    patched = patches(
        ("AInventories.inventories",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.inventory")
    invs = [f"INV{c}" for c in range(0, 5)]

    with patched as (m_invs, ):
        m_invs.return_value = invs
        result = inventories.__iter__()
        assert isinstance(result, types.GeneratorType)
        assert (
            list(result)
            == invs)


def test_abstract_inventories_inventories(patches):
    inventories = DummyInventories("PROJECT")
    patched = patches(
        "_version",
        ("AInventories.paths",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.inventory")
    paths = [MagicMock() for p in range(0, 5)]

    with patched as (m_version, m_paths):
        m_paths.return_value = paths
        assert (
            inventories.inventories
            == {m_version.Version.return_value: p
                for p
                in paths})

    assert (
        m_version.Version.call_args_list
        == [[(p.parent.name.__getitem__.return_value,),
             {}] for p in paths])
    for p in paths:
        assert (
            p.parent.name.__getitem__.call_args
            == [(slice(1, None), ), {}])
    assert "inventories" in inventories.__dict__


def test_abstract_inventories_paths():
    project = MagicMock()
    inventories = DummyInventories(project)
    assert (
        inventories.paths
        == project.path.glob.return_value)
    assert (
        project.path.glob.call_args
        == [(abstract.project.inventory.INVENTORY_PATH_GLOB, ), {}])
    assert "paths" not in inventories.__dict__


async def test_abstract_inventories_syncable(patches):
    releases = []
    for i in range(0, 10):
        release = MagicMock()
        release.version = i
        releases.append(release)

    async def repo_releases():
        for release in releases:
            yield release

    project = MagicMock()
    project.repo.releases.side_effect = repo_releases
    inventories = DummyInventories(project)
    patched = patches(
        "_version",
        "dict",
        "max",
        "utils",
        ("AInventories.versions_path",
         dict(new_callable=PropertyMock)),
        "AInventories.should_sync",
        prefix="envoy.base.utils.abstract.project.inventory")

    with patched as (m_version, m_dict, m_max, m_utils, m_path, m_should):
        m_should.side_effect = lambda x, y: y % 2
        assert (
            await inventories.syncable
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(), {}])
    assert (
        project.repo.releases.call_args
        == [(), {}])
    assert (
        m_utils.minor_version_for.call_args_list
        == [[(r.version, ), {}]
            for r in releases])
    assert (
        m_should.call_args_list
        == [[(m_utils.minor_version_for.return_value,
              r.version),
             {}]
            for r in releases])
    assert (
        m_dict.return_value.__setitem__.call_args_list
        == [[(m_utils.minor_version_for.return_value,
              m_max.return_value, ),
             {}]
            for r in releases
            if r.version % 2])
    assert (
        m_max.call_args_list
        == [[(r.version, m_dict.return_value.get.return_value), {}]
            for r in releases
            if r.version % 2])
    assert (
        m_dict.return_value.get.call_args_list
        == [[(m_utils.minor_version_for.return_value,
              m_version.Version.return_value), {}]
            for r in releases
            if r.version % 2])
    assert (
        m_version.Version.call_args_list
        == [[("0.0", ), {}]
            for r in releases
            if r.version % 2])
    assert not hasattr(
        inventories,
        abstract.AInventories.syncable.cache_name)


def test_abstract_inventories_versions(patches):
    inventories = DummyInventories("PROJECT")
    patched = patches(
        "_version",
        "utils",
        ("AInventories.versions_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.inventory")
    versions = {f"K{v}": f"V{v}" for v in range(0, 5)}

    with patched as (m_version, m_utils, m_path):
        m_utils.from_yaml.return_value.items.return_value = versions.items()
        assert (
            inventories.versions
            == {m_version.Version.return_value: m_version.Version.return_value
                for v
                in versions})

    assert (
        m_version.Version.call_args_list
        == [[(v,), {}]
            for v
            in itertools.chain.from_iterable(versions.items())])
    assert (
        m_utils.from_yaml.call_args
        == [(m_path.return_value, typing.VersionConfigDict), {}])
    assert "versions" in inventories.__dict__


def test_abstract_inventories_versions_path():
    project = MagicMock()
    inventories = DummyInventories(project)
    assert (
        inventories.versions_path
        == project.path.joinpath.return_value)
    assert (
        project.path.joinpath.call_args
        == [(abstract.project.inventory.INVENTORY_VERSIONS_PATH, ), {}])
    assert "versions_path" not in inventories.__dict__


def test_abstract_inventories_yaml(patches):
    inventories = DummyInventories("PROJECT")
    patched = patches(
        "_yaml",
        "_version",
        "AInventories.yaml_version_presenter",
        prefix="envoy.base.utils.abstract.project.inventory")

    with patched as (m_yaml, m_version, m_pres):
        assert (
            inventories.yaml
            == m_yaml)

    assert (
        m_yaml.add_representer.call_args
        == [(m_version.Version, m_pres), {}])
    assert "yaml" in inventories.__dict__


@pytest.mark.parametrize(
    "items",
    [{},
     {i: True for i in range(0, 10)},
     {i: False for i in range(0, 10)},
     {i: (i % 2) for i in range(0, 10)}])
@pytest.mark.parametrize("sync", [True, False])
def test_abstract_inventories_changes(patches, items, sync):
    inventories = DummyInventories("PROJECT")
    patched = patches(
        "set",
        "INVENTORY_VERSIONS_PATH",
        "AInventories.inventory_url",
        "AInventories.rel_inventory_path",
        prefix="envoy.base.utils.abstract.project.inventory")
    change = MagicMock()
    change.__contains__.return_value = sync
    change.__getitem__.return_value.get.return_value = items

    with patched as (m_set, m_path, m_url, m_rel):
        assert (
            inventories.changes_for_commit(change)
            == m_set.return_value)

    assert (
        m_set.call_args
        == [(), {}])
    assert (
        change.__contains__.call_args
        == [("sync", ), {}])
    if not sync:
        assert not change.__getitem__.called
        assert not m_rel.called
        assert not m_set.return_value.add.called
        return
    assert (
        change.__getitem__.call_args
        == [("sync", ), {}])
    assert (
        change.__getitem__.return_value.get.call_args
        == [("inventory", {}), {}])
    if not items:
        assert not m_rel.called
        assert not m_set.return_value.add.called
        return
    assert (
        m_set.return_value.add.call_args_list
        == ([[(m_rel.return_value, ), {}]
            for k, v in items.items()
            if v]
            + [[(m_path, ), {}]]))
    assert (
        m_rel.call_args_list
        == [[(k, ), {}]
            for k, v
            in items.items() if v])


@pytest.mark.parametrize("response", [None, 404, "OTHER"])
async def test_abstract_inventories_fetch(patches, response):
    project = MagicMock()
    inventories = DummyInventories(project)
    patched = patches(
        "AInventories.inventory_url",
        prefix="envoy.base.utils.abstract.project.inventory")
    version = MagicMock()
    get = AsyncMock()
    read = AsyncMock()
    get.return_value.read.side_effect = read
    get.return_value.status = response
    project.session.get.side_effect = get

    with patched as (m_url, ):
        assert (
            await inventories.fetch(version)
            == (read.return_value
                if response != 404
                else None))

    assert (
        get.call_args
        == [(m_url.return_value, ), {}])
    assert (
        m_url.call_args
        == [(version, ), {}])
    if response == 404:
        assert not read.called
    else:
        assert (
            read.call_args
            == [(), {}])


def test_abstract_inventories_inventory_path(patches):
    project = MagicMock()
    inventories = DummyInventories(project)
    patched = patches(
        "AInventories.rel_inventory_path",
        prefix="envoy.base.utils.abstract.project.inventory")
    version = MagicMock()

    with patched as (m_path, ):
        assert (
            inventories.inventory_path(version)
            == project.path.joinpath.return_value)
    assert (
        project.path.joinpath.call_args
        == [(m_path.return_value, ), {}])
    assert (
        m_path.call_args
        == [(version, ), {}])


def test_abstract_inventories_inventory_url(patches):
    project = MagicMock()
    inventories = DummyInventories(project)
    patched = patches(
        "INVENTORY_URL_FMT",
        prefix="envoy.base.utils.abstract.project.inventory")
    version = MagicMock()

    with patched as (m_tpl, ):
        assert (
            inventories.inventory_url(version)
            == m_tpl.format.return_value)
    assert (
        m_tpl.format.call_args
        == [(), dict(version=version.base_version)])


def test_abstract_inventories_rel_inventory_path(patches):
    inventories = DummyInventories("PROJECT")
    patched = patches(
        "utils",
        "INVENTORY_PATH_FMT",
        prefix="envoy.base.utils.abstract.project.inventory")
    version = MagicMock()

    with patched as (m_utils, m_fmt):
        assert (
            inventories.rel_inventory_path(version)
            == m_fmt.format.return_value)

    assert (
        m_fmt.format.call_args
        == [(), dict(minor_version=m_utils.minor_version_for.return_value)])
    assert (
        m_utils.minor_version_for.call_args
        == [(version, ), {}])


@pytest.mark.parametrize("version", range(0, 5))
@pytest.mark.parametrize("project_version", range(0, 5))
@pytest.mark.parametrize("first_stable", range(0, 5))
@pytest.mark.parametrize("existing", range(0, 5))
def test_abstract_inventories_should_sync(
        patches, version, project_version, first_stable, existing):
    project = MagicMock()
    project.version = project_version
    project.stable_versions.__getitem__.return_value = first_stable
    inventories = DummyInventories(project)
    patched = patches(
        ("AInventories.versions",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.inventory")
    minor_version = MagicMock()
    should_sync = True
    if version >= project_version:
        should_sync = False
    if version < first_stable:
        should_sync = False
    if existing >= version:
        should_sync = False

    with patched as (m_versions, ):
        m_versions.return_value.get.return_value = existing
        assert inventories.should_sync(minor_version, version) == should_sync


def test_abstract_inventories_write_inventory(patches):
    inventories = DummyInventories("PROJECT")
    patched = patches(
        "AInventories.inventory_path",
        prefix="envoy.base.utils.abstract.project.inventory")
    version = MagicMock()
    content = MagicMock()

    with patched as (m_path, ):
        assert not inventories.write_inventory(version, content)

    assert (
        m_path.call_args
        == [(version, ), {}])
    assert (
        m_path.return_value.parent.mkdir.call_args
        == [(), dict(exist_ok=True, parents=True)])
    assert (
        m_path.return_value.write_bytes.call_args
        == [(content, ), {}])


@pytest.mark.parametrize(
    "fetch",
    [(lambda x: True),
     (lambda x: False),
     (lambda x: int(x[1:]) % 2)])
async def test_abstract_inventories_sync(patches, fetch):
    inventories = DummyInventories("PROJECT")
    patched = patches(
        ("AInventories.syncable",
         dict(new_callable=PropertyMock)),
        "AInventories.fetch",
        "AInventories.write_inventory",
        "AInventories.write_versions",
        prefix="envoy.base.utils.abstract.project.inventory")
    syncable = {f"K{s}": f"V{s}" for s in range(0, 10)}

    with patched as (m_syncable, m_fetch, m_write_inv, m_write_ver):
        sync = AsyncMock()
        m_syncable.side_effect = sync
        sync.return_value.items = MagicMock(return_value=syncable.items())
        m_fetch.side_effect = fetch
        assert (
            await inventories.sync()
            == {v: fetch(v)
                for v
                in syncable.values()})

    assert (
        m_fetch.call_args_list
        == [[(v, ), {}] for v in syncable.values()])
    assert (
        m_write_inv.call_args_list
        == [[(v, True), {}]
            for v
            in syncable.values()
            if fetch(v)])
    versions = {
        m: v
        for m, v
        in syncable.items()
        if fetch(v)}
    if versions:
        assert (
            m_write_ver.call_args
            == [(versions, ), {}])
    else:
        assert not m_write_ver.called


def test_abstract_inventories_write_versions(patches):
    inventories = DummyInventories("PROJECT")
    patched = patches(
        ("AInventories.versions",
         dict(new_callable=PropertyMock)),
        ("AInventories.versions_path",
         dict(new_callable=PropertyMock)),
        ("AInventories.yaml",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract.project.inventory")
    versions = MagicMock()

    with patched as (m_versions, m_path, m_yaml):
        assert not inventories.write_versions(versions)

    assert (
        m_versions.return_value.copy.call_args
        == [(), {}])
    assert (
        m_versions.return_value.copy.return_value.update.call_args
        == [(versions, ), {}])
    assert (
        m_path.return_value.write_text.call_args
        == [(m_yaml.return_value.dump.return_value, ), {}])
    assert (
        m_yaml.return_value.dump.call_args
        == [(m_versions.return_value.copy.return_value, ),
            dict(default_flow_style=False,
                 default_style=None,
                 sort_keys=False)])


@pytest.mark.parametrize("count", range(0, 3))
def test_abstract_inventories_yaml_version_presenter(patches, count):
    inventories = DummyInventories("PROJECT")
    patched = patches(
        "str",
        prefix="envoy.base.utils.abstract.project.inventory")
    dumper = MagicMock()
    data = MagicMock()

    with patched as (m_str, ):
        m_str.return_value.count.return_value = count
        assert (
            inventories.yaml_version_presenter(dumper, data)
            == dumper.represent_scalar.return_value)

    assert (
        dumper.represent_scalar.call_args
        == [("tag:yaml.org,2002:str",
             m_str.return_value),
            dict(style='"' if count == 1 else None)])
    assert (
        m_str.call_args
        == [(data, ), {}])
