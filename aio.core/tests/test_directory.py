
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio.core import directory, subprocess


def test_abstract_directory_make_path_absolute(patches):
    patched = patches(
        "os",
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_os, ):
        assert (
            directory.ADirectory.make_path_absolute("ROOT_PATH", "PATH")
            == m_os.path.join.return_value)

    assert (
        m_os.path.join.call_args
        == [("ROOT_PATH", "PATH"), {}])
    assert directory.ADirectory.make_path_absolute.cache_info().misses == 1
    assert directory.ADirectory.make_path_absolute.cache_info().currsize == 1


def test_abstract_directory__make_paths_absolute(patches):
    patched = patches(
        "set",
        "ADirectory.make_path_absolute",
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_set, m_abspath):
        assert (
            directory.ADirectory._make_paths_absolute("PATH", range(0, 5))
            == m_set.return_value)
        iterator = m_set.call_args[0][0]
        assert isinstance(iterator, types.GeneratorType)
        assert (
            list(iterator)
            == [m_abspath.return_value] * 5)

    assert (
        m_set.call_args
        == [(iterator, ), {}])
    assert (
        m_abspath.call_args_list
        == [[("PATH", i), {}] for i in range(0, 5)])


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_directory_constructor(patches, args, kwargs):
    patched = patches(
        "directory.ADirectory.__init__",
        prefix="aio.core.directory.directory")

    with patched as (m_super, ):
        m_super.return_value = None
        direct = directory.Directory(*args, **kwargs)

    assert isinstance(direct, directory.ADirectory)
    assert (
        m_super.call_args
        == [tuple(args), kwargs])


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
def test_git_directory_constructor(patches, args, kwargs):
    patched = patches(
        "directory.AGitDirectory.__init__",
        prefix="aio.core.directory.directory")

    with patched as (m_super, ):
        m_super.return_value = None
        direct = directory.GitDirectory(*args, **kwargs)

    assert isinstance(direct, directory.AGitDirectory)
    assert (
        m_super.call_args
        == [tuple(args), kwargs])


@pytest.mark.parametrize("exclude", [None, 0, [], (), "EXCLUDE"])
@pytest.mark.parametrize("exclude_dirs", [None, 0, [], (), "EXCLUDE"])
@pytest.mark.parametrize("path_matcher", [None, 0, [], (), "MATCHER"])
@pytest.mark.parametrize("exclude_matcher", [None, 0, [], (), "MATCHER"])
@pytest.mark.parametrize("text_only", [None, True, False])
def test_abstract_directory_constructor(
        exclude, exclude_dirs, path_matcher,
        exclude_matcher, text_only):
    kwargs = {}
    if exclude is not None:
        kwargs["exclude"] = exclude
    if exclude_dirs is not None:
        kwargs["exclude_dirs"] = exclude_dirs
    if path_matcher is not None:
        kwargs["path_matcher"] = path_matcher
    if exclude_matcher is not None:
        kwargs["exclude_matcher"] = exclude_matcher
    if text_only is not None:
        kwargs["text_only"] = text_only

    direct = directory.ADirectory("PATH", **kwargs)
    assert direct._path == "PATH"
    assert direct.path_matcher == path_matcher
    assert direct.exclude_matcher == exclude_matcher
    assert (
        direct.text_only
        == (True if text_only is None else text_only))
    assert direct.exclude == (exclude or ())
    assert direct.exclude_dirs == (exclude_dirs or ())


async def test_abstract_directory_files(patches):
    direct = directory.ADirectory("PATH")
    patched = patches(
        ("ADirectory.grep",
         dict(new_callable=AsyncMock)),
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_grep, ):
        result = await direct.files
        assert (
            result
            == m_grep.return_value)

    assert (
        m_grep.call_args
        == [(["-l", ""], ), {}])
    assert (
        getattr(
            direct,
            directory.ADirectory.files.cache_name)[
                "files"]
        == result)


