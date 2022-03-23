
import types
from unittest.mock import MagicMock, PropertyMock

import pytest

from envoy.base import utils
from envoy.code import check


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


def test_extensions_all_extensions(patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.builtin_extensions",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.configured_extensions",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    builtin_exts = [f"EXT{i}" for i in range(2, 10)]
    configured_exts = {f"EXT{i}": f"EXT_DATA{i}" for i in range(0, 5)}

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
def test_extensions_all_fuzzed(patches, fuzzed, robust):
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
        m_robust.return_value = robust
        assert (
            checker.all_fuzzed
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
        "json",
        "pathlib",
        "typing",
        "utils",
        prefix="envoy.code.check.abstract.extensions")

    with patched as (m_json, m_plib, m_typing, m_utils):
        assert (
            checker.configured_extensions
            == m_utils.typed.return_value)

    assert (
        m_utils.typed.call_args
        == [(m_typing.ConfiguredExtensionsDict, m_json.loads.return_value),
            {}])
    assert (
        m_json.loads.call_args
        == [(m_plib.Path.return_value.read_text.return_value, ), {}])
    assert (
        m_plib.Path.call_args
        == [("BUILD", ), {}])
    assert (
        m_plib.Path.return_value.read_text.call_args
        == [(), {}])
    assert "configured_extensions" in checker.__dict__


def test_extensions_extensions_schema(patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "typing",
        "utils",
        ("AExtensionsCheck.extensions_schema_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")

    with patched as (m_typing, m_utils, m_path):
        assert (
            checker.extensions_schema
            == m_utils.typed.return_value)

    assert (
        m_utils.typed.call_args
        == [(m_typing.ExtensionsSchemaDict,
             m_utils.from_yaml.return_value), {}])
    assert (
        m_utils.from_yaml.call_args
        == [(m_path.return_value, ), {}])
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


def test_extensions_fuzzed_count(patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "len",
        ("AExtensionsCheck.fuzz_test_path",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.fuzzed_filter_names_re",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    lines = [f"L{i}" for i in range(0, 5)]

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


def test_extensions_metadata(patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "dict",
        ("AExtensionsCheck.metadata_core",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.metadata_contrib",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    core = {f"KCORE{i}": f"VCORE{i}" for i in range(0, 5)}
    contrib = {f"KCONTRIB{i}": f"VCONTRIB{i}" for i in range(0, 5)}

    with patched as (m_dict, m_core, m_contrib):
        m_core.return_value = core
        m_contrib.return_value = contrib
        assert (
            checker.metadata
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(), dict(**core, **contrib)])


@pytest.mark.parametrize("mtype", ["core", "contrib"])
@pytest.mark.parametrize(
    "raises", [None, BaseException, utils.exceptions.TypeCastingError])
def test_extensions_metadata_data(patches, mtype, raises):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "utils.from_yaml",
        "utils.typed",
        (f"AExtensionsCheck.metadata_{mtype}_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")

    with patched as (m_yaml, m_typed, m_path):
        if raises:
            m_typed.side_effect = raises("AN ERROR OCCURRED")

        if raises == utils.exceptions.TypeCastingError:
            ConfigError = check.exceptions.ExtensionsConfigurationError
            with pytest.raises(ConfigError) as e:
                getattr(checker, f"metadata_{mtype}")
        elif raises:
            with pytest.raises(raises):
                getattr(checker, f"metadata_{mtype}")
        else:
            assert (
                getattr(checker, f"metadata_{mtype}")
                == m_typed.return_value)

    assert (
        m_typed.call_args
        == [(check.typing.ExtensionsMetadataDict,
             m_yaml.return_value), {}])
    assert (
        m_yaml.call_args
        == [(m_path.return_value, ), {}])
    if raises == utils.exceptions.TypeCastingError:
        assert (
            e.value.args[0]
            == (f"Failed to parse {mtype} metadata "
                f"({m_path.return_value}): AN ERROR OCCURRED"))
    assert (
        (f"metadata_{mtype}" in checker.__dict__)
        is (not raises))


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


def test_extensions_metadata_errors(patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.metadata",
         dict(new_callable=PropertyMock)),
        "AExtensionsCheck.check_metadata",
        prefix="envoy.code.check.abstract.extensions")
    meta = [f"KMETA{i}" for i in range(0, 5)]

    with patched as (m_meta, m_check):
        m_meta.return_value = meta
        assert (
            checker.metadata_errors
            == {k: m_check.return_value
                for k in meta})

    assert (
        m_check.call_args_list
        == [[(k, ), {}] for k in meta])
    assert "metadata_errors" not in checker.__dict__


def test_extensions_metadata_missing(patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.all_extensions",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.metadata",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    all_ext = set([f"K{i}" for i in range(0, 10)])
    meta = {f"K{i}": f"V{i}" for i in range(0, 10) if i % 2}
    expected = set([f"K{i}" for i in range(0, 10) if not i % 2])

    with patched as (m_all, m_meta):
        m_all.return_value = all_ext
        m_meta.return_value = meta
        assert (
            checker.metadata_missing
            == expected)

    assert "metadata_missing" not in checker.__dict__


def test_extensions_metadata_only(patches):
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
    meta = {f"K{i}": f"V{i}" for i in range(0, 20)}
    meta_only = set([f"K{i}" for i in range(7, 13)])
    expected = set([
        f"K{i}"
        for i
        in range(0, 20)
        if (not i % 2 and i not in range(7, 13))])

    with patched as (m_all, m_meta, m_meta_only):
        m_all.return_value = all_ext
        m_meta.return_value = meta
        m_meta_only.return_value = meta_only

        assert (
            checker.metadata_only
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


def test_extensions_registration_errors(patches):
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
        m_missing.return_value = missing
        m_only.return_value = only
        assert (
            checker.registration_errors
            == [*[f"Metadata for unused extension found: {extension}"
                  for extension
                  in sorted(only)],
                *[f"Metadata missing for extension: {extension}"
                  for extension
                  in sorted(missing)]])

    assert "registration_errors" not in checker.__dict__


def test_extensions_robust_to_downstream_count(patches):
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
        m_meta.return_value = metadata
        assert checker.robust_to_downstream_count == 3

    assert "robust_to_downstream_count" not in checker.__dict__


def test_extensions_check_metadata(patches):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        "AExtensionsCheck._check_metadata_categories",
        "AExtensionsCheck._check_metadata_security_posture",
        "AExtensionsCheck._check_metadata_status",
        prefix="envoy.code.check.abstract.extensions")
    cats = [f"CAT{i}" for i in range(0, 5)]
    sec = tuple(f"SEC{i}" for i in range(0, 5))
    status = (f"STATUS{i}" for i in range(0, 5))
    extension = MagicMock()

    with patched as (m_cats, m_sec, m_status):
        m_cats.return_value = cats
        m_sec.return_value = sec
        m_status.return_value = status
        assert (
            checker.check_metadata(extension)
            == (list(cats)
                + list(sec)
                + list(f"STATUS{i}" for i in range(0, 5))))

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
def test_extensions__check_metadata_categories(patches, ext_cats, all_cats):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.extension_categories",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.metadata",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")

    with patched as (m_cats, m_meta):
        m_cats.return_value = all_cats
        (m_meta.return_value.__getitem__
               .return_value.get.return_value) = ext_cats
        _result = checker._check_metadata_categories("EXTENSION")
        assert isinstance(_result, types.GeneratorType)
        result = list(_result)

    assert (
        list(m_meta.return_value.__getitem__.call_args)
        == [('EXTENSION',), {}])
    assert (
        list(m_meta.return_value.__getitem__.return_value.get.call_args)
        == [('categories', ()), {}])

    if not ext_cats:
        assert (
            result
            == ["Missing extension category for EXTENSION. "
                "Please make sure the target is an envoy_cc_extension "
                "and category is set"])
        return

    wrong_cats = [cat for cat in ext_cats if cat not in all_cats]
    if wrong_cats:
        assert (
            result
            == [f"Unknown extension category for EXTENSION: {cat}. "
                "Please add it to tools/extensions/extensions_check.py"
                for cat in wrong_cats])
        return

    assert result == []


@pytest.mark.parametrize("sec_posture", [None, "A", "Z"])
def test_extensions__check_metadata_security_posture(patches, sec_posture):
    checker = check.AExtensionsCheck(
        "DIRECTORY", extensions_build_config="BUILD")
    patched = patches(
        ("AExtensionsCheck.extension_security_postures",
         dict(new_callable=PropertyMock)),
        ("AExtensionsCheck.metadata",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.extensions")
    postures = ["A", "B", "C"]

    with patched as (m_sec, m_meta):
        m_sec.return_value = postures
        (m_meta.return_value.__getitem__
               .return_value.__getitem__.return_value) = sec_posture
        _result = checker._check_metadata_security_posture("EXTENSION")
        assert isinstance(_result, types.GeneratorType)
        result = list(_result)

    assert (
        list(m_meta.return_value.__getitem__.call_args)
        == [('EXTENSION',), {}])
    assert (
        list(m_meta.return_value.__getitem__
                   .return_value.__getitem__.call_args)
        == [('security_posture',), {}])

    if not sec_posture:
        assert (
            result
            == ["Missing security posture for EXTENSION. "
                "Please make sure the target is an "
                "envoy_cc_extension and security_posture is set"])
    elif sec_posture not in postures:
        assert (
            result
            == [f"Unknown security posture for EXTENSION: {sec_posture}"])
    else:
        assert result == []


@pytest.mark.parametrize("status", ["A", "Z"])
def test_extensions__check_metadata_status(patches, status):
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
        m_status.return_value = status_values
        (m_meta.return_value.__getitem__
               .return_value.__getitem__.return_value) = status
        _result = checker._check_metadata_status("EXTENSION")
        assert isinstance(_result, types.GeneratorType)
        result = list(_result)

    assert (
        list(m_meta.return_value.__getitem__.call_args)
        == [('EXTENSION',), {}])
    assert (
        list(m_meta.return_value.__getitem__
                   .return_value.__getitem__.call_args)
        == [('status',), {}])

    if status not in status_values:
        assert result == [f'Unknown status for EXTENSION: {status}']
    else:
        assert result == []
