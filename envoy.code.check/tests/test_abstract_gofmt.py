
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio.core import subprocess

from envoy.code import check


def test_gofmt_constructor():
    gofmt = check.abstract.gofmt.Gofmt("PATH")
    assert isinstance(gofmt, subprocess.ISubprocessHandler)
    assert isinstance(gofmt, subprocess.ASubprocessHandler)


@pytest.mark.parametrize("diff", [True, False])
def test_gofmt_handle(patches, diff):
    gofmt = check.abstract.gofmt.Gofmt("PATH")
    response = MagicMock()
    if diff:
        response.args.__getitem__.return_value = "-d"
    patched = patches(
        "Gofmt.handle_diff",
        "Gofmt.handle_problems",
        prefix="envoy.code.check.abstract.gofmt")

    with patched as (m_diff, m_probs):
        assert (
            gofmt.handle(response)
            == (m_diff.return_value
                if diff
                else m_probs.return_value))

    assert (
        response.args.__getitem__.call_args
        == [(1, ), {}])
    if diff:
        assert not m_probs.called
        assert (
            m_diff.call_args
            == [(response, ), {}])
    else:
        assert not m_diff.called
        assert (
            m_probs.call_args
            == [(response, ), {}])


@pytest.mark.parametrize("stdout", [True, False])
@pytest.mark.parametrize("failure", [None, "extra", "missing"])
def test_gofmt_handle_diff(patches, iters, stdout, failure):
    gofmt = check.abstract.gofmt.Gofmt("PATH")
    response = MagicMock()
    response.stdout.__bool__.return_value = stdout
    lines = iters()
    files = iters(cb=MagicMock)
    response.stdout.splitlines.return_value = lines
    response.args.__getitem__.return_value = files
    patched = patches(
        "dict",
        "Gofmt._diff_line",
        prefix="envoy.code.check.abstract.gofmt")
    e = None

    with patched as (m_dict, m_diff):
        if failure == "missing":
            m_diff.return_value = None
        elif failure == "extra":
            m_diff.return_value = "EXTRA"
        else:
            m_diff.return_value = files[0]
        if not stdout or not failure:
            assert (
                gofmt.handle_diff(response)
                == m_dict.return_value)
        else:
            with pytest.raises(check.abstract.gofmt.GofmtError) as e:
                gofmt.handle_diff(response)

    assert (
        m_dict.call_args
        == [(), {}])
    if not stdout:
        assert not e
        assert not response.args.__getitem__.called
        assert not response.stdout.splitlines.called
        assert not m_diff.called
        return
    assert (
        response.stdout.splitlines.call_args
        == [(), {}])
    assert (
        m_diff.call_args_list[0]
        == [("", m_dict.return_value, lines[0]), {}])
    if failure == "missing":
        assert e.value.args[0] == f"Unable to parse: {response}"
    if failure == "extra":
        assert (
            e.value.args[0]
            == f"Unable to parse filename (EXTRA): {response}")
    if failure:
        assert len(m_diff.call_args_list) == 1
        return
    assert not e
    filename = ""
    for i, l in enumerate(lines):
        assert (
            m_diff.call_args_list[i]
            == [(filename, m_dict.return_value, l), {}])
        filename = m_diff.return_value


def test_gofmt_handle_error():
    gofmt = check.abstract.gofmt.Gofmt("PATH")
    response = MagicMock()
    with pytest.raises(check.abstract.gofmt.GofmtError) as e:
        gofmt.handle_error(response)

    assert e.value.args[0] == response


def test_gofmt_handle_problems(patches):
    gofmt = check.abstract.gofmt.Gofmt("PATH")
    response = MagicMock()
    patched = patches(
        "dict",
        "checker",
        prefix="envoy.code.check.abstract.gofmt")

    with patched as (m_dict, m_checker):
        assert (
            gofmt.handle_problems(response)
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(), dict(reformat=m_checker.Problems.return_value)])
    assert (
        m_checker.Problems.call_args
        == [(), dict(errors=response.stdout.splitlines.return_value)])
    assert (
        response.stdout.splitlines.call_args
        == [(), {}])


