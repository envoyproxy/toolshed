
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio.core import subprocess

from envoy.code import check


def test_envoy_buildifier_constructor(patches):
    kwargs = dict(
        _foo=MagicMock(),
        _bar=MagicMock(),
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "_subprocess.ASubprocessHandler.__init__",
        prefix="envoy.code.check.abstract.bazel")

    with patched as (m_handler, ):
        buildifier = check.abstract.bazel.EnvoyBuildifier(
            "PATH",
            "FOO",
            "BAR",
            **kwargs)
    assert isinstance(buildifier, subprocess.ISubprocessHandler)
    assert isinstance(buildifier, subprocess.ASubprocessHandler)
    for k, v in kwargs.items():
        if not k.startswith("_"):
            assert getattr(buildifier, k) == v
    assert buildifier.api_prefix == "api"
    assert (
        m_handler.call_args
        == [("PATH", "FOO", "BAR"),
            {k: v for k, v in kwargs.items() if k.startswith("_")}])


@pytest.mark.parametrize("bazel", [True, False])
@pytest.mark.parametrize("starlark", [True, False])
@pytest.mark.parametrize("mobile", [True, False])
def test_envoy_buildifier_allowed_bazel_tools(
        patches, bazel, starlark, mobile):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        ("EnvoyBuildifier.is_mobile",
         dict(new_callable=PropertyMock)),
        ("EnvoyBuildifier.is_starlark",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    (kwargs["filepath"].parts.__getitem__.return_value
                             .__eq__.return_value) = bazel

    with patched as (m_mobile, m_star):
        m_star.return_value = starlark
        m_mobile.return_value = mobile
        assert (
            buildifier.allowed_bazel_tools
            == starlark or bazel)

    assert "allowed_bazel_tools" in buildifier.__dict__
    if starlark:
        assert not kwargs["filepath"].parts.__getitem__.called
        return
    assert (
        kwargs["filepath"].parts.__getitem__.call_args
        == [(0 if not mobile else 1, ), {}])
    assert (
        kwargs["filepath"].parts.__getitem__.return_value.__eq__.call_args
        == [("bazel", ), {}])


@pytest.mark.parametrize("suffix", [True, False])
@pytest.mark.parametrize("included", [True, False])
def test_envoy_buildifier_allowed_protobuf_direct(
        patches, iters, suffix, included):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "any",
        ("EnvoyBuildifier.format_config",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    kwargs["filepath"].name.endswith.return_value = suffix
    paths = dict(
        proto=iters(),
        repositories_bzl=iters())
    config_paths = iters()

    with patched as (m_any, m_config):
        m_any.return_value = included
        (m_config.return_value.suffixes
                 .__getitem__.side_effect) = lambda idx: paths[idx]
        (m_config.return_value.paths
                 .__getitem__.return_value
                 .__getitem__.return_value) = config_paths
        assert (
            buildifier.allowed_protobuf_direct
            == suffix or included)
        if not suffix:
            path_iter = m_any.call_args[0][0]
            path_list = list(path_iter)

    assert "allowed_protobuf_direct" in buildifier.__dict__
    assert (
        kwargs["filepath"].name.endswith.call_args
        == [(('I0', 'I1', 'I2', 'I3', 'I4',
              'I0', 'I1', 'I2', 'I3', 'I4'), ), {}])
    if suffix:
        assert not m_any.called
        return
    assert type(path_iter) is types.GeneratorType
    assert (
        path_list
        == [
            kwargs["filepath"].is_relative_to.return_value
            for x in config_paths])
    assert (
        kwargs["filepath"].is_relative_to.call_args_list
        == [[(x, ), {}]
            for x in config_paths])


@pytest.mark.parametrize("contains", [True, False])
def test_envoy_buildifier_allowed_urls(patches, contains):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "str",
        ("EnvoyBuildifier.format_config",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    with patched as (m_str, m_config):
        (m_config.return_value.paths
                 .__getitem__.return_value
                 .__getitem__.return_value
                 .__contains__.return_value) = contains
        assert (
            buildifier.allowed_urls
            == contains)

    assert "allowed_urls" in buildifier.__dict__
    assert (
        m_str.call_args
        == [(kwargs["filepath"], ), {}])
    assert (
        m_config.return_value.paths.__getitem__.call_args
        == [("build_urls", ), {}])
    assert (
        (m_config.return_value.paths
                 .__getitem__.return_value
                 .__getitem__.call_args)
        == [("include", ), {}])
    assert (
        (m_config.return_value.paths
                 .__getitem__.return_value
                 .__getitem__.return_value
                 .__contains__.call_args)
        == [(m_str.return_value, ), {}])


def test_envoy_buildifier_errors(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    assert buildifier.errors == []
    assert "errors" in buildifier.__dict__


def test_envoy_buildifier_format_config(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "shared.EnvoyFormatConfig",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    with patched as (m_fconfig, ):
        assert (
            buildifier.format_config
            == m_fconfig.return_value)

    assert "format_config" in buildifier.__dict__
    assert (
        m_fconfig.call_args
        == [(kwargs["config"], kwargs["filepath"]), {}])


@pytest.mark.parametrize("api", [True, False])
def test_envoy_buildifier_is_api(patches, api):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    (kwargs["filepath"].parts.__getitem__
                       .return_value.__eq__.return_value) = api

    assert buildifier.is_api == api

    assert "is_api" in buildifier.__dict__
    assert (
        kwargs["filepath"].parts.__getitem__.call_args
        == [(0, ), {}])
    assert (
        kwargs["filepath"].parts.__getitem__.return_value.__eq__.call_args
        == [(buildifier.api_prefix, ), {}])


@pytest.mark.parametrize("starlark", [True, False])
@pytest.mark.parametrize("workspace", [True, False])
@pytest.mark.parametrize("external", [True, False])
def test_envoy_buildifier_is_build(patches, starlark, workspace, external):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        ("EnvoyBuildifier.is_starlark",
         dict(new_callable=PropertyMock)),
        ("EnvoyBuildifier.is_workspace",
         dict(new_callable=PropertyMock)),
        ("EnvoyBuildifier.is_external_build",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    with patched as (m_star, m_workspace, m_external):
        m_star.return_value = starlark
        m_workspace.return_value = workspace
        m_external.return_value = external
        assert (
            buildifier.is_build
            == (not starlark
                and not workspace
                and not external))

    assert "is_build" in buildifier.__dict__


def test_envoy_buildifier_is_build_fixer_excluded(patches, iters):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "any",
        ("EnvoyBuildifier.format_config",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    paths = iters()

    with patched as (m_any, m_config):
        (m_config.return_value.paths
                 .__getitem__.return_value
                 .__getitem__.return_value) = paths
        assert (
            buildifier.is_build_fixer_excluded
            == m_any.return_value)
        any_iter = m_any.call_args[0][0]
        any_list = list(any_iter)

    assert "is_build_fixer_excluded" not in buildifier.__dict__
    assert (
        type(any_iter)
        is types.GeneratorType)
    assert (
        any_list
        == [kwargs["filepath"].is_relative_to.return_value
            for x in paths])
    assert (
        kwargs["filepath"].is_relative_to.call_args_list
        == [[(x, ), {}]
            for x in paths])
    assert (
        m_config.return_value.paths.__getitem__.call_args
        == [("build_fixer", ), {}])
    assert (
        (m_config.return_value.paths
                 .__getitem__.return_value.__getitem__.call_args)
        == [("exclude", ), {}])


@pytest.mark.parametrize("api", [True, False])
@pytest.mark.parametrize("envoy", [True, False])
def test_envoy_buildifier_is_api_envoy(patches, api, envoy):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        ("EnvoyBuildifier.is_api",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    (kwargs["filepath"].parts.__getitem__
                       .return_value.__eq__.return_value) = envoy

    with patched as (m_api, ):
        m_api.return_value = api
        assert (
            buildifier.is_api_envoy
            == (api and envoy))

    assert "is_api_envoy" in buildifier.__dict__
    if not api:
        assert not kwargs["filepath"].parts.__getitem__.called
        return
    assert (
        kwargs["filepath"].parts.__getitem__.call_args
        == [(1, ), {}])
    assert (
        (kwargs["filepath"].parts.__getitem__
                           .return_value.__eq__.call_args)
        == [("envoy", ), {}])


def test_envoy_buildifier_is_external_build(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "any",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    (kwargs["filepath"].is_relative_to
                       .return_value) = False

    with patched as (m_any, ):
        assert (
            buildifier.is_external_build
            == m_any.return_value)
        any_iters = m_any.call_args[0][0]
        any_list = list(any_iters)

    assert type(any_iters) is types.GeneratorType
    assert any_list == [False, False]
    assert (
        kwargs["filepath"].is_relative_to.call_args_list
        == [[("bazel/external", ), {}],
            [("tools/clang_tools", ), {}]])


@pytest.mark.parametrize("build", [True, False])
@pytest.mark.parametrize("api", [True, False])
@pytest.mark.parametrize("excluded", [True, False])
def test_envoy_buildifier_is_package(patches, build, api, excluded):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        ("EnvoyBuildifier.is_api",
         dict(new_callable=PropertyMock)),
        ("EnvoyBuildifier.is_build",
         dict(new_callable=PropertyMock)),
        ("EnvoyBuildifier.is_build_fixer_excluded",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    with patched as (m_api, m_build, m_exclude):
        m_api.return_value = api
        m_build.return_value = build
        m_exclude.return_value = excluded
        assert (
            buildifier.is_package
            == (build and not api and not excluded))

    assert "is_package" in buildifier.__dict__


@pytest.mark.parametrize("bzl", [True, False])
def test_envoy_buildifier_is_starlark(patches, bzl):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    kwargs["filepath"].name.endswith.return_value = bzl

    assert (
        buildifier.is_starlark
        == bzl)

    assert "is_starlark" in buildifier.__dict__
    assert (
        kwargs["filepath"].name.endswith.call_args
        == [(".bzl", ), {}])


@pytest.mark.parametrize("workspace", [True, False])
def test_envoy_buildifier_is_workspace(patches, workspace):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    kwargs["filepath"].name.__eq__.return_value = workspace

    assert (
        buildifier.is_workspace
        == workspace)

    assert "is_workspace" in buildifier.__dict__
    assert (
        kwargs["filepath"].name.__eq__.call_args
        == [("WORKSPACE", ), {}])


def __test_envoy_buildifier_re_api_include(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    with patched as (m_re, ):
        assert (
            buildifier.re_api_include
            == m_re.compile.return_value)

    assert "re_api_include" in buildifier.__dict__
    assert (
        m_re.compile.call_args
        == [(check.abstract.bazel.RE_API_INCLUDE, ), {}])


def __test_envoy_buildifier_re_buildozer_print(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    with patched as (m_re, ):
        assert (
            buildifier.re_buildozer_print
            == m_re.compile.return_value)

    assert "re_buildozer_print" in buildifier.__dict__
    assert (
        m_re.compile.call_args
        == [(check.abstract.bazel.RE_BUILDOZER_PRINT, ), {}])


def test_envoy_buildifier_re_contrib_package_load_block(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    with patched as (m_re, ):
        assert (
            buildifier.re_contrib_package_load_block
            == m_re.compile.return_value)

    assert "re_contrib_package_load_block" in buildifier.__dict__
    assert (
        m_re.compile.call_args
        == [(check.abstract.bazel.RE_CONTRIB_PACKAGE_LOAD_BLOCK,
             m_re.DOTALL),
            {}])


def test_envoy_buildifier_re_envoy_rule(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    with patched as (m_re, ):
        assert (
            buildifier.re_envoy_rule
            == m_re.compile.return_value)

    assert "re_envoy_rule" in buildifier.__dict__
    assert (
        m_re.compile.call_args
        == [(check.abstract.bazel.RE_ENVOY_RULE, ), {}])


def test_envoy_buildifier_re_extension_package_load_block(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    with patched as (m_re, ):
        assert (
            buildifier.re_extension_package_load_block
            == m_re.compile.return_value)

    assert "re_extension_package_load_block" in buildifier.__dict__
    assert (
        m_re.compile.call_args
        == [(check.abstract.bazel.RE_EXTENSION_PACKAGE_LOAD_BLOCK,
             m_re.DOTALL),
            {}])


def test_envoy_buildifier_re_mobile_package_load_block(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    with patched as (m_re, ):
        assert (
            buildifier.re_mobile_package_load_block
            == m_re.compile.return_value)

    assert "re_mobile_package_load_block" in buildifier.__dict__
    assert (
        m_re.compile.call_args
        == [(check.abstract.bazel.RE_MOBILE_PACKAGE_LOAD_BLOCK,
             m_re.DOTALL),
            {}])


def test_envoy_buildifier_re_old_license(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    with patched as (m_re, ):
        assert (
            buildifier.re_old_license
            == m_re.compile.return_value)

    assert "re_old_license" in buildifier.__dict__
    assert (
        m_re.compile.call_args
        == [(check.abstract.bazel.RE_OLD_LICENSES, m_re.MULTILINE), {}])


def test_envoy_buildifier_re_package_load_block(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    with patched as (m_re, ):
        assert (
            buildifier.re_package_load_block
            == m_re.compile.return_value)

    assert "re_package_load_block" in buildifier.__dict__
    assert (
        m_re.compile.call_args
        == [(check.abstract.bazel.RE_PACKAGE_LOAD_BLOCK, m_re.DOTALL), {}])


def test_envoy_buildifier_text(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)

    assert (
        buildifier.text
        == kwargs["filepath"].read_text.return_value)

    assert "text" in buildifier.__dict__
    assert (
        kwargs["filepath"].read_text.call_args
        == [(), {}])


@pytest.mark.parametrize("allowed", [True, False])
@pytest.mark.parametrize("contains", [True, False])
@pytest.mark.parametrize("excepted", [True, False])
def test_envoy_buildifier_bad_bazel_tools_line(
        patches, allowed, contains, excepted):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        ("EnvoyBuildifier.allowed_bazel_tools",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    line = MagicMock()

    def has(thing):
        if thing == "@bazel_tools":
            return contains
        if thing == "python/runfiles":
            return excepted

    line.__contains__.side_effect = has

    with patched as (m_allowed, ):
        m_allowed.return_value = allowed
        assert (
            buildifier.bad_bazel_tools_line(line)
            == (not allowed
                and contains
                and not excepted))

    if allowed:
        assert not line.__contains__.called
        return
    assert (
        line.__contains__.call_args_list[0]
        == [("@bazel_tools", ), {}])
    if not contains:
        assert len(line.__contains__.call_args_list) == 1
        return
    assert (
        line.__contains__.call_args
        == [("python/runfiles", ), {}])


@pytest.mark.parametrize("build", [True, False])
@pytest.mark.parametrize("contains", [True, False])
def test_envoy_buildifier_bad_envoy_line(patches, build, contains):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        ("EnvoyBuildifier.is_build",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    line = MagicMock()
    line.__contains__.return_value = contains

    with patched as (m_build, ):
        m_build.return_value = build
        assert (
            buildifier.bad_envoy_line(line)
            == (build and contains))

    if not build:
        assert not line.__contains__.called
        return
    assert (
        line.__contains__.call_args
        == [("@envoy//", ), {}])


@pytest.mark.parametrize("allowed", [True, False])
@pytest.mark.parametrize("contains", [True, False])
def test_envoy_buildifier_bad_protobuf_line(patches, allowed, contains):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        ("EnvoyBuildifier.allowed_protobuf_direct",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    line = MagicMock()
    line.__contains__.return_value = contains

    with patched as (m_allowed, ):
        m_allowed.return_value = allowed
        assert (
            buildifier.bad_protobuf_line(line)
            == (not allowed and contains))

    if allowed:
        assert not line.__contains__.called
        return
    assert (
        line.__contains__.call_args
        == [('"protobuf"', ), {}])


@pytest.mark.parametrize("allowed", [True, False])
@pytest.mark.parametrize("contains_plural", [True, False])
@pytest.mark.parametrize("contains", [True, False])
def test_envoy_buildifier_bad_url_line(
        patches, allowed, contains_plural, contains):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        ("EnvoyBuildifier.allowed_urls",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    line = MagicMock()

    def has(thing):
        if thing == " url = ":
            return contains
        if thing == " urls = ":
            return contains_plural

    line.__contains__.side_effect = has

    with patched as (m_allowed, ):
        m_allowed.return_value = allowed
        assert (
            buildifier.bad_url_line(line)
            == (not allowed and (contains or contains_plural)))

    if allowed:
        assert not line.__contains__.called
        return
    assert (
        line.__contains__.call_args_list[0]
        == [(" urls = ", ), {}])
    if contains_plural:
        assert len(line.__contains__.call_args_list) == 1
        return
    assert (
        line.__contains__.call_args
        == [(" url = ", ), {}])


def __test_envoy_buildifier_find_api_deps(patches, iters):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "set",
        ("EnvoyBuildifier.re_api_include",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    source_path = MagicMock()
    lines = iters()
    source_path.open.return_value.__enter__.return_value = lines
    matchers = {}

    def _match(thing):
        idx = int(thing[1])
        if idx % 2:
            matchers[thing[1]] = MagicMock()
            return matchers[thing[1]]

    with patched as (m_set, m_re):
        m_re.return_value.match.side_effect = _match
        assert (
            buildifier.find_api_deps(source_path)
            == m_set.return_value)
        setiter = m_set.call_args[0][0]
        setlist = list(setiter)

    assert type(setiter) is types.GeneratorType
    assert (
        setlist
        == [f"@envoy_api//{matcher.group.return_value}:pkg_cc_proto"
            for matcher in matchers.values()])
    assert (
        source_path.open.call_args
        == [(), {}])
    assert (
        m_re.return_value.match.call_args_list
        == [[(idx, ), {}]
            for idx in lines])
    for matcher in matchers.values():
        assert (
            matcher.group.call_args
            == [(1, ), {}])


@pytest.mark.parametrize("tools", [True, False])
@pytest.mark.parametrize("envoy", [True, False])
@pytest.mark.parametrize("protobuf", [True, False])
@pytest.mark.parametrize("url", [True, False])
def test_envoy_buildifier_fix_build_line(patches, tools, envoy, protobuf, url):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        ("EnvoyBuildifier.errors",
         dict(new_callable=PropertyMock)),
        "EnvoyBuildifier.bad_bazel_tools_line",
        "EnvoyBuildifier.bad_envoy_line",
        "EnvoyBuildifier.bad_protobuf_line",
        "EnvoyBuildifier.bad_url_line",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    line = MagicMock()
    all_errors = dict(
        tools=(
            "unexpected @bazel_tools reference, "
            "please indirect via a definition in //bazel"),
        protobuf=(
            "unexpected direct external dependency on protobuf, use "
            "//source/common/protobuf instead."),
        envoy="Superfluous '@envoy//' prefix",
        url="Only repository_locations.bzl may contains URL references")
    local_vars = locals()
    errors = [v for k, v in all_errors.items() if local_vars[k]]

    with patched as (m_errors, m_tools, m_envoy, m_proto, m_url):
        m_tools.return_value = tools
        m_envoy.return_value = envoy
        m_proto.return_value = protobuf
        m_url.return_value = url
        assert (
            buildifier.fix_build_line(line)
            == (line
                if not envoy
                else line.replace.return_value))

    for bad in (m_tools, m_envoy, m_proto):
        assert (
            bad.call_args
            == [(line, ), {}])
    assert (
        m_url.call_args
        == [(line if not envoy else line.replace.return_value, ), {}])
    assert (
        m_errors.return_value.append.call_args_list
        == [[(error, ), {}]
            for error in errors])
    if not envoy:
        assert not line.replace.called
        return
    assert (
        line.replace.call_args
        == [("@envoy//", "//"), {}])


@pytest.mark.parametrize("has_errors", [True, False])
def test_envoy_buildifier_handle(patches, iters, has_errors):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "str",
        "checker.Problems",
        ("EnvoyBuildifier.errors",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    errors = (
        iters()
        if has_errors
        else [])
    response = MagicMock()

    with patched as (m_str, m_problems, m_errors):
        m_errors.return_value = errors
        assert (
            buildifier.handle(response)
            == ({m_str.return_value: m_problems.return_value}
                if has_errors
                else {}))

    if not errors:
        assert not m_str.called
        assert not m_problems.called
        return
    assert (
        m_str.call_args
        == [(kwargs["filepath"], ), {}])
    _errors = "\n".join(errors)
    assert (
        m_problems.call_args
        == [(), dict(errors=[f"{kwargs['filepath']}\n{_errors}"])])


def test_envoy_buildifier_handle_error(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "str",
        "checker.Problems",
        "EnvoyBuildifier._diff",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    response = MagicMock()

    with patched as (m_str, m_problems, m_diff):
        assert (
            buildifier.handle_error(response)
            == {m_str.return_value: m_problems.return_value})

    assert (
        m_str.call_args
        == [(kwargs["filepath"], ), {}])
    assert (
        m_problems.call_args
        == [(), dict(errors=[f"{kwargs['filepath']}\n{m_diff.return_value}"])])
    assert (
        m_diff.call_args
        == [(response, ), {}])


def test_envoy_buildifier_has_failed(patches):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "bool",
        "EnvoyBuildifier._diff",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    response = MagicMock()

    with patched as (m_bool, m_diff):
        assert (
            buildifier.has_failed(response)
            == m_bool.return_value)

    assert (
        m_bool.call_args
        == [(m_diff.return_value, ), {}])
    assert (
        m_diff.call_args
        == [(response, ), {}])


@pytest.mark.parametrize("build", [True, False])
@pytest.mark.parametrize("package", [True, False])
@pytest.mark.parametrize("api", [True, False])
def test_envoy_buildifier_preprocess(patches, build, package, api):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        ("EnvoyBuildifier.is_build",
         dict(new_callable=PropertyMock)),
        ("EnvoyBuildifier.is_api_envoy",
         dict(new_callable=PropertyMock)),
        ("EnvoyBuildifier.is_package",
         dict(new_callable=PropertyMock)),
        "EnvoyBuildifier.xform_build",
        "EnvoyBuildifier.xform_package",
        "EnvoyBuildifier.xform_deps_api",
        "EnvoyBuildifier.xform_api_package",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    text = MagicMock()

    with patched as patchy:
        (m_build, m_api, m_package, m_xbuild,
         m_xpackage, m_xdeps, m_xapi) = patchy
        m_api.return_value = api
        m_build.return_value = build
        m_package.return_value = package
        result = buildifier.preprocess(text)

    _result = input = text
    if build:
        assert (
            m_xbuild.call_args
            == [(input, ), {}])
        _result = input = m_xbuild.return_value
    else:
        assert not m_xbuild.called
    if package:
        assert (
            m_xpackage.call_args
            == [(input, ), {}])
        assert (
            m_xdeps.call_args
            == [(m_xpackage.return_value, ), {}])
        _result = input = m_xdeps.return_value
    else:
        assert not m_xpackage.called
        assert not m_xdeps.called
    if api:
        assert (
            m_xapi.call_args
            == [(input, ), {}])
        _result = m_xapi.return_value
    else:
        assert not m_xapi.called
    assert result == _result


def __test_envoy_buildifier_run_buildozer(patches, iters):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "pathlib",
        "tempfile",
        "EnvoyBuildifier._run_buildozer",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    cmds = iters(dict).items()
    text = MagicMock()

    with patched as (m_plib, m_temp, m_run):
        assert (
            buildifier.run_buildozer(cmds, text)
            == m_run.return_value.strip.return_value)

    assert (
        m_temp.NamedTemporaryFile.call_args
        == [(), dict(mode="w")])
    assert (
        m_plib.Path.call_args
        == [((m_temp.NamedTemporaryFile.return_value
                    .__enter__.return_value.name), ),
            {}])
    expected = "\n".join(
        "%s|-:%s"
        % (cmd, target) for cmd, target in cmds)
    assert (
        m_plib.Path.return_value.write_text.call_args
        == [(expected, ), {}])
    assert (
        m_run.call_args
        == [(m_plib.Path.return_value, text), {}])


@pytest.mark.parametrize("workspace", [True, False])
def test_envoy_buildifier_subprocess_args(patches, iters, workspace):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "_subprocess.ASubprocessHandler.subprocess_args",
        ("EnvoyBuildifier.is_workspace",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    args = iters()
    kwargs = iters(dict)

    with patched as (m_super, m_workspace):
        m_workspace.return_value = workspace
        assert (
            buildifier.subprocess_args(*args, **kwargs)
            == m_super.return_value)

    expected_args = (
        args + ["-type=workspace"]
        if workspace
        else args)
    assert (
        m_super.call_args
        == [tuple(expected_args), kwargs])


def test_envoy_buildifier_subprocess_kwargs(patches, iters):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        ("EnvoyBuildifier.text",
         dict(new_callable=PropertyMock)),
        "EnvoyBuildifier.preprocess",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    args = iters()
    kwargs = iters(dict)

    with patched as (m_text, m_preproc):
        assert (
            buildifier.subprocess_kwargs(*args, **kwargs)
            == {**buildifier.kwargs,
                "input": m_preproc.return_value,
                **kwargs})

    assert (
        m_preproc.call_args
        == [(m_text.return_value, ), {}])


@pytest.mark.parametrize("cached", [None, "CACHED"])
def test_envoy_buildifier__diff(patches, iters, cached):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "difflib",
        "str",
        ("EnvoyBuildifier.text",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    buildifier._diff_output = cached
    response = MagicMock()
    diff = iters()

    with patched as (m_diff, m_str, m_text):
        m_diff.unified_diff.return_value = diff
        assert (
            buildifier._diff(response)
            == (cached if cached
                else "\n".join(diff)))

    if cached:
        assert not response.stdout.splitlines.called
        assert not m_text.return_value.splitlines.called
        assert not m_str.called
        assert not m_diff.unified_diff.called
        return
    assert (
        response.stdout.splitlines.call_args
        == [(), {}])
    assert (
        m_text.return_value.splitlines.call_args
        == [(), {}])
    assert (
        m_diff.unified_diff.call_args
        == [(m_text.return_value.splitlines.return_value,
             response.stdout.splitlines.return_value),
            dict(fromfile=m_str.return_value,
                 tofile=m_str.return_value)])
    assert (
        m_str.call_args_list
        == [[(kwargs["filepath"], ), {}],
            [(kwargs["filepath"], ), {}]])
    assert buildifier._diff_output == "\n".join(diff)


@pytest.mark.parametrize("responsecode", [0, 1, 3, 137])
@pytest.mark.parametrize("stdout", [True, False])
def __test_envoy_buildifier__run_buildozer(patches, responsecode, stdout):
    kwargs = dict(
        buildozer_path=MagicMock(),
        config=MagicMock(),
        filepath=MagicMock())
    patched = patches(
        "str",
        "subprocess",
        prefix="envoy.code.check.abstract.bazel")
    buildifier = check.abstract.bazel.EnvoyBuildifier(
        "PATH",
        **kwargs)
    cmd_path = MagicMock()
    text = MagicMock()

    with patched as (m_str, m_subproc):
        m_subproc.run.return_value.returncode = responsecode
        if not stdout:
            m_subproc.run.return_value.stdout = None
        if responsecode in [0, 3]:
            assert (
                buildifier._run_buildozer(cmd_path, text)
                == (text
                    if not stdout
                    else (m_subproc.run.return_value
                                   .stdout.decode.return_value)))
        else:
            with pytest.raises(check.exceptions.FixError) as e:
                buildifier._run_buildozer(cmd_path, text)

    assert (
        m_subproc.run.call_args
        == [([kwargs["buildozer_path"], "-stdout",
              "-f", m_str.return_value], ),
            dict(input=text.encode.return_value,
                 stdout=m_subproc.PIPE,
                 stderr=m_subproc.PIPE)])
    assert (
        m_str.call_args
        == [(cmd_path, ), {}])
    if responsecode not in [0, 3]:
        assert (
            e.value.args[0]
            == f"buildozer execution failed: {m_subproc.run.return_value}")
        return
    if stdout:
        assert (
            m_subproc.run.return_value.stdout.decode.call_args
            == [(), {}])


def test_bazel_check_constructor():
    bazel = check.ABazelCheck("DIRECTORY")
    assert bazel.directory == "DIRECTORY"
    assert isinstance(bazel, check.interface.IBazelCheck)
    assert isinstance(bazel, check.abstract.AFileCodeCheck)


def test_bazel_check_filter_files(patches, iters):
    patched = patches(
        "set",
        prefix="envoy.code.check.abstract.bazel")
    files = iters(count=10)

    def match_fun(item):
        return int(item[1:]) % 3

    def exclude_fun(item):
        return int(item[1:]) % 2

    match = MagicMock()
    exclude = MagicMock()
    match.side_effect = match_fun
    exclude.side_effect = exclude_fun

    with patched as (m_set, ):
        assert (
            check.ABazelCheck.filter_files(files, match, exclude)
            == m_set.return_value)
        resultiter = m_set.call_args[0][0]
        result = list(resultiter)

    assert isinstance(resultiter, types.GeneratorType)
    assert (
        result
        == [x for x in files if int(x[1:]) % 3 and not int(x[1:]) % 2])
    assert (
        match.call_args_list
        == [[(f, ), {}] for f in files])
    assert (
        exclude.call_args_list
        == [[(f, ), {}] for f in files if int(f[1:]) % 3])


def test_bazel_check_run_buildifier(patches, iters):
    patched = patches(
        "pathlib",
        "EnvoyBuildifier",
        prefix="envoy.code.check.abstract.bazel")
    args = iters()
    path = MagicMock()
    config = MagicMock()
    buildozer_path = MagicMock()

    with patched as (m_plib, m_build):
        assert (
            check.ABazelCheck.run_buildifier(
                path, config, buildozer_path, *args)
            == m_build.return_value.run.return_value)

    assert (
        m_build.call_args
        == [(path, ),
            dict(config=config,
                 filepath=m_plib.Path.return_value,
                 buildozer_path=buildozer_path)])
    assert (
        m_plib.Path.call_args
        == [(args[-1], ), {}])
    assert (
        m_build.return_value.run.call_args
        == [tuple(args[:-1]), {}])


def test_bazel_check_buildifier_command(patches):
    directory = MagicMock()
    config = MagicMock()
    bazel = check.abstract.bazel.ABazelCheck(
        directory,
        config=config)
    patched = patches(
        "partial",
        ("ABazelCheck.buildifier_path",
         dict(new_callable=PropertyMock)),
        ("ABazelCheck.buildozer_path",
         dict(new_callable=PropertyMock)),
        "ABazelCheck.run_buildifier",
        prefix="envoy.code.check.abstract.bazel")

    with patched as (m_partial, m_ifier_path, m_ozer_path, m_run):
        assert (
            bazel.buildifier_command
            == m_partial.return_value)

    assert "buildifier_command" in bazel.__dict__
    assert (
        m_partial.call_args
        == [(m_run,
             directory.path,
             config,
             m_ozer_path.return_value,
             m_ifier_path.return_value,
             "-mode=fix",
             "-lint=fix"), {}])


def test_bazel_check_buildifier_path(patches):
    bazel = check.abstract.bazel.ABazelCheck("DIRECTORY")
    patched = patches(
        "ABazelCheck.command_path",
        prefix="envoy.code.check.abstract.bazel")

    with patched as (m_path, ):
        assert (
            bazel.buildifier_path
            == m_path.return_value)

    assert "buildifier_path" in bazel.__dict__
    assert (
        m_path.call_args
        == [("buildifier", ), {}])


def test_bazel_check_buildozer_path(patches):
    bazel = check.abstract.bazel.ABazelCheck("DIRECTORY")
    patched = patches(
        "ABazelCheck.command_path",
        prefix="envoy.code.check.abstract.bazel")

    with patched as (m_path, ):
        assert (
            bazel.buildozer_path
            == m_path.return_value)

    assert "buildozer_path" in bazel.__dict__
    assert (
        m_path.call_args
        == [("buildozer", ), {}])


async def test_bazel_check_checker_files(patches):
    directory = MagicMock()
    files = AsyncMock()
    directory.files = files()
    bazel = check.abstract.bazel.ABazelCheck(directory)
    patched = patches(
        ("ABazelCheck.re_path_match",
         dict(new_callable=PropertyMock)),
        "ABazelCheck.filter_files",
        prefix="envoy.code.check.abstract.bazel")

    with patched as (m_re, m_filter):
        assert (
            await bazel.checker_files
            == m_filter.return_value)

    assert (
        m_filter.call_args
        == [(files.return_value, m_re.return_value.match, bazel.exclude), {}])
    assert not (
        hasattr(
            bazel,
            check.ABazelCheck.checker_files.cache_name))


@pytest.mark.parametrize("has_files", [True, False])
async def test_bazel_check_problem_files(patches, iters, has_files):
    _files = (
        iters()
        if has_files
        else None)
    files = AsyncMock(return_value=_files)
    bazel = check.abstract.bazel.ABazelCheck("DIRECTORY")
    patched = patches(
        "dict",
        "tasks",
        ("ABazelCheck.buildifier_command",
         dict(new_callable=PropertyMock)),
        ("ABazelCheck.files",
         dict(new_callable=PropertyMock)),
        "ABazelCheck.execute",
        prefix="envoy.code.check.abstract.bazel")
    errors = iters()

    async def concurrent(jobs):
        for error in errors:
            yield error

    with patched as (m_dict, m_tasks, m_command, m_files, m_exec):
        m_files.side_effect = files
        m_tasks.concurrent.side_effect = concurrent
        assert (
            await bazel.problem_files
            == (m_dict.return_value
                if has_files
                else {})
            == getattr(
                bazel,
                check.ABazelCheck.problem_files.cache_name)[
                    "problem_files"])
        if has_files:
            taskiters = m_tasks.concurrent.call_args[0][0]
            tasklist = list(taskiters)

    if not has_files:
        assert not m_dict.called
        assert not m_tasks.concurrent.called
        assert not m_exec.called
        return
    assert (
        m_dict.call_args
        == [(), {}])
    assert type(taskiters) is types.GeneratorType
    assert (
        tasklist
        == [m_exec.return_value for f in _files])
    assert (
        m_exec.call_args_list
        == [[(m_command.return_value, f), {}]
            for f in _files])
    assert (
        m_dict.return_value.update.call_args_list
        == [[(error, ), {}]
            for error in errors])


def test_bazel_check_re_path_match(patches):
    bazel = check.abstract.bazel.ABazelCheck("DIRECTORY")
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.bazel")

    with patched as (m_re, ):
        assert (
            bazel.re_path_match
            == m_re.compile.return_value)

    assert "re_path_match" in bazel.__dict__
    assert (
        m_re.compile.call_args
        == [("|".join(check.abstract.bazel.RE_BAZEL_MATCH), ), {}])


def test_bazel_check_exclude(patches):
    config = MagicMock()
    bazel = check.abstract.bazel.ABazelCheck("DIRECTORY", config=config)
    patched = patches(
        "tuple",
        prefix="envoy.code.check.abstract.bazel")
    path = MagicMock()

    with patched as (m_tuple, ):
        assert (
            bazel.exclude(path)
            == path.startswith.return_value)

    assert (
        path.startswith.call_args
        == [(m_tuple.return_value, ), {}])
    assert (
        m_tuple.call_args
        == [(config.__getitem__.return_value.__getitem__.return_value, ), {}])
    assert (
        config.__getitem__.call_args
        == [("paths", ), {}])
    assert (
        config.__getitem__.return_value.__getitem__.call_args
        == [("excluded", ), {}])
