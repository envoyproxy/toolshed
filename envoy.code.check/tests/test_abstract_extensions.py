
import json
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import yaml as _yaml

from envoy.base import utils
from envoy.code import check
from envoy.code.check import exceptions


@pytest.mark.parametrize(
    "args",
    [[],
     [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{},
     {f"K{i}": f"V{i}" for i in range(0, 5)}])
@pytest.mark.parametrize("build_config", [None, "BUILD_CONFIG"])
def test_extensions_constructor(patches, args, kwargs, build_config):
    if build_config is not None:
        kwargs["extensions_build_config"] = build_config
    patched = patches(
        "abstract.ACodeCheck.__init__",
        prefix="envoy.code.check.abstract.extensions")

    with patched as (m_super, ):
        m_super.return_value = None
        if not build_config:
            with pytest.raises(KeyError):
                check.AExtensionsCheck(*args, **kwargs)
            return
        else:
            checker = check.AExtensionsCheck(*args, **kwargs)

    assert checker.extensions_build_config == build_config
    if build_config:
        del kwargs["extensions_build_config"]
    assert (
        m_super.call_args
        == [tuple(args), kwargs])


def test_extensions_all_extensions(iters, patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.builtin_extensions",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.configured_extensions",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    builtin_exts = iters(cb=lambda i: f"EXT{i}", start=2, count=8)
    configured_exts = iters(dict, cb=lambda i: (f"EXT{i}", f"EXT_DATA{i}"))

    with patched as (m_builtin, m_exts):
        m_exts.return_value = configured_exts
        m_builtin.return_value = builtin_exts
        result = checker.all_extensions

    assert (
        result
        == (set(configured_exts.keys())
            | set(builtin_exts)))
    assert "all_extensions" in checker.__dict__


@pytest.mark.parametrize("fuzzed", range(0, 3))
@pytest.mark.parametrize("robust", range(0, 3))
async def test_extensions_all_fuzzed(patches, fuzzed, robust):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.fuzzed_count",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.robust_to_downstream_count",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")

    with patched as (m_fuzzed, m_robust):
        m_fuzzed.return_value = fuzzed
        m_robust.side_effect = AsyncMock(return_value=robust)
        assert (
            await checker.all_fuzzed
            == (fuzzed == robust))

    assert "all_fuzzed" not in checker.__dict__


@pytest.mark.parametrize(
    "item",
    (("builtin_extensions", "builtin"),
     ("extension_categories", "categories"),
     ("extension_security_postures", "security_postures"),
     ("extension_status_values", "status_values")))
def test_extensions_schema(patches, item):
    prop, key = item
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.extensions_schema",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")

    with patched as (m_schema, ):
        assert (
            getattr(checker, prop)
            == m_schema.return_value.__getitem__.return_value)

    assert (
        m_schema.return_value.__getitem__.call_args
        == [(key, ), {}])

    assert prop not in checker.__dict__


def test_extensions_configured_extensions(patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "cast",
        "typing",
        "AExtensionsCheck._from_json",
        prefix="envoy.code.check.abstract.extensions")

    with patched as (m_cast, m_typing, m_json):
        assert (
            checker.configured_extensions
            == m_cast.return_value)

    assert (
        m_cast.call_args
        == [(m_typing.ConfiguredExtensionsDict,
             m_json.return_value), {}])
    assert (
        m_json.call_args
        == [("BUILD",
             m_typing.ConfiguredExtensionsDict,
             "Failed to parse extensions {path}:\n{e}",
             "Extensions parsing error: {path}:\n{e}"),
            {}])
    assert "configured_extensions" in checker.__dict__


def test_extensions_extensions_schema(patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "cast",
        "typing",
        ("AExtensionsCheck.extensions_schema_path",
         dict(new_callable=PropertyMock)),
        "AExtensionsCheck._from_yaml",
        prefix="envoy.code.check.abstract.extensions")

    with patched as (m_cast, m_typing, m_path, m_yaml):
        assert (
            checker.extensions_schema
            == m_cast.return_value)
    assert (
        m_cast.call_args
        == [(m_typing.ExtensionsSchemaDict,
             m_yaml.return_value), {}])
    assert (
        m_yaml.call_args
        == [(m_path.return_value,
             m_typing.ExtensionsSchemaDict,
             "Failed to parse extensions schema {path}:\n{e}",
             "Extensions schema parsing error: {path}:\n{e}"),
            {}])
    assert "extensions_schema" in checker.__dict__


def test_extensions_extensions_schema_path():
    directory = MagicMock()
    checker = check.AExtensionsCheck(
        directory, extensions_build_config="BUILD")
    assert (
        checker.extensions_schema_path
        == directory.path.joinpath.return_value)

    assert (
        directory.path.joinpath.call_args
        == [(check.abstract.extensions.EXTENSIONS_SCHEMA, ), {}])
    assert "extensions_schema_path" not in checker.__dict__


def test_extensions_fuzz_test_path():
    directory = MagicMock()
    checker = check.AExtensionsCheck(
        directory, extensions_build_config="BUILD")
    assert (
        checker.fuzz_test_path
        == directory.path.joinpath.return_value)

    assert (
        directory.path.joinpath.call_args
        == [(check.abstract.extensions.FUZZ_TEST_PATH, ), {}])
    assert "fuzz_test_path" not in checker.__dict__


def test_extensions_fuzzed_count(iters, patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "len",
        ("AExtensionsCheck.fuzz_test_path",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.fuzzed_filter_names_re",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    lines = iters()

    with patched as (m_len, m_path, m_re):
        (m_path.return_value.read_text
               .return_value.splitlines
               .return_value.__getitem__.return_value) = lines
        assert (
            checker.fuzzed_count
            == m_len.return_value)

    assert (
        m_len.call_args
        == [(m_re.return_value.findall.return_value, ), {}])
    assert (
        m_re.return_value.findall.call_args
        == [("".join(lines), ), {}])
    assert (
        m_path.return_value.read_text.call_args
        == [(), {}])
    assert (
        m_path.return_value.read_text.return_value.splitlines.call_args
        == [(), {}])
    assert (
        (m_path.return_value.read_text
               .return_value.splitlines
               .return_value.__getitem__.call_args)
        == [(slice(None, 50), ), {}])
    assert "fuzzed_count" not in checker.__dict__


def test_extensions_fuzzed_filter_names_re(patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.extensions")

    with patched as (m_re, ):
        assert (
            checker.fuzzed_filter_names_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [(check.abstract.extensions.FILTER_NAMES_PATTERN, ), {}])
    assert "fuzzed_filter_names_re" in checker.__dict__


async def test_extensions_metadata(iters, patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "dict",
        ("AExtensionsCheck.metadata_core",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.metadata_contrib",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    core = iters(dict, cb=lambda i: (f"KCORE{i}", f"VCORE{i}"))
    contrib = iters(dict, cb=lambda i: (f"KCONTRIB{i}", f"VCONTRIB{i}"))

    with patched as (m_dict, m_core, m_contrib):
        m_core.side_effect = AsyncMock(return_value=core)
        m_contrib.side_effect = AsyncMock(return_value=contrib)
        assert (
            await checker.metadata
            == m_dict.return_value
            == getattr(
                checker,
                check.AExtensionsCheck.metadata.cache_name)["metadata"])

    assert (
        m_dict.call_args
        == [(), dict(**core, **contrib)])


@pytest.mark.parametrize("mtype", ["core", "contrib"])
async def test_extensions_metadata_data(patches, mtype):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        (f"AExtensionsCheck.metadata_{mtype}_path",
         dict(new_callable=PropertyMock)),
        "AExtensionsCheck._metadata",
        prefix="envoy.code.check.abstract.extensions")

    with patched as (m_path, m_meta):
        assert (
            await getattr(checker, f"metadata_{mtype}")
            == m_meta.return_value)

    assert not hasattr(
        checker,
        getattr(
            check.AExtensionsCheck,
            f"metadata_{mtype}").cache_name)


def test_extensions_metadata_contrib_path():
    directory = MagicMock()
    checker = check.AExtensionsCheck(
        directory, extensions_build_config="BUILD")
    assert (
        checker.metadata_contrib_path
        == directory.path.joinpath.return_value)

    assert (
        directory.path.joinpath.call_args
        == [(check.abstract.extensions.CONTRIB_METADATA_PATH, ), {}])
    assert "metadata_contrib_path" not in checker.__dict__


def test_extensions_metadata_core_path():
    directory = MagicMock()
    checker = check.AExtensionsCheck(
        directory, extensions_build_config="BUILD")
    assert (
        checker.metadata_core_path
        == directory.path.joinpath.return_value)

    assert (
        directory.path.joinpath.call_args
        == [(check.abstract.extensions.METADATA_PATH, ), {}])
    assert "metadata_core_path" not in checker.__dict__


async def test_extensions_metadata_errors(iters, patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.metadata",
         dict(new_callable=PropertyMock)),
        "AExtensionsCheck.check_metadata",
        prefix="envoy.code.check.abstract.extensions")
    meta = iters()

    with patched as (m_meta, m_check):
        ameta = AsyncMock(return_value=meta)
        m_meta.side_effect = ameta
        assert (
            await checker.metadata_errors
            == {k: m_check.return_value
                for k in meta})

    assert (
        m_check.call_args_list
        == [[(k, ), {}] for k in meta])
    assert "metadata_errors" not in checker.__dict__


async def test_extensions_metadata_missing(iters, patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.all_extensions",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.metadata",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    all_ext = iters(set, cb=lambda i: f"K{i}", count=10)
    meta = {f"K{i}": f"V{i}" for i in range(0, 10) if i % 2}
    expected = set([f"K{i}" for i in range(0, 10) if not i % 2])

    with patched as (m_all, m_meta):
        ameta = AsyncMock(return_value=meta)
        m_meta.side_effect = ameta
        m_all.return_value = all_ext
        assert (
            await checker.metadata_missing
            == expected)

    assert "metadata_missing" not in checker.__dict__


async def test_extensions_metadata_only(iters, patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.all_extensions",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.metadata",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.metadata_only_extensions",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    all_ext = set([f"K{i}" for i in range(0, 20) if i % 2])
    meta = iters(dict, count=20)
    meta_only = iters(set, cb=lambda i: f"K{i}", start=7, count=6)
    expected = set([
        f"K{i}"
        for i
        in range(0, 20)
        if (not i % 2 and i not in range(7, 13))])

    with patched as (m_all, m_meta, m_meta_only):
        ameta = AsyncMock(return_value=meta)
        m_meta.side_effect = ameta
        m_all.return_value = all_ext
        m_meta_only.return_value = meta_only

        assert (
            await checker.metadata_only
            == expected)

    assert "metadata_only" not in checker.__dict__


def test_extensions_metadata_only_extensions(patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "set",
        prefix="envoy.code.check.abstract.extensions")

    with patched as (m_set, ):
        assert (
            checker.metadata_only_extensions
            == m_set.return_value)

    assert (
        m_set.call_args
        == [(check.abstract.extensions.METADATA_ONLY_EXTENSIONS, ), {}])
    assert "metadata_only_extensions" not in checker.__dict__


async def test_extensions_registration_errors(patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.metadata_missing",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.metadata_only",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    missing = [f"MISS{i}" for i in reversed(range(0, 10))]
    only = [f"ONLY{i}" for i in reversed(range(0, 10))]

    with patched as (m_missing, m_only):
        amissing = AsyncMock(return_value=missing)
        m_missing.side_effect = amissing
        aonly = AsyncMock(return_value=only)
        m_only.side_effect = aonly
        assert (
            await checker.registration_errors
            == [*[f"Metadata for unused extension found: {extension}"
                  for extension
                  in sorted(only)],
                *[f"Metadata missing for extension: {extension}"
                  for extension
                  in sorted(missing)]])

    assert "registration_errors" not in checker.__dict__


async def test_extensions_robust_to_downstream_count(patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.metadata",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    metadata = dict(
        foo0=dict(security_posture="robust_to_untrusted_downstream"),
        bar0=dict(security_posture="robust_to_untrusted_downstream"),
        baz0=dict(security_posture="robust_to_untrusted_downstream"),
        foo1=dict(security_posture="NOT_robust_to_untrusted_downstream"),
        bar1=dict(security_posture="NOT_robust_to_untrusted_downstream"),
        baz1=dict(security_posture="NOT_robust_to_untrusted_downstream"),
        foo0network=dict(
            security_posture="robust_to_untrusted_downstream"),
        bar0network=dict(
            security_posture="robust_to_untrusted_downstream"),
        baz0network=dict(
            security_posture="robust_to_untrusted_downstream"),
        foo1network=dict(
            security_posture="NOT_robust_to_untrusted_downstream"),
        bar1network=dict(
            security_posture="NOT_robust_to_untrusted_downstream"),
        baz1network=dict(
            security_posture="NOT_robust_to_untrusted_downstream"))

    with patched as (m_meta, ):
        meta = AsyncMock(return_value=metadata)
        m_meta.side_effect = meta
        assert await checker.robust_to_downstream_count == 3

    assert "robust_to_downstream_count" not in checker.__dict__


async def test_extensions_check_metadata(iters, patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "AExtensionsCheck._check_metadata_categories",
        "AExtensionsCheck._check_metadata_security_posture",
        "AExtensionsCheck._check_metadata_status",
        prefix="envoy.code.check.abstract.extensions")
    cats = iters(cb=lambda i: f"CAT{i}")
    sec = iters(tuple, cb=lambda i: f"SEC{i}")
    status = (f"STATUS{i}" for i in range(0, 5))
    extension = MagicMock()

    with patched as (m_cats, m_sec, m_status):
        m_cats.return_value = cats
        m_sec.return_value = sec
        m_status.return_value = status
        assert (
            await checker.check_metadata(extension)
            == (*cats,
                *sec,
                *(f"STATUS{i}" for i in range(0, 5))))

    for source in m_cats, m_sec, m_status:
        assert (
            getattr(source, "call_args")
            == [(extension, ), {}])


@pytest.mark.parametrize(
    "ext_cats",
    [(),
     ("A", "B", "C", "D"),
     ("A", "B"),
     ("B", "C", "D")])
@pytest.mark.parametrize(
    "all_cats",
    [("A", "B", "C", "D"),
     ("A", "B"),
     ("B", "C", "D")])
async def test_extensions__check_metadata_categories(
        patches, ext_cats, all_cats):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.extension_categories",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.metadata",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    if not ext_cats:
        expected = (
            "Missing extension category for EXTENSION. "
            "Please make sure the target is an envoy_cc_extension "
            "and category is set", )
    else:
        wrong_cats = [cat for cat in ext_cats if cat not in all_cats]
        if wrong_cats:
            expected = tuple(
                f"Unknown extension category for EXTENSION: {cat}. "
                "Please add it to tools/extensions/extensions_check.py"
                for cat
                in wrong_cats)
        else:
            expected = ()

    with patched as (m_cats, m_meta):
        meta = AsyncMock()
        m_meta.side_effect = meta
        m_cats.return_value = all_cats
        (meta.return_value.__getitem__
             .return_value.get.return_value) = ext_cats
        assert (
            await checker._check_metadata_categories("EXTENSION")
            == expected)

    assert (
        list(meta.return_value.__getitem__.call_args)
        == [('EXTENSION',), {}])
    assert (
        list(meta.return_value.__getitem__.return_value.get.call_args)
        == [('categories', ()), {}])


@pytest.mark.parametrize("sec_posture", [None, "A", "Z"])
async def test_extensions__check_metadata_security_posture(
        patches, sec_posture):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.extension_security_postures",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.metadata",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    postures = ["A", "B", "C"]

    if not sec_posture:
        expected = (
            "Missing security posture for EXTENSION. "
            "Please make sure the target is an "
            "envoy_cc_extension and security_posture is set", )
    elif sec_posture not in postures:
        expected = (f"Unknown security posture for EXTENSION: {sec_posture}", )
    else:
        expected = ()

    with patched as (m_sec, m_meta):
        meta = AsyncMock()
        m_meta.side_effect = meta
        m_sec.return_value = postures
        (meta.return_value.__getitem__
             .return_value.__getitem__.return_value) = sec_posture
        assert (
            await checker._check_metadata_security_posture("EXTENSION")
            == expected)

    assert (
        list(meta.return_value.__getitem__.call_args)
        == [('EXTENSION',), {}])
    assert (
        list(meta.return_value.__getitem__
                 .return_value.__getitem__.call_args)
        == [('security_posture',), {}])


@pytest.mark.parametrize("status", ["A", "Z"])
async def test_extensions__check_metadata_status(patches, status):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.extension_status_values",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.metadata",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    status_values = ["A", "B", "C"]

    with patched as (m_status, m_meta):
        meta = AsyncMock()
        m_meta.side_effect = meta
        m_status.return_value = status_values
        (meta.return_value.__getitem__
             .return_value.__getitem__.return_value) = status
        assert (
            await checker._check_metadata_status("EXTENSION")
            == ((f'Unknown status for EXTENSION: {status}', )
                if status not in status_values
                else ()))

    assert (
        list(meta.return_value.__getitem__.call_args)
        == [('EXTENSION',), {}])
    assert (
        list(meta.return_value.__getitem__
                 .return_value.__getitem__.call_args)
        == [('status',), {}])


@pytest.mark.parametrize(
    "raises",
    [None,
     BaseException,
     FileNotFoundError,
     utils.exceptions.TypeCastingError,
     json.JSONDecodeError])
def test_extensions__from_json(patches, raises):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "logger",
        "typing",
        "utils.from_json",
        prefix="envoy.code.check.abstract.extensions")
    config_error = raises in [FileNotFoundError, json.JSONDecodeError]
    no_error = (not raises or raises == utils.exceptions.TypeCastingError)
    path = MagicMock()
    type = MagicMock()
    err_message = MagicMock()
    warn_message = MagicMock()

    with patched as (m_log, m_typing, m_json):
        if raises:
            error = raises("AN ERROR OCCURRED", "X", 23)
            error.value = "ERROR_VALUE"
            m_json.side_effect = error
        if no_error:
            assert (
                checker._from_json(path, type, err_message, warn_message)
                == (m_json.return_value
                    if not raises
                    else error.value))
        elif config_error:
            ConfigError = check.exceptions.ExtensionsConfigurationError
            with pytest.raises(ConfigError) as e:
                checker._from_json(path, type, err_message, warn_message)
        else:
            with pytest.raises(raises) as e:
                checker._from_json(path, type, err_message, warn_message)

    assert (
        m_json.call_args
        == [(path, type), {}])
    if raises == utils.exceptions.TypeCastingError:
        assert (
            m_log.warning.call_args
            == [(warn_message.format.return_value, ), {}])
        assert (
            warn_message.format.call_args
            == [(), dict(path=path, e=error)])
        return
    assert not m_log.warning.called
    assert not warn_message.format.called
    if config_error:
        assert (
            e.value.args[0]
            == err_message.format.return_value)
        assert (
            err_message.format.call_args
            == [(), dict(path=path, e=error)])
        return
    assert not err_message.format.called


@pytest.mark.parametrize(
    "raises",
    [None,
     BaseException,
     FileNotFoundError,
     utils.exceptions.TypeCastingError,
     _yaml.reader.ReaderError])
def test_extensions__from_yaml(patches, raises):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "logger",
        "typing",
        "utils.from_yaml",
        prefix="envoy.code.check.abstract.extensions")
    config_error = raises in [FileNotFoundError, _yaml.reader.ReaderError]
    no_error = (not raises or raises == utils.exceptions.TypeCastingError)
    path = MagicMock()
    type = MagicMock()
    err_message = MagicMock()
    warn_message = MagicMock()

    with patched as (m_log, m_typing, m_yaml):
        if raises:
            error = raises("AN ERROR OCCURRED", "X", 23, "Y", "Z")
            error.value = "ERROR_VALUE"
            m_yaml.side_effect = error
        if no_error:
            assert (
                checker._from_yaml(path, type, err_message, warn_message)
                == (m_yaml.return_value
                    if not raises
                    else error.value))
        elif config_error:
            ConfigError = check.exceptions.ExtensionsConfigurationError
            with pytest.raises(ConfigError) as e:
                checker._from_yaml(path, type, err_message, warn_message)
        else:
            with pytest.raises(raises) as e:
                checker._from_yaml(path, type, err_message, warn_message)

    assert (
        m_yaml.call_args
        == [(path, type), {}])
    if raises == utils.exceptions.TypeCastingError:
        assert (
            m_log.warning.call_args
            == [(warn_message.format.return_value, ), {}])
        assert (
            warn_message.format.call_args
            == [(), dict(path=path, e=error)])
        return
    assert not m_log.warning.called
    assert not warn_message.format.called
    if config_error:
        assert (
            e.value.args[0]
            == err_message.format.return_value)
        assert (
            err_message.format.call_args
            == [(), dict(path=path, e=error)])
        return
    assert not err_message.format.called


@pytest.mark.parametrize(
    "raises",
    [None,
     BaseException,
     utils.exceptions.TypeCastingError,
     FileNotFoundError])
async def test_extensions__metadata(patches, raises):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "typing",
        "utils.from_yaml",
        ("AExtensionsCheck.execute",
         dict(new_callable=AsyncMock)),
        prefix="envoy.code.check.abstract.extensions")
    path = MagicMock()

    with patched as (m_typing, m_yaml, m_exec):
        if raises:
            error = raises("AN ERROR OCCURRED")
            m_exec.side_effect = error

        if raises == BaseException:
            with pytest.raises(raises):
                await checker._metadata(path)
        elif raises:
            with pytest.raises(exceptions.ExtensionsConfigurationError) as e:
                await checker._metadata(path)
        else:
            assert (
                await checker._metadata(path)
                == m_exec.return_value)

    assert (
        m_exec.call_args
        == [(m_yaml,
             path,
             m_typing.ExtensionsMetadataDict), {}])
    if raises and not raises == BaseException:
        assert (
            e.value.args[0]
            == ("Failed to parse extensions metadata "
                f"({path}): {error}"))