@pytest.mark.parametrize("starts", [True, False])
def test_gofmt__diff_line(patches, starts):
    gofmt = check.abstract.gofmt.Gofmt("PATH")
    result = MagicMock()
    filename = MagicMock()
    line = MagicMock()
    line.startswith.return_value = starts
    patched = patches(
        "checker",
        prefix="envoy.code.check.abstract.gofmt")

    with patched as (m_checker, ):
        assert (
            gofmt._diff_line(filename, result, line)
            == (filename
                if not starts
                else line.split.return_value.__getitem__.return_value))

    assert (
        line.startswith.call_args
        == [("diff -u", ), {}])
    if not starts:
        assert not line.split.called
        assert (
            result.__getitem__.call_args
            == [(filename, ), {}])
        assert (
            result.__getitem__.return_value.errors.__getitem__.call_args
            == [(0, ), {}])
        assert (
            (result.__getitem__.return_value
                   .errors.__getitem__.return_value
                   .__iadd__.call_args)
            == [(f"{line}\n", ), {}])
        assert not line.split.called
        assert not result.__setitem__.called
        assert not result.get.called
        assert not m_checker.Problems.called
        return
    assert not result.__getitem__.return_value.errors.__getitem__.called
    assert (
        line.split.call_args
        == [(), {}])
    assert (
        line.split.return_value.__getitem__.call_args
        == [(-1, ), {}])
    assert (
        result.__setitem__.call_args
        == [(line.split.return_value.__getitem__.return_value,
             result.get.return_value), {}])
    assert (
        result.get.call_args
        == [(line.split.return_value.__getitem__.return_value,
             m_checker.Problems.return_value), {}])
    assert (
        m_checker.Problems.call_args
        == [(),
            dict(errors=[
                "Requires reformatting: "
                f"{line.split.return_value.__getitem__.return_value}\n"
                f"{line}\n"])])


def test_gofmt_check_constructor():
    gofmt = check.AGofmtCheck("DIRECTORY")
    assert gofmt.directory == "DIRECTORY"
    assert isinstance(gofmt, check.AFileCodeCheck)


@pytest.mark.parametrize("exclude", [None, MagicMock()])
def test_gofmt_check_filter_files(patches, exclude, iters):
    gofmt = check.AGofmtCheck("DIRECTORY")
    patched = patches(
        "set",
        prefix="envoy.code.check.abstract.gofmt")
    files = iters()

    def exclude_fun(item):
        return int(item[1:]) % 2

    if exclude:
        exclude.match.side_effect = exclude_fun

    with patched as (m_set, ):
        assert (
            gofmt.filter_files(files, exclude)
            == m_set.return_value)
        resultiter = m_set.call_args[0][0]
        result = list(resultiter)

    assert isinstance(resultiter, types.GeneratorType)
    if exclude:
        assert (
            result
            == [x for x in files if not int(x[1:]) % 2])
    else:
        assert result == files


def test_gofmt_check_gofmt(patches, iters):
    gofmt = check.AGofmtCheck("DIRECTORY")
    patched = patches(
        "Gofmt",
        prefix="envoy.code.check.abstract.gofmt")
    path = MagicMock()
    args = iters()

    with patched as (m_gofmt, ):
        assert (
            gofmt.gofmt(path, *args)
            == m_gofmt.return_value.return_value)

    assert (
        m_gofmt.call_args
        == [(path, ), {}])
    assert (
        m_gofmt.return_value.call_args
        == [tuple(args), {}])


@pytest.mark.parametrize(
    "cmd",
    [["diff", "-d"],
     ["fix", "-w"],
     ["problems", "-l"]])
def test_gofmt_check_gofmt_cmds(patches, cmd):
    cmd, expected = cmd
    directory = MagicMock()
    gofmt = check.AGofmtCheck(directory)
    patched = patches(
        "AGofmtCheck._gofmt",
        prefix="envoy.code.check.abstract.gofmt")
    with patched as (m_gofmt, ):
        assert (
            getattr(gofmt, f"gofmt_{cmd}")
            == m_gofmt.return_value)

    assert (
        m_gofmt.call_args
        == [(expected, ), {}])
    assert f"gofmt_{cmd}" in gofmt.__dict__


