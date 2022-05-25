
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio.core import directory

from envoy.code import check


async def test_glint_no_newlines(iters, patches):
    patched = patches(
        "NewlineChecker",
        prefix="envoy.code.check.abstract.glint")
    path = MagicMock()
    paths = iters(cb=lambda i: MagicMock(), count=3)

    with patched as (m_newlines, ):
        assert (
            check.AGlintCheck.no_newlines(path, *paths)
            == m_newlines.return_value.no_newlines.return_value)

    assert (
        m_newlines.call_args
        == [(path, ), {}])
    assert (
        m_newlines.return_value.no_newlines.call_args
        == [(tuple(paths), ), {}])


def test_glint_constructor():
    glint = check.AGlintCheck("DIRECTORY")
    assert glint.directory == "DIRECTORY"


@pytest.mark.parametrize("files", [True, False])
async def test_glint_checker_files(patches, files):
    directory = MagicMock()
    glint = check.AGlintCheck(directory)
    patched = patches(
        "set",
        ("AGlintCheck.noglint_re",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.glint")
    files = AsyncMock(return_value=range(0, 20))
    directory.files = files()

    with patched as (m_set, m_re):
        m_re.return_value.match.side_effect = lambda x: x % 2
        assert (
            await glint.checker_files
            == m_set.return_value)
        iterator = m_set.call_args[0][0]
        called = list(iterator)

    assert (
        called
        == [x for x in range(0, 20)
            if not x % 2])
    assert (
        m_re.return_value.match.call_args_list
        == [[(x, ), {}] for x in range(0, 20)])
    assert not (
        hasattr(
            glint,
            check.AGlintCheck.checker_files.cache_name))


async def test_glint_files_with_mixed_tabs(patches):
    directory = MagicMock()
    glint = check.AGlintCheck(directory)
    patched = patches(
        ("AGlintCheck.files_with_preceeding_tabs",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.glint")
    directory.grep = AsyncMock()

    with patched as (m_tabs, ):
        tabs = AsyncMock()
        m_tabs.side_effect = tabs
        assert (
            await glint.files_with_mixed_tabs
            == directory.grep.return_value)

    assert (
        directory.grep.call_args
        == [(["-lP", r"^ "], ),
            dict(target=tabs.return_value)])
    assert not (
        hasattr(
            glint,
            check.AGlintCheck.files_with_mixed_tabs.cache_name))


async def test_glint_files_with_preceeding_tabs(patches):
    directory = MagicMock()
    glint = check.AGlintCheck(directory)
    patched = patches(
        ("AGlintCheck.files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.glint")
    directory.grep = AsyncMock()

    with patched as (m_files, ):
        files = AsyncMock()
        m_files.side_effect = files
        assert (
            await glint.files_with_preceeding_tabs
            == directory.grep.return_value)

    assert (
        directory.grep.call_args
        == [(["-lP", r"^\t"], ),
            dict(target=files.return_value)])
    assert not (
        hasattr(
            glint,
            check.AGlintCheck.files_with_preceeding_tabs.cache_name))


async def test_glint_files_with_no_newline(patches):
    directory = MagicMock()
    glint = check.AGlintCheck(directory)
    patched = patches(
        "partial",
        ("AGlintCheck.files",
         dict(new_callable=PropertyMock)),
        "AGlintCheck.execute_in_batches",
        "AGlintCheck.no_newlines",
        prefix="envoy.code.check.abstract.glint")
    batched = [
        set(x for x in range(0, 10)),
        set(x for x in range(1, 7)),
        set(x for x in range(5, 13))]
    expected = batched[0] | batched[1] | batched[2]

    async def batch_iter(x):
        for batch in batched:
            yield batch

    with patched as (m_partial, m_files, m_execute, m_newlines):
        m_files.side_effect = AsyncMock(
            [f"FILE{i}" for i in range(0, 5)])
        m_execute.side_effect = batch_iter
        assert (
            await glint.files_with_no_newline
            == expected)

    assert not (
        hasattr(
            glint,
            check.AGlintCheck.files_with_no_newline.cache_name))
    assert (
        m_execute.call_args
        == [(m_partial.return_value, *m_files.return_value), {}])
    assert (
        m_partial.call_args
        == [(m_newlines, directory.path), {}])


async def test_glint__check_problems(patches):
    glint = check.AGlintCheck("DIRECTORY")
    patched = patches(
        "list",
        "AGlintCheck._check_path",
        prefix="envoy.code.check.abstract.glint")
    batched = [
        set(x for x in range(0, 10)),
        set(x for x in range(1, 7)),
        set(x for x in range(5, 13))]
    expected = batched[0] | batched[1] | batched[2]

    with patched as (m_list, m_check):
        assert (
            await glint._check_problems(batched)
            == {p: m_list.return_value
                for p in expected})

    assert (
        m_list.call_args_list
        == [[(m_check.return_value, ), {}]
            for p
            in expected])
    assert (
        m_check.call_args_list
        == [[(p, *batched), {}]
            for p
            in expected])


@pytest.mark.parametrize("files", [[], [f"F{i}" for i in range(0, 5)]])
async def test_glint_files_with_trailing_whitespace(patches, files):
    directory = MagicMock()
    glint = check.AGlintCheck(directory)
    patched = patches(
        ("AGlintCheck.files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.glint")
    directory.grep = AsyncMock()

    with patched as (m_files, ):
        files = AsyncMock()
        m_files.side_effect = files
        assert (
            await glint.files_with_trailing_whitespace
            == directory.grep.return_value)

    assert (
        directory.grep.call_args
        == [(["-lE", r"[[:blank:]]$"], ),
            dict(target=files.return_value)])
    assert not (
        hasattr(
            glint,
            check.AGlintCheck.files_with_trailing_whitespace.cache_name))


def test_glint_noglint_re(patches):
    glint = check.AGlintCheck("DIRECTORY")
    patched = patches(
        "re",
        prefix="envoy.code.check.abstract.glint")

    with patched as (m_re, ):
        assert (
            glint.noglint_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [("|".join(check.abstract.glint.NOGLINT_RE), ),
            {}])
    assert "noglint_re" in glint.__dict__


@pytest.mark.parametrize("files", [True, False])
async def test_glint_problem_files(patches, files):
    glint = check.AGlintCheck("DIRECTORY")
    patched = patches(
        "asyncio",
        ("AGlintCheck.files",
         dict(new_callable=PropertyMock)),
        ("AGlintCheck.files_with_no_newline",
         dict(new_callable=PropertyMock)),
        ("AGlintCheck.files_with_mixed_tabs",
         dict(new_callable=PropertyMock)),
        ("AGlintCheck.files_with_trailing_whitespace",
         dict(new_callable=PropertyMock)),
        "AGlintCheck._check_problems",
        prefix="envoy.code.check.abstract.glint")

    with patched as patchy:
        (m_asyncio, m_files, m_newline, m_tabs,
         m_ws, m_checks) = patchy
        m_files.side_effect = AsyncMock(return_value=files)
        gather = AsyncMock()
        m_asyncio.gather = gather
        assert (
            await glint.problem_files
            == (m_checks.return_value
                if files
                else {})
            == getattr(
                glint,
                check.AGlintCheck.problem_files.cache_name)[
                    "problem_files"])

    if not files:
        assert not m_checks.called
        assert not gather.called
        assert not m_newline.called
        assert not m_tabs.called
        assert not m_ws.called
        return
    assert (
        m_checks.call_args
        == [(gather.return_value, ), {}])
    assert (
        gather.call_args
        == [(m_newline.return_value,
             m_tabs.return_value,
             m_ws.return_value), {}])


@pytest.mark.parametrize(
    "newline", [[], ["PATH", "other"], ["PATH"], ["no", "path"]])
@pytest.mark.parametrize(
    "mixed_tabs", [[], ["PATH", "other"], ["PATH"], ["no", "path"]])
@pytest.mark.parametrize(
    "whitespace", [[], ["PATH", "other"], ["PATH"], ["no", "path"]])
def test_glint__check_path(patches, newline, mixed_tabs, whitespace):
    glint = check.AGlintCheck("DIRECTORY")
    expected = []
    if "PATH" in newline:
        expected.append("Missing final newline: PATH")
    if "PATH" in mixed_tabs:
        expected.append("Mixed preceeding tabs and whitespace: PATH")
    if "PATH" in whitespace:
        expected.append("Trailing whitespace: PATH")
    assert (
        list(glint._check_path("PATH", newline, mixed_tabs, whitespace))
        == expected)


def test_glint_newline_checker_constructor():
    nl_checker = check.abstract.glint.NewlineChecker("PATH")
    assert isinstance(nl_checker, directory.IDirectoryContext)
    assert isinstance(nl_checker, directory.ADirectoryContext)


@pytest.mark.parametrize("n", range(1, 5))
def test_glint_newline_checker_no_newlines(patches, n):
    nl_checker = check.abstract.glint.NewlineChecker("PATH")
    patched = patches(
        "set",
        ("NewlineChecker.in_directory",
         dict(new_callable=PropertyMock)),
        "utils",
        prefix="envoy.code.check.abstract.glint")
    paths = [MagicMock() for x in range(0, 5)]

    class Byter:
        counter = 0

        def last_n_bytes_of(self, target):
            self.counter += 1
            if self.counter % n:
                return b"\n"
            return "OTHER"

    byter = Byter()

    with patched as (m_set, m_dir_ctx, m_utils):
        m_utils.last_n_bytes_of.side_effect = byter.last_n_bytes_of
        assert (
            nl_checker.no_newlines(paths)
            == m_set.return_value)
        pathgen = m_set.call_args[0][0]
        assert isinstance(pathgen, types.GeneratorType)
        assert (
            list(pathgen)
            == [p
                for i, p
                in enumerate(paths)
                if not bool((i + 1) % n)])

    assert m_dir_ctx.return_value.__enter__.called
    assert (
        m_utils.last_n_bytes_of.call_args_list
        == [[(p, ), {}]
            for p in paths])
