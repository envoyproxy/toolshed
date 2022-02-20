
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from envoy.code import check


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


@pytest.mark.parametrize("files", [[], [f"F{i}" for i in range(0, 5)]])
async def test_glint_files_with_mixed_tabs(patches, files):
    directory = MagicMock()
    glint = check.AGlintCheck(directory)
    patched = patches(
        "set",
        ("AGlintCheck.files_with_preceeding_tabs",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.glint")
    directory.grep = AsyncMock()

    with patched as (m_set, m_tabs):
        m_tabs.side_effect = AsyncMock(return_value=files)
        assert (
            await glint.files_with_mixed_tabs
            == (directory.grep.return_value
                if files
                else m_set.return_value))

    if files:
        assert not m_set.called
        assert (
            directory.grep.call_args
            == [(["-lP", r"^ ", *files], ), {}])
    else:
        assert m_set.call_args == [(), {}]
        assert not directory.grep.called
    assert not (
        hasattr(
            glint,
            check.AGlintCheck.files_with_mixed_tabs.cache_name))


@pytest.mark.parametrize("files", [[], [f"F{i}" for i in range(0, 5)]])
async def test_glint_files_with_preceeding_tabs(patches, files):
    directory = MagicMock()
    glint = check.AGlintCheck(directory)
    patched = patches(
        "set",
        ("AGlintCheck.files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.glint")
    directory.grep = AsyncMock()

    with patched as (m_set, m_tabs):
        m_tabs.side_effect = AsyncMock(return_value=files)
        assert (
            await glint.files_with_preceeding_tabs
            == (directory.grep.return_value
                if files
                else m_set.return_value))

    if files:
        assert not m_set.called
        assert (
            directory.grep.call_args
            == [(["-lP", r"^\t", *files], ), {}])
    else:
        assert m_set.call_args == [(), {}]
        assert not directory.grep.called
    assert not (
        hasattr(
            glint,
            check.AGlintCheck.files_with_preceeding_tabs.cache_name))


@pytest.mark.parametrize("files", [True, False])
async def test_glint_files_with_no_newline(patches, files):
    glint = check.AGlintCheck("DIRECTORY")
    patched = patches(
        "set",
        ("AGlintCheck.absolute_paths",
         dict(new_callable=PropertyMock)),
        ("AGlintCheck.files",
         dict(new_callable=PropertyMock)),
        "AGlintCheck.execute",
        "AGlintCheck.have_newlines",
        prefix="envoy.code.check.abstract.glint")

    with patched as (m_set, m_paths, m_files, m_execute, m_newlines):
        m_files.side_effect = AsyncMock(return_value=files)
        abs_paths = AsyncMock()
        m_paths.side_effect = abs_paths
        assert (
            await glint.files_with_no_newline
            == (m_set.return_value
                if not files
                else m_execute.return_value))

    assert not (
        hasattr(
            glint,
            check.AGlintCheck.files_with_no_newline.cache_name))
    if not files:
        assert not m_execute.called
        assert not m_paths.called
        return
    assert (
        m_execute.call_args
        == [(m_newlines, abs_paths.return_value), {}])


@pytest.mark.parametrize("files", [[], [f"F{i}" for i in range(0, 5)]])
async def test_glint_files_with_trailing_whitespace(patches, files):
    directory = MagicMock()
    glint = check.AGlintCheck(directory)
    patched = patches(
        "set",
        ("AGlintCheck.files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.glint")
    directory.grep = AsyncMock()

    with patched as (m_set, m_tabs):
        m_tabs.side_effect = AsyncMock(return_value=files)
        assert (
            await glint.files_with_trailing_whitespace
            == (directory.grep.return_value
                if files
                else m_set.return_value))

    if files:
        assert not m_set.called
        assert (
            directory.grep.call_args
            == [(["-lE", r"[[:blank:]]$", *files], ), {}])
    else:
        assert m_set.call_args == [(), {}]
        assert not directory.grep.called
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


@pytest.mark.parametrize("files", [[], [f"F{i}" for i in range(0, 10)]])
@pytest.mark.parametrize("any_problems", [True, False])
async def test_glint_problem_files(patches, files, any_problems):
    glint = check.AGlintCheck("DIRECTORY")
    patched = patches(
        "any",
        "list",
        ("AGlintCheck.problems",
         dict(new_callable=PropertyMock)),
        ("AGlintCheck.files",
         dict(new_callable=PropertyMock)),
        "AGlintCheck._check_path",
        prefix="envoy.code.check.abstract.glint")

    class DummyProblems:
        i = 0

        def to_list(self, item):
            self.i += 1
            if not (self.i - 1) % 2:
                return []
            return [f"P{i}" for i in range(0, self.i)]

    dummy_problems = DummyProblems()

    with patched as (m_any, m_list, m_probs, m_files, m_check):
        m_any.return_value = any_problems
        m_list.side_effect = dummy_problems.to_list
        m_files.side_effect = AsyncMock(return_value=files)
        m_probs.side_effect = AsyncMock(
            return_value=[f"PROB{i}" for i in range(0, 5)])
        result = await glint.problem_files

    assert (
        getattr(
            glint,
            check.AGlintCheck.problem_files.cache_name)[
                "problem_files"]
        == result)

    # files called
    if not files:
        assert not m_probs.called
        assert not m_any.called
        assert not m_list.called
        assert not m_check.called
        assert result == {}
        return
    # any called
    # problems called
    if not any_problems:
        assert not m_list.called
        assert not m_check.called
        assert result == {}
        return
    assert (
        result
        == {f"F{i}":
            [f"P{x}"
             for x
             in range(0, i + 1)]
            for i
            in range(0, 10)
            if i % 2})


async def test_glint_problems(patches):
    glint = check.AGlintCheck("DIRECTORY")
    patched = patches(
        "asyncio",
        ("AGlintCheck.files_with_no_newline",
         dict(new_callable=PropertyMock)),
        ("AGlintCheck.files_with_mixed_tabs",
         dict(new_callable=PropertyMock)),
        ("AGlintCheck.files_with_trailing_whitespace",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.glint")

    with patched as (m_aio, m_newline, m_tabs, m_ws):
        m_aio.gather = AsyncMock()
        assert (
            await glint.problems
            == m_aio.gather.return_value)

    assert (
        m_aio.gather.call_args
        == [(m_newline.return_value,
             m_tabs.return_value,
             m_ws.return_value), {}])
    assert not (
        hasattr(
            glint,
            check.AGlintCheck.problems.cache_name))


@pytest.mark.parametrize("n", range(1, 5))
def test_glint_have_newlines(patches, n):
    glint = check.AGlintCheck("DIRECTORY")
    patched = patches(
        "set",
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

    with patched as (m_set, m_utils):
        m_utils.last_n_bytes_of.side_effect = byter.last_n_bytes_of
        assert (
            glint.have_newlines(paths)
            == m_set.return_value)
        pathgen = m_set.call_args[0][0]
        assert isinstance(pathgen, types.GeneratorType)
        assert (
            list(pathgen)
            == [(p, bool((i + 1) % n))
                for i, p in enumerate(paths)])

    assert (
        m_utils.last_n_bytes_of.call_args_list
        == [[(p, ), {}]
            for p in paths])


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