@pytest.mark.parametrize("text_only", [True, False])
def test_abstract_directory_grep_args(patches, text_only):
    direct = directory.ADirectory("PATH", text_only=text_only)
    patched = patches(
        ("ADirectory.grep_command_args",
         dict(new_callable=PropertyMock)),
        ("ADirectory.grep_exclusion_args",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")

    grep_command = [f"CMD{i}" for i in range(0, 5)]
    grep_exclusions = [f"EXC{i}" for i in range(0, 5)]
    text_flag = (
        ("-I", )
        if text_only
        else ())
    expected = (*grep_command, *text_flag, *grep_exclusions)

    with patched as (m_cmd, m_exc):
        m_cmd.return_value = grep_command
        m_exc.return_value = grep_exclusions
        assert (
            direct.grep_args
            == expected)

    assert "grep_args" in direct.__dict__


@pytest.mark.parametrize("grep", [None, "GREP"])
def test_abstract_directory_grep_command_args(patches, grep):
    direct = directory.ADirectory("PATH")
    patched = patches(
        "shutil",
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_shutil, ):
        m_shutil.which.return_value = grep
        if not grep:
            with pytest.raises(subprocess.exceptions.OSCommandError) as e:
                direct.grep_command_args
            assert e.value.args[0] == "Unable to find `grep` command"
        else:
            assert (
                direct.grep_command_args
                == ("GREP", "-r"))

    assert (
        m_shutil.which.call_args
        == [("grep", ), {}])
    assert "grep_command_args" not in direct.__dict__


@pytest.mark.parametrize("exclude", [[], range(0, 5), ["a", "b", "c"]])
@pytest.mark.parametrize("exclude_dirs", [[], range(0, 5), ["a", "b", "c"]])
def test_abstract_directory_grep_exclusion_args(exclude, exclude_dirs):
    direct = directory.ADirectory(
        "PATH", exclude=exclude, exclude_dirs=exclude_dirs)
    expected = []
    for x in exclude:
        expected.append(f"--exclude={x}")
    for x in exclude_dirs:
        expected.append(f"--exclude-dir={x}")

    assert direct.grep_exclusion_args == tuple(expected)
    assert "grep_exclusion_args" not in direct.__dict__


def test_abstract_directory_path(patches):
    direct = directory.ADirectory("PATH")
    patched = patches(
        "pathlib",
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_plib, ):
        assert direct.path == m_plib.Path.return_value

    assert (
        m_plib.Path.call_args
        == [("PATH", ), {}])
    assert "path" in direct.__dict__


def test_abstract_directory_shell(patches):
    direct = directory.ADirectory("PATH")
    patched = patches(
        "subprocess",
        ("ADirectory.loop",
         dict(new_callable=PropertyMock)),
        ("ADirectory.path",
         dict(new_callable=PropertyMock)),
        ("ADirectory.pool",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_sub, m_loop, m_path, m_pool):
        assert direct.shell == m_sub.AsyncShell.return_value

    assert (
        m_sub.AsyncShell.call_args
        == [(),
            dict(cwd=m_path.return_value,
                 loop=m_loop.return_value,
                 pool=m_pool.return_value)])
    assert "shell" in direct.__dict__


def test_abstract_directory_absolute_path(patches):
    direct = directory.ADirectory("PATH")
    patched = patches(
        "str",
        ("ADirectory.path",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_str, m_path):
        assert direct.absolute_path == m_str.return_value

    assert (
        m_str.call_args
        == [(m_path.return_value.resolve.return_value, ), {}])
    assert (
        m_path.return_value.resolve.call_args
        == [(), {}])
    assert "absolute_path" in direct.__dict__


def test_abstract_directory_grep(patches):
    direct = directory.ADirectory("PATH")
    patched = patches(
        "async_set",
        "AwaitableGenerator",
        "ADirectory._grep",
        "ADirectory._include_file",
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_set, m_gen, m_grep, m_include):
        assert (
            direct.grep("ARGS", "TARGET")
            == m_gen.return_value)

    assert (
        m_gen.call_args
        == [(m_grep.return_value, ),
            dict(collector=m_set, predicate=m_include)])
    assert (
        m_grep.call_args
        == [("ARGS", "TARGET"), {}])


async def test_abstract_directory_paths_absolute(patches):
    direct = directory.ADirectory("PATH")
    patched = patches(
        ("ADirectory.absolute_path",
         dict(new_callable=PropertyMock)),
        ("ADirectory.execute",
         dict(new_callable=AsyncMock)),
        "ADirectory._make_paths_absolute",
        prefix="aio.core.directory.abstract.directory")
    paths = MagicMock()

    with patched as (m_path, m_execute, m_abs):
        assert (
            await direct.make_paths_absolute(paths)
            == m_execute.return_value)

    assert (
        m_execute.call_args
        == [(m_abs, m_path.return_value, paths),
            {}])


@pytest.mark.parametrize("target", [0, False, None, "TARGET"])
def test_abstract_directory_parse_grep_args(patches, target):
    direct = directory.ADirectory("PATH")
    patched = patches(
        ("ADirectory.grep_args",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")

    grep_args = [f"GARG{i}" for i in range(0, 5)]
    args = [f"ARG{i}" for i in range(0, 5)]
    target_arg = (
        (target, )
        if target is not None
        else ())
    expected = (*grep_args, *args, *target_arg)

    with patched as (m_grep_args, ):
        m_grep_args.return_value = grep_args
        assert (
            direct.parse_grep_args(args, *target_arg)
            == expected)


def test_abstract_directory_relative_path(patches):
    direct = directory.ADirectory("PATH")
    patched = patches(
        "len",
        ("ADirectory.absolute_path",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")
    path = MagicMock()

    with patched as (m_len, m_path):
        m_len.return_value = 22
        assert (
            direct.relative_path(path)
            == path.__getitem__.return_value)

    assert (
        m_len.call_args
        == [(m_path.return_value, ), {}])
    assert (
        path.__getitem__.call_args
        == [(slice(23, None), ), {}])
    assert direct.relative_path.cache_info().misses == 1
    assert direct.relative_path.cache_info().currsize == 1


def test_abstract_directory_relative_paths(patches):
    direct = directory.ADirectory("PATH")
    patched = patches(
        "ADirectory.relative_path",
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_relpath, ):
        m_relpath.side_effect = lambda i: f"PATH{i}"
        assert (
            direct.relative_paths(range(0, 5))
            == set(f"PATH{i}" for i in range(0, 5)))

    assert (
        m_relpath.call_args_list
        == [[(i, ), {}] for i in range(0, 5)])


@pytest.mark.parametrize(
    "raises",
    [None, Exception, subprocess.exceptions.RunError])
@pytest.mark.parametrize("returncode", [None, 0, False, 1, 2])
@pytest.mark.parametrize("stdout", [True, False])
@pytest.mark.parametrize("stderr", [True, False])
async def test_abstract_directory__grep(
        patches, raises, returncode, stdout, stderr):
    direct = directory.ADirectory("PATH")
    patched = patches(
        ("ADirectory.shell",
         dict(new_callable=PropertyMock)),
        "ADirectory.parse_grep_args",
        prefix="aio.core.directory.abstract.directory")
    results = []
    items = [str(i) for i in range(0, 5)] + [0, None, (), ""]
    error = MagicMock()
    error.returncode = returncode
    error.stdout = stdout
    error.stderr = stderr

    with patched as (m_shell, m_parse):
        shell_mock = AsyncMock(return_value=items)
        m_shell.return_value.side_effect = shell_mock
        if raises:
            raised = raises(
                "AN ERROR OCCURRED", error)
            shell_mock.side_effect = raised

        if raises == Exception:
            with pytest.raises(Exception) as e:
                async for result in direct._grep("ARGS", "TARGET"):
                    pass
            assert e.value is raised
        elif raises and (returncode != 1 or stdout or stderr):
            with pytest.raises(subprocess.exceptions.RunError) as e:
                async for result in direct._grep("ARGS", "TARGET"):
                    pass
            assert e.value is raised
        else:
            async for result in direct._grep("ARGS", "TARGET"):
                results.append(result)

    assert (
        m_shell.return_value.call_args
        == [(m_parse.return_value, ), {}])
    assert (
        results
        == ([str(i) for i in range(0, 5)]
            if not raises
            else []))
    assert (
        m_parse.call_args
        == [("ARGS", "TARGET"), {}])


@pytest.mark.parametrize("matcher", [True, False])
@pytest.mark.parametrize("matcher_matches", [True, False])
@pytest.mark.parametrize("exclude", [True, False])
@pytest.mark.parametrize("exclude_matches", [True, False])
def test_abstract_directory__include_file(
        matcher, matcher_matches, exclude, exclude_matches):
    kwargs = {}
    if matcher:
        kwargs["path_matcher"] = MagicMock()
        kwargs["path_matcher"].match.return_value = matcher_matches
    if exclude:
        kwargs["exclude_matcher"] = MagicMock()
        kwargs["exclude_matcher"].match.return_value = exclude_matches

    direct = directory.ADirectory("PATH", **kwargs)
    assert (
        direct._include_file("PATH")
        == ((not matcher or matcher_matches)
            and (not exclude or not exclude_matches)))


@pytest.mark.parametrize(
    "args",
    [[], [f"ARG{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "kwargs",
    [{}, {f"K{i}": f"V{i}" for i in range(0, 5)}])
@pytest.mark.parametrize("changed", [None, True, False])
def test_abstract_git_directory_constructor(patches, args, kwargs, changed):
    patched = patches(
        "directory.ADirectory.__init__",
        prefix="aio.core.directory.directory")
    if changed is not None:
        kwargs["changed"] = changed

    with patched as (m_super, ):
        m_super.return_value = None
        direct = directory.AGitDirectory(*args, **kwargs)

    kwargs.pop("changed", None)
    assert isinstance(direct, directory.ADirectory)
    assert (
        m_super.call_args
        == [tuple(args), kwargs])
    assert direct.changed == changed


async def test_abstract_git_directory_changed_files(patches):
    direct = directory.AGitDirectory("PATH", changed="CHANGED")
    patched = patches(
        ("AGitDirectory.git_command",
         dict(new_callable=PropertyMock)),
        ("AGitDirectory.shell",
         dict(new_callable=PropertyMock)),
        "AGitDirectory._include_file",
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_command, m_shell, m_include):
        m_include.side_effect = lambda x: x % 2
        m_shell.return_value.side_effect = AsyncMock(
            return_value=(
                [None, "", False]
                + list(range(0, 10))
                + list(range(0, 10))))
        result = await direct.changed_files
        assert (
            result
            == set(i for i in range(0, 10) if i % 2))

    assert (
        m_shell.return_value.call_args
        == [([m_command.return_value,
              "diff",
              "--name-only",
              "CHANGED",
              "--diff-filter=ACMR",
              "--ignore-submodules=all"], ),
            {}])
    assert (
        m_include.call_args_list
        == [[(i, ), {}]
            for i
            in (list(range(1, 10))
                + list(range(1, 10)))])
    assert (
        getattr(
            direct,
            directory.AGitDirectory.changed_files.cache_name)[
                "changed_files"]
        == result)


@pytest.mark.parametrize("changed", [True, False])
async def test_abstract_git_directory_files(patches, changed):
    direct = directory.AGitDirectory(
        "PATH",
        changed=changed)
    patched = patches(
        "AGitDirectory.get_changed_files",
        "AGitDirectory.get_files",
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_changed_files, m_files):
        result = await direct.files
        assert (
            result
            == (m_changed_files.return_value
                if changed
                else m_files.return_value)
            == getattr(
                direct,
                directory.AGitDirectory.files.cache_name)[
                    "files"])

    if changed:
        assert not m_files.called
    else:
        assert not m_changed_files.called


@pytest.mark.parametrize(
    "files",
    [set(),
     set(f"F{i}" for i in range(0, 5)),
     set(f"F{i}" for i in range(0, 10))])
@pytest.mark.parametrize(
    "changed_files",
    [set(),
     set(f"F{i}" for i in range(0, 5)),
     set(f"F{i}" for i in range(0, 10))])
@pytest.mark.parametrize("path_matcher", [None, "PATH_MATCHER"])
@pytest.mark.parametrize("exclude_matcher", [None, "EXCLUDE_MATCHER"])
async def test_abstract_git_directory_get_changed_files(
        patches, files, changed_files, path_matcher, exclude_matcher):
    direct = directory.AGitDirectory(
        "PATH",
        path_matcher=path_matcher,
        exclude_matcher=exclude_matcher)
    patched = patches(
        "set",
        ("AGitDirectory.changed_files",
         dict(new_callable=PropertyMock)),
        "ADirectory.get_files",
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_set, m_changed, m_files):
        m_files.return_value = files
        m_changed.side_effect = AsyncMock(return_value=changed_files)
        result = await direct.get_changed_files()
        empty_set = False
        if (path_matcher or exclude_matcher):
            if not files:
                empty_set = True
        elif not changed_files:
            empty_set = True
        assert (
            result
            == (m_set.return_value
                if empty_set
                else files & changed_files))

    if (path_matcher or exclude_matcher) and not files:
        assert not m_changed.called
        assert (
            m_files.call_args_list
            == [[(), {}]])
    elif not (path_matcher or exclude_matcher) and not changed_files:
        assert not m_files.called
        assert (
            m_changed.call_args
            == [(), {}])
    else:
        assert (
            m_files.call_args_list
            == [[(), {}]])
        assert (
            m_changed.call_args
            == [(), {}])


@pytest.mark.parametrize("git", [None, "GIT"])
def test_abstract_git_directory_git_command(patches, git):
    direct = directory.AGitDirectory("PATH")
    patched = patches(
        "shutil",
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_shutil, ):
        m_shutil.which.return_value = git
        if not git:
            with pytest.raises(subprocess.exceptions.OSCommandError) as e:
                direct.git_command
            assert e.value.args[0] == "Unable to find the `git` command"
        else:
            assert (
                direct.git_command
                == git)

    assert (
        m_shutil.which.call_args
        == [("git", ), {}])
    assert "git_command" not in direct.__dict__


@pytest.mark.parametrize("git", [None, "GIT"])
def test_abstract_git_directory_grep_command_args(patches, git):
    direct = directory.AGitDirectory("PATH")
    patched = patches(
        ("AGitDirectory.git_command",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_command, ):
        assert (
            direct.grep_command_args
            == (m_command.return_value, "grep", "--cached"))

    assert "grep_command_args" not in direct.__dict__