async def test_gofmt_checker_files(patches, iters):
    directory = MagicMock()
    gofmt = check.AGofmtCheck(directory)
    patched = patches(
        "AGofmtCheck.filter_files",
        ("AGofmtCheck.go_files",
         dict(new_callable=PropertyMock)),
        ("AGofmtCheck.nogofmt_re",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.gofmt")
    files = iters()

    with patched as (m_filter, m_files, m_re):
        m_files.side_effect = AsyncMock(return_value=files)
        assert (
            await gofmt.checker_files
            == m_filter.return_value)

    assert (
        m_filter.call_args
        == [(files, m_re.return_value), {}])
    assert not (
        hasattr(
            gofmt,
            check.AGofmtCheck.checker_files.cache_name))


async def test_gofmt_fixable_files(patches, iters):
    directory = MagicMock()
    gofmt = check.AGofmtCheck(directory)
    patched = patches(
        "set",
        "AGofmtCheck.execute_in_batches",
        ("AGofmtCheck.gofmt_problems",
         dict(new_callable=PropertyMock)),
        ("AGofmtCheck.files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.gofmt")
    files = iters()
    jobs = iters(cb=lambda x: MagicMock(dict(errors=["I{x}"])))

    async def iter_jobs(x, y, *z):
        for job in jobs:
            yield job

    with patched as (m_set, m_exec, m_probs, m_files):
        m_exec.side_effect = iter_jobs
        m_files.side_effect = AsyncMock(return_value=files)
        assert (
            await gofmt.fixable_files
            == (m_set.return_value
                .__ior__.return_value
                .__ior__.return_value
                .__ior__.return_value
                .__ior__.return_value
                .__ior__.return_value)
            == getattr(
                gofmt,
                check.AGofmtCheck.fixable_files.cache_name)[
                    "fixable_files"])

    assert (
        m_exec.call_args
        == [(m_probs.return_value,) + tuple(files), {}])
    assert (
        m_set.call_args_list
        == ([[(), {}]]
            + [[(j.__getitem__.return_value.errors, ), {}]
               for j
               in jobs]))
    tset = m_set.return_value
    for i, j in enumerate(jobs):
        assert (
            tset.__ior__.call_args
            == [(m_set.return_value, ), {}])
        assert (
            j.__getitem__.call_args
            == [("reformat", ), {}])
        tset = tset.__ior__.return_value


async def test_gofmt_fixed_files(patches, iters):
    directory = MagicMock()
    gofmt = check.AGofmtCheck(directory)
    patched = patches(
        "checker",
        "AGofmtCheck.execute_in_batches",
        ("AGofmtCheck.gofmt_fix",
         dict(new_callable=PropertyMock)),
        ("AGofmtCheck.fixable_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.gofmt")
    files = iters()
    jobs = iters(cb=lambda x: MagicMock(dict(errors=["I{x}"])))

    async def iter_jobs(x, y, *z):
        for job in jobs:
            yield job

    with patched as (m_checker, m_exec, m_fix, m_files):
        m_exec.side_effect = iter_jobs
        m_files.side_effect = AsyncMock(return_value=files)
        assert (
            await gofmt.fixed_files
            == {f: m_checker.Problems.return_value
                for f in files})

    assert (
        m_exec.call_args
        == [(m_fix.return_value, ) + tuple(files), {}])
    assert (
        m_checker.Problems.call_args_list
        == [[(), dict(errors=[f"Reformatted: {f}"])]
            for f in files])
    assert not (
        hasattr(
            gofmt,
            check.AGofmtCheck.fixed_files.cache_name))


async def test_gofmt_check_go_files(patches, iters):
    directory = MagicMock()
    gofmt = check.AGofmtCheck(directory)
    patched = patches(
        "set",
        prefix="envoy.code.check.abstract.gofmt")

    def filemock(x):
        mock = MagicMock()
        mock.x = x
        mock.endswith.side_effect = lambda y: bool(x % 2)
        return mock

    files = iters(cb=filemock)
    directory.files = AsyncMock(return_value=files)()

    with patched as (m_set, ):
        assert (
            await gofmt.go_files
            == m_set.return_value)
        resultiter = m_set.call_args[0][0]
        result = list(resultiter)

    assert isinstance(resultiter, types.GeneratorType)
    assert result == [x for x in files if x.x % 2]
    for file in files:
        assert (
            file.endswith.call_args
            == [(".go", ), {}])


@pytest.mark.parametrize("binfile", [True, False])
@pytest.mark.parametrize("command", [None, False, "", "COMMAND"])
def test_gofmt_gofmt_command(patches, command, binfile):
    gofmt = check.AGofmtCheck("DIRECTORY")
    patched = patches(
        "pathlib",
        "shutil",
        ("AGofmtCheck.binaries",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.gofmt")

    with patched as (m_plib, m_shutil, m_bins):
        m_bins.return_value.__contains__.return_value = binfile
        m_shutil.which.return_value = command
        if command or binfile:
            assert (
                gofmt.gofmt_command
                == (m_plib.Path.return_value.absolute.return_value
                    if binfile
                    else command))
        else:
            with pytest.raises(subprocess.exceptions.OSCommandError) as e:
                gofmt.gofmt_command
            assert e.value.args[0] == 'Unable to find gofmt command'

    assert (
        m_bins.return_value.__contains__.call_args
        == [("gofmt", ), {}])
    if command or binfile:
        assert "gofmt_command" in gofmt.__dict__
    if binfile:
        assert not m_shutil.called
        assert (
            m_plib.Path.call_args
            == [(m_bins.return_value.__getitem__.return_value, ), {}])
        assert (
            m_bins.return_value.__getitem__.call_args
            == [("gofmt", ), {}])
        assert (
            m_plib.Path.return_value.absolute.call_args
            == [(), {}])
    else:
        assert not m_plib.Path.called
        assert not m_bins.return_value.__getitem__.called
        assert (
            m_shutil.which.call_args
            == [("gofmt", ), {}])


@pytest.mark.parametrize("nogo_re", [None, "NOGO"])
def test_gofmt_nogofmt_re(patches, nogo_re):
    gofmt = check.AGofmtCheck("DIRECTORY")
    patched = patches(
        "re",
        "NOGOFMT_RE",
        prefix="envoy.code.check.abstract.gofmt")

    with patched as (m_re, m_nogo_re):
        m_nogo_re.__bool__.return_value = bool(nogo_re)
        assert (
            gofmt.nogofmt_re
            == (m_re.compile.return_value
                if nogo_re
                else None))

    assert "nogofmt_re" in gofmt.__dict__
    if not nogo_re:
        assert not m_re.compile.called
        return
    assert (
        m_re.compile.call_args
        == [("|".join(check.abstract.gofmt.NOGOFMT_RE), ),
            {}])


@pytest.mark.parametrize("fix", [True, False])
async def test_gofmt_problem_files(patches, iters, fix):
    directory = MagicMock()
    gofmt = check.AGofmtCheck(directory)
    patched = patches(
        "dict",
        "AGofmtCheck.execute_in_batches",
        "AGofmtCheck.gofmt_diff",
        ("AGofmtCheck.files",
         dict(new_callable=PropertyMock)),
        ("AGofmtCheck.fix",
         dict(new_callable=PropertyMock)),
        ("AGofmtCheck.fixed_files",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.gofmt")
    files = iters()
    jobs = iters(cb=MagicMock)
    fixed = iters(cb=MagicMock)

    async def iter_jobs(x, y, *z):
        for i, job in enumerate(jobs):
            job.__bool__.return_value = bool(i % 2)
            yield job

    with patched as (m_dict, m_exec, m_diff, m_files, m_fix, m_fixed):
        m_fix.return_value = fix
        m_exec.side_effect = iter_jobs
        m_files.side_effect = AsyncMock(return_value=files)
        m_fixed.side_effect = AsyncMock(return_value=fixed)
        assert (
            await gofmt.problem_files
            == (fixed
                if fix
                else m_dict.return_value)
            == getattr(
                gofmt,
                check.AGofmtCheck.problem_files.cache_name)[
                    "problem_files"])

    if fix:
        assert not m_dict.return_value.update.called
        assert not m_exec.called
        return
    assert not m_fixed.called
    assert (
        m_dict.return_value.update.call_args_list
        == [[(j, ), {}]
            for i, j
            in enumerate(jobs)
            if i % 2])
    assert (
        m_exec.call_args
        == [(m_diff, ) + tuple(files), {}])


def test_gofmt__gofmt(patches, iters):
    directory = MagicMock()
    gofmt = check.AGofmtCheck(directory)
    patched = patches(
        "partial",
        "AGofmtCheck.gofmt",
        ("AGofmtCheck.gofmt_command",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.gofmt")
    args = iters()

    with patched as (m_partial, m_gofmt, m_cmd):
        assert (
            gofmt._gofmt(*args)
            == m_partial.return_value)

    assert (
        m_partial.call_args
        == [(m_gofmt,
             directory.path,
             m_cmd.return_value) + tuple(args), {}])
