
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import abstracts

from aio.core import directory, subprocess


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


@abstracts.implementer(directory.ADirectory)
class DummyDirectory:

    @property
    def directory_grepper_class(self):
        return super().directory_grepper_class


@abstracts.implementer(directory.AGitDirectory)
class DummyGitDirectory:

    @property
    def directory_grepper_class(self):
        return super().directory_grepper_class


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
    with pytest.raises(TypeError):
        directory.ADirectory(**kwargs)
    direct = DummyDirectory("PATH", **kwargs)
    assert direct._path == "PATH"
    assert direct.path_matcher == path_matcher
    assert direct.exclude_matcher == exclude_matcher
    assert (
        direct.text_only
        == (True if text_only is None else text_only))
    assert direct.exclude == (exclude or ())
    assert direct.exclude_dirs == (exclude_dirs or ())
    assert (
        direct.grep_max_batch_size
        == directory.abstract.directory.GREP_MAX_BATCH_SIZE)
    assert "grep_max_batch_size" not in direct.__dict__
    assert (
        direct.grep_min_batch_size
        == directory.abstract.directory.GREP_MIN_BATCH_SIZE)
    assert "grep_min_batch_size" not in direct.__dict__
    iface_props = ["directory_grepper_class"]
    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(direct, prop)


async def test_abstract_directory_files(patches):
    direct = DummyDirectory("PATH")
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
        == [(["-l"], ""), {}])
    assert (
        getattr(
            direct,
            directory.ADirectory.files.cache_name)[
                "files"]
        == result)


@pytest.mark.parametrize("text_only", [True, False])
def test_abstract_directory_grep_args(patches, text_only):
    direct = DummyDirectory("PATH", text_only=text_only)
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
    direct = DummyDirectory("PATH")
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
    direct = DummyDirectory(
        "PATH", exclude=exclude, exclude_dirs=exclude_dirs)
    expected = []
    for x in exclude:
        expected.append(f"--exclude={x}")
    for x in exclude_dirs:
        expected.append(f"--exclude-dir={x}")

    assert direct.grep_exclusion_args == tuple(expected)
    assert "grep_exclusion_args" not in direct.__dict__


def test_abstract_directory_grepper(patches):
    direct = DummyDirectory("PATH")
    patched = patches(
        "str",
        ("ADirectory.directory_grepper_class",
         dict(new_callable=PropertyMock)),
        ("ADirectory.path",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")
    direct.path_matcher = MagicMock()
    direct.exclude_matcher = MagicMock()

    with patched as (m_str, m_class, m_path):
        assert (
            direct.grepper
            == m_class.return_value.return_value)

    assert (
        m_class.return_value.call_args
        == [(m_str.return_value, ),
            dict(path_matcher=direct.path_matcher,
                 exclude_matcher=direct.exclude_matcher)])
    assert (
        m_str.call_args
        == [(m_path.return_value, ), {}])


def test_abstract_directory_path(patches):
    direct = DummyDirectory("PATH")
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
    direct = DummyDirectory("PATH")
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
    direct = DummyDirectory("PATH")
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
    direct = DummyDirectory("PATH")
    patched = patches(
        "async_set",
        "AwaitableGenerator",
        "ADirectory._grep",
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_set, m_gen, m_grep):
        assert (
            direct.grep("ARGS", "TARGET")
            == m_gen.return_value)

    assert (
        m_gen.call_args
        == [(m_grep.return_value, ),
            dict(collector=m_set)])
    assert (
        m_grep.call_args
        == [("ARGS", "TARGET"), {}])


@pytest.mark.parametrize("is_str", [True, False])
def test_abstract_directory_parse_grep_args(patches, is_str):
    direct = DummyDirectory("PATH")
    patched = patches(
        "isinstance",
        ("ADirectory.grep_args",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")
    grep_args = [f"GARG{i}" for i in range(0, 5)]
    args = [f"ARG{i}" for i in range(0, 5)]
    target = MagicMock()
    expected = (
        (*grep_args,
         *args),
        ((target, )
         if is_str
         else target))

    with patched as (m_inst, m_grep_args):
        m_grep_args.return_value = grep_args
        m_inst.return_value = is_str
        assert (
            direct.parse_grep_args(args, target)
            == expected)

    assert (
        m_inst.call_args
        == [(target, str), {}])


async def test_abstract_directory__grep(patches):
    direct = DummyDirectory("PATH")
    patched = patches(
        "ADirectory.parse_grep_args",
        "ADirectory._batched_grep",
        prefix="aio.core.directory.abstract.directory")
    results = []
    expected = []

    async def iter_batches(args, paths):
        for x in range(0, 7):
            batch = [
                f"ITEM.{x}.{y}"
                for y
                in range(0, 3)]
            expected.extend(batch)
            yield batch

    with patched as (m_parse, m_batched):
        m_parse.return_value = ("ARGS_", "TARGET_")
        m_batched.side_effect = iter_batches
        async for result in direct._grep("ARGS", "TARGET"):
            results.append(result)

    assert results == expected
    assert (
        m_parse.call_args
        == [("ARGS", "TARGET"), {}])
    assert (
        m_batched.call_args
        == [("ARGS_", "TARGET_"), {}])


def test_abstract_directory__batched_grep(patches):
    direct = DummyDirectory("PATH")
    patched = patches(
        "partial",
        "ADirectory.execute_in_batches",
        ("ADirectory.grepper",
         dict(new_callable=PropertyMock)),
        ("ADirectory.grep_max_batch_size",
         dict(new_callable=PropertyMock)),
        ("ADirectory.grep_min_batch_size",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")
    grep_args = [f"GARG{i}" for i in range(0, 5)]
    paths = [f"PATH{i}" for i in range(0, 5)]
    direct.exclude_matcher = MagicMock()
    direct.path_matcher = MagicMock()

    with patched as patchy:
        (m_partial, m_exec,
         m_grepper, m_max, m_min) = patchy
        assert (
            direct._batched_grep(grep_args, paths)
            == m_exec.return_value)

    assert (
        m_exec.call_args
        == [(m_partial.return_value, *paths),
            dict(min_batch_size=m_min.return_value,
                 max_batch_size=m_max.return_value)])
    assert (
        m_partial.call_args
        == [(m_grepper.return_value,
             *grep_args)])


@pytest.mark.parametrize("matcher", [True, False])
@pytest.mark.parametrize("matcher_matches", [True, False])
@pytest.mark.parametrize("exclude", [True, False])
@pytest.mark.parametrize("exclude_matches", [True, False])
def __test_abstract_directory__include_file(
        matcher, matcher_matches, exclude, exclude_matches):
    kwargs = {}
    if matcher:
        kwargs["path_matcher"] = MagicMock()
        kwargs["path_matcher"].match.return_value = matcher_matches
    if exclude:
        kwargs["exclude_matcher"] = MagicMock()
        kwargs["exclude_matcher"].match.return_value = exclude_matches

    direct = DummyDirectory("PATH", **kwargs)
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
        with pytest.raises(TypeError):
            directory.AGitDirectory(*args, **kwargs)
        direct = DummyGitDirectory(*args, **kwargs)

    kwargs.pop("changed", None)
    assert isinstance(direct, directory.ADirectory)
    assert (
        m_super.call_args
        == [tuple(args), kwargs])
    assert direct.changed == changed
    iface_props = ["directory_grepper_class"]
    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(direct, prop)


async def __test_abstract_git_directory_changed_files(patches):
    direct = DummyGitDirectory("PATH", changed="CHANGED")
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
    direct = DummyGitDirectory(
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
    direct = DummyGitDirectory(
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
    direct = DummyGitDirectory("PATH")
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
    direct = DummyGitDirectory("PATH")
    patched = patches(
        ("AGitDirectory.git_command",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_command, ):
        assert (
            direct.grep_command_args
            == (m_command.return_value, "grep", "--cached"))

    assert "grep_command_args" not in direct.__dict__
