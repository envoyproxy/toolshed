
import types
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
    assert direct.finder_class == directory.DirectoryFileFinder


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
    assert direct.finder_class == directory.GitDirectoryFileFinder


@abstracts.implementer(directory.ADirectory)
class DummyDirectory:

    @property
    def finder_class(self):
        return super().finder_class


@abstracts.implementer(directory.AGitDirectory)
class DummyGitDirectory:

    @property
    def finder_class(self):
        return super().finder_class


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
    iface_props = ["finder_class"]
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


def test_abstract_directory_init_kwargs(patches):
    matcher = MagicMock()
    exclude = MagicMock()
    text_only = MagicMock()
    direct = DummyDirectory(
        "PATH",
        path_matcher=matcher,
        exclude_matcher=exclude,
        text_only=text_only)
    patched = patches(
        "dict",
        ("ADirectory.path",
         dict(new_callable=PropertyMock)),
        ("ADirectory.loop",
         dict(new_callable=PropertyMock)),
        ("ADirectory.pool",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_dict, m_path, m_loop, m_pool):
        assert (
            direct.init_kwargs
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(),
            dict(path=m_path.return_value,
                 path_matcher=matcher,
                 exclude_matcher=exclude,
                 text_only=text_only,
                 loop=m_loop.return_value,
                 pool=m_pool.return_value)])
    assert "init_kwargs" not in direct.__dict__


def test_abstract_finder(patches):
    direct = DummyDirectory("PATH")
    patched = patches(
        "str",
        ("ADirectory.finder_class",
         dict(new_callable=PropertyMock)),
        ("ADirectory.path",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")
    direct.path_matcher = MagicMock()
    direct.exclude_matcher = MagicMock()

    with patched as (m_str, m_class, m_path):
        assert (
            direct.finder
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


def test_abstract_directory_filtered(patches):
    direct = DummyDirectory("PATH")
    patched = patches(
        "ADirectory.__init__",
        ("ADirectory.init_kwargs",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")
    init_kwargs = {f"K{i}": f"VINIT{i}" for i in range(0, 7)}
    kwargs = {f"K{i}": f"VINIT{i}" for i in range(0, 7)}
    expected = init_kwargs.copy()
    expected.update(kwargs)

    with patched as (m_class, m_init):
        m_class.return_value = None
        m_init.return_value = init_kwargs
        assert isinstance(direct.filtered(**kwargs), DummyDirectory)

    assert (
        m_class.call_args
        == [(), expected])


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


@pytest.mark.parametrize("is_str", [True, False])
@pytest.mark.parametrize("target", [True, False])
async def test_abstract_directory__grep(patches, is_str, target):
    direct = DummyDirectory("PATH")
    patched = patches(
        "isinstance",
        "ADirectory.parse_grep_args",
        "ADirectory._batched_grep",
        prefix="aio.core.directory.abstract.directory")
    results = []
    expected = []
    target = "TARGET" if target else None

    async def iter_batches(args, paths):
        for x in range(0, 7):
            batch = [
                f"ITEM.{x}.{y}"
                for y
                in range(0, 3)]
            if is_str or target:
                expected.extend(batch)
            yield batch

    with patched as (m_isinst, m_parse, m_batched):
        m_isinst.return_value = is_str
        m_parse.return_value = ("ARGS_", "TARGET_")
        m_batched.side_effect = iter_batches
        async for result in direct._grep("ARGS", target):
            results.append(result)

    assert results == expected
    assert (
        m_isinst.call_args
        == [(target, str), {}])
    if not is_str and not target:
        assert not m_parse.called
        assert not m_batched.called
        return
    assert (
        m_parse.call_args
        == [("ARGS", target), {}])
    assert (
        m_batched.call_args
        == [("ARGS_", "TARGET_"), {}])


def test_abstract_directory__batched_grep(patches):
    direct = DummyDirectory("PATH")
    patched = patches(
        "partial",
        "ADirectory.execute_in_batches",
        ("ADirectory.finder",
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
         m_finder, m_max, m_min) = patchy
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
        == [(m_finder.return_value,
             *grep_args)])


def test_abstract_git_directory_find_git_deleted_files():
    finder = MagicMock()
    git_command = MagicMock()
    assert (
        directory.GitDirectory.find_git_deleted_files(
            finder,
            git_command)
        == finder.return_value)
    assert (
        finder.call_args
        == [(git_command,
             "ls-files",
             "--deleted"),
            {}])


def test_abstract_git_directory_find_git_files_changed_since():
    finder = MagicMock()
    git_command = MagicMock()
    since = MagicMock()
    assert (
        directory.GitDirectory.find_git_files_changed_since(
            finder,
            git_command,
            since)
        == finder.return_value)
    assert (
        finder.call_args
        == [(git_command,
             "diff",
             "--name-only",
             since,
             "--diff-filter=ACMR",
             "--ignore-submodules=all"),
            {}])


def test_abstract_git_directory_find_git_untracked_files():
    finder = MagicMock()
    git_command = MagicMock()
    assert (
        directory.GitDirectory.find_git_untracked_files(
            finder,
            git_command)
        == finder.return_value)
    assert (
        finder.call_args
        == [(git_command,
             "ls-files",
             "--others",
             "--exclude-standard",
             "--eol"),
            {}])


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
    iface_props = ["finder_class"]
    for prop in iface_props:
        with pytest.raises(NotImplementedError):
            getattr(direct, prop)


async def test_abstract_git_directory_changed_files(patches):
    direct = DummyGitDirectory("PATH", changed="CHANGED")
    patched = patches(
        "AGitDirectory.find_git_files_changed_since",
        ("AGitDirectory.finder",
         dict(new_callable=PropertyMock)),
        ("AGitDirectory.git_command",
         dict(new_callable=PropertyMock)),
        ("AGitDirectory.execute",
         dict(new_callable=AsyncMock)),
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_find, m_finder, m_command, m_execute):
        assert (
            await direct.changed_files
            == m_execute.return_value
            == getattr(
                direct,
                directory.AGitDirectory.changed_files.cache_name)[
                    "changed_files"])

    assert (
        m_execute.call_args
        == [(m_find,
             m_finder.return_value,
             m_command.return_value,
             "CHANGED"), {}])


async def test_abstract_git_directory_deleted_files(patches):
    direct = DummyGitDirectory("PATH")
    patched = patches(
        "AGitDirectory.find_git_deleted_files",
        ("AGitDirectory.finder",
         dict(new_callable=PropertyMock)),
        ("AGitDirectory.git_command",
         dict(new_callable=PropertyMock)),
        ("AGitDirectory.execute",
         dict(new_callable=AsyncMock)),
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_find, m_finder, m_command, m_execute):
        assert (
            await direct.deleted_files
            == m_execute.return_value
            == getattr(
                direct,
                directory.AGitDirectory.deleted_files.cache_name)[
                    "deleted_files"])

    assert (
        m_execute.call_args
        == [(m_find,
             m_finder.return_value,
             m_command.return_value), {}])


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
@pytest.mark.parametrize("changed", [None, "CHANGED"])
async def test_abstract_git_directory_files(
        patches, files, changed_files, path_matcher, exclude_matcher, changed):
    direct = DummyGitDirectory(
        "PATH",
        path_matcher=path_matcher,
        exclude_matcher=exclude_matcher,
        changed=changed)
    patched = patches(
        "set",
        ("AGitDirectory.changed_files",
         dict(new_callable=PropertyMock)),
        "AGitDirectory.get_files",
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_set, m_changed, m_files):
        m_files.return_value = files
        m_changed.side_effect = AsyncMock(return_value=changed_files)
        result = await direct.files
        empty_set = False
        if (path_matcher or exclude_matcher):
            if not files:
                empty_set = True
        elif not changed_files:
            empty_set = True
        expected = (
            m_files.return_value
            if not changed
            else (m_set.return_value
                  if empty_set
                  else files & changed_files))
        assert (
            result
            == expected
            == getattr(
                direct,
                directory.AGitDirectory.files.cache_name)[
                    "files"])

    if not changed:
        assert (
            m_files.call_args_list
            == [[(), {}]])
        assert not m_changed.called
        return
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


def test_abstract_git_directory_finder_kwargs(patches):
    untracked = MagicMock()
    binaries = MagicMock()
    direct = DummyGitDirectory("PATH", untracked=untracked, binaries=binaries)
    patched = patches(
        "dict",
        ("ADirectory.finder_kwargs",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")
    super_kwargs = {f"K{i}": f"V{i}" for i in range(0, 7)}

    with patched as (m_dict, m_super):
        m_super.return_value = super_kwargs
        assert (
            direct.finder_kwargs
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(),
            dict(**super_kwargs,
                 match_binaries=binaries,
                 match_all_files=untracked)])
    assert "finder_kwargs" not in direct.__dict__


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


def test_abstract_git_directory_init_kwargs(patches):
    untracked = MagicMock()
    direct = DummyGitDirectory("PATH", untracked=untracked)
    patched = patches(
        "dict",
        ("ADirectory.init_kwargs",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")
    super_kwargs = {f"K{i}": f"V{i}" for i in range(0, 7)}

    with patched as (m_dict, m_super):
        m_super.return_value = super_kwargs
        assert (
            direct.init_kwargs
            == m_dict.return_value)

    assert (
        m_dict.call_args
        == [(), dict(**super_kwargs, untracked=untracked)])
    assert "init_kwargs" not in direct.__dict__


async def test_abstract_git_directory_untracked_files(patches):
    direct = DummyGitDirectory("PATH")
    patched = patches(
        "AGitDirectory.find_git_untracked_files",
        ("AGitDirectory.finder",
         dict(new_callable=PropertyMock)),
        ("AGitDirectory.git_command",
         dict(new_callable=PropertyMock)),
        ("AGitDirectory.execute",
         dict(new_callable=AsyncMock)),
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_files, m_finder, m_git, m_exec):
        assert (
            await direct.untracked_files
            == m_exec.return_value)

    assert (
        m_exec.call_args
        == [(m_files, m_finder.return_value, m_git.return_value), {}])
    assert not hasattr(
        direct,
        directory.AGitDirectory.untracked_files.cache_name)


async def test_abstract_git_directory_get_files(patches):
    direct = DummyGitDirectory("PATH")
    patched = patches(
        "ADirectory.get_files",
        ("AGitDirectory.deleted_files",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")
    files = set([f"F{i}" for i in range(0, 10)])
    deleted = set([f"F{i}" for i in range(7, 13)])

    with patched as (m_super, m_deleted):
        m_super.return_value = files
        m_deleted.side_effect = AsyncMock(return_value=deleted)
        assert (
            await direct.get_files()
            == (files - deleted))

    assert (
        m_super.call_args
        == [(), {}])


@abstracts.implementer(directory.IDirectoryContext)
class DummyDirectoryContextInterface:

    @property
    def path(self):
        return directory.IDirectoryContext.path.fget(self)

    @property
    def in_directory(self):
        return directory.IDirectoryContext.in_directory.fget(self)


def test_directory_context_interface():
    with pytest.raises(TypeError):
        directory.IDirectoryContext()

    iface = DummyDirectoryContextInterface()

    for iface_prop in ["path", "in_directory"]:
        with pytest.raises(NotImplementedError):
            getattr(iface, iface_prop)


@abstracts.implementer(directory.ADirectoryContext)
class DummyDirectoryContext:

    @property
    def path(self):
        return super().path

    @property
    def in_directory(self):
        return super().in_directory


def test_directory_context_constructor():
    context = DummyDirectoryContext("PATH")
    assert context._path == "PATH"
    assert isinstance(context, directory.IDirectoryContext)


@pytest.mark.parametrize("path", [None, False, "", "PATH"])
def test_directory_context_path(patches, path):
    context = DummyDirectoryContext(path)
    patched = patches(
        "pathlib",
        prefix="aio.core.directory.context")

    with patched as (m_plib, ):
        assert (
            context.path
            == m_plib.Path.return_value)

    assert (
        m_plib.Path.call_args
        == [(path or ".", ), {}])
    assert "path" in context.__dict__


def test_directory_context_in_directory(patches):
    context = DummyDirectoryContext("PATH")
    patched = patches(
        "utils",
        ("ADirectoryContext.path",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.context")

    with patched as (m_utils, m_path):
        assert (
            context.in_directory
            == m_utils.directory_context.return_value)

    assert (
        m_utils.directory_context.call_args
        == [(m_path.return_value, ), {}])
    assert "in_directory" not in context.__dict__


@abstracts.implementer(directory.ADirectoryFileFinder)
class DummyDirectoryFileFinder:
    pass


@pytest.mark.parametrize("path_matcher", [None, True, False])
@pytest.mark.parametrize("exclude_matcher", [None, True, False])
def test_finder_include_matcher(path_matcher, exclude_matcher):
    path = MagicMock()
    p_match = MagicMock()
    p_match.match.return_value = path_matcher
    p_matcher = (
        p_match
        if path_matcher is not None
        else None)
    x_match = MagicMock()
    x_match.match.return_value = exclude_matcher
    x_matcher = (
        x_match
        if exclude_matcher is not None
        else None)
    expected = (
        True
        if (path_matcher is not False
            and exclude_matcher is not True)
        else False)
    assert (
        directory.ADirectoryFileFinder.include_path(path, p_matcher, x_matcher)
        == expected)
    if p_matcher:
        assert (
            p_matcher.match.call_args
            == [(path, ), {}])
    if not x_matcher:
        return
    if path_matcher is False:
        assert not x_matcher.match.called
    else:
        assert (
            x_matcher.match.call_args
            == [(path, ), {}])


@pytest.mark.parametrize("path_matcher", [None, 0, [], (), "MATCHER"])
@pytest.mark.parametrize("exclude_matcher", [None, 0, [], (), "MATCHER"])
def test_finder_constructor(patches, path_matcher, exclude_matcher):
    patched = patches(
        "_subprocess.ASubprocessHandler.__init__",
        prefix="aio.core.directory.abstract.directory")
    kwargs = {}
    if path_matcher is not None:
        kwargs["path_matcher"] = path_matcher
    if exclude_matcher is not None:
        kwargs["exclude_matcher"] = exclude_matcher
    path = MagicMock()

    with patched as (m_super, ):
        m_super.return_value = None
        finder = DummyDirectoryFileFinder(path, **kwargs)

    assert (
        m_super.call_args
        == [(finder, path, ), {}])
    assert finder.path_matcher == path_matcher
    assert finder.exclude_matcher == exclude_matcher


@pytest.mark.parametrize("n", range(1, 5))
def test_finder_handle(patches, n):
    path_matcher = MagicMock()
    exclude_matcher = MagicMock()
    finder = DummyDirectoryFileFinder(
        "PATH",
        path_matcher=path_matcher,
        exclude_matcher=exclude_matcher)
    patched = patches(
        "set",
        "_subprocess.ASubprocessHandler.handle_error",
        "ADirectoryFileFinder.include_path",
        "ADirectoryFileFinder.parse_response",
        prefix="aio.core.directory.abstract.directory")
    response = MagicMock()
    paths = [f"PATH{i}" for i in range(0, 7)]

    def include(path, *args):
        return int(path[-1]) % n

    with patched as (m_set, m_super, m_include, m_parse):
        m_parse.return_value = paths
        m_include.side_effect = include
        assert (
            finder.handle(response)
            == m_set.return_value)
        path_iter = m_set.call_args[0][0]
        assert isinstance(path_iter, types.GeneratorType)
        result = list(path_iter)

    assert (
        result
        == [p for i, p in enumerate(paths) if i % n])
    assert (
        m_parse.call_args
        == [(response, ), {}])
    assert (
        m_include.call_args_list
        == [[(p, path_matcher, exclude_matcher), {}]
            for p in paths])


def test_finder_handle_error(patches):
    finder = DummyDirectoryFileFinder("PATH")
    patched = patches(
        "_subprocess.ASubprocessHandler.handle_error",
        prefix="aio.core.directory.abstract.directory")
    response = MagicMock()

    with patched as (m_super, ):
        assert (
            finder.handle_error(response)
            == m_super.return_value)

    assert (
        m_super.call_args
        == [(response, ), {}])


def test_finder_parse_response():
    finder = DummyDirectoryFileFinder("PATH")
    response = MagicMock()
    assert (
        finder.parse_response(response)
        == response.stdout.split.return_value)
    assert (
        response.stdout.split.call_args
        == [("\n", ), {}])


@abstracts.implementer(directory.AGitDirectoryFileFinder)
class DummyGitDirectoryFileFinder:
    pass


@pytest.mark.parametrize("path_matcher", [None, 0, [], (), "MATCHER"])
@pytest.mark.parametrize("exclude_matcher", [None, 0, [], (), "MATCHER"])
@pytest.mark.parametrize("all_files", [None, True, False])
def test_git_finder_constructor(
        patches, path_matcher, exclude_matcher, all_files):
    patched = patches(
        "ADirectoryFileFinder.__init__",
        prefix="aio.core.directory.abstract.directory")
    kwargs = {}
    if path_matcher is not None:
        kwargs["path_matcher"] = path_matcher
    if exclude_matcher is not None:
        kwargs["exclude_matcher"] = exclude_matcher
    if all_files is not None:
        kwargs["match_all_files"] = all_files
    path = MagicMock()

    with patched as (m_super, ):
        m_super.return_value = None
        finder = DummyGitDirectoryFileFinder(path, **kwargs)

    assert (
        m_super.call_args
        == [(path, ),
            dict(path_matcher=path_matcher,
                 exclude_matcher=exclude_matcher)])
    assert finder.match_all_files == (all_files or False)


def test_git_finder_matcher(patches):
    finder = DummyGitDirectoryFileFinder("PATH")
    patched = patches(
        "re",
        "GIT_LS_FILES_EOL_RE",
        prefix="aio.core.directory.abstract.directory")

    with patched as (m_re, m_ls_re):
        assert (
            finder.matcher
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [(m_ls_re, ), {}])
    assert "matcher" in finder.__dict__


@pytest.mark.parametrize("all_files", [True, False])
def test_git_finder_parse_response(patches, all_files):
    finder = DummyGitDirectoryFileFinder("PATH", match_all_files=all_files)
    patched = patches(
        "ADirectoryFileFinder.parse_response",
        "AGitDirectoryFileFinder._get_file",
        prefix="aio.core.directory.abstract.directory")
    response = MagicMock()
    files = [f"F{i}" for i in range(0, 10)]
    filtered = [f"F{i}" for i in range(0, 10) if i % 2]

    def get(line):
        if int(line[1:]) % 2:
            return line

    with patched as (m_super, m_get):
        m_get.side_effect = get
        m_super.return_value = files
        assert (
            finder.parse_response(response)
            == (filtered
                if all_files
                else files))

    assert m_super.call_args == [(response, ), {}]
    if all_files:
        assert (
            m_get.call_args_list
            == [[(f, ), {}]
                for f in files])
    else:
        assert not m_get.called


@pytest.mark.parametrize("eol", [None, 0, [], (), "", "EOL", "-text", "none"])
@pytest.mark.parametrize("match_binaries", [True, False])
def test_git_finder__get_file(patches, eol, match_binaries):
    finder = DummyGitDirectoryFileFinder("PATH", match_binaries=match_binaries)
    patched = patches(
        "AGitDirectoryFileFinder._parse_line",
        prefix="aio.core.directory.abstract.directory")
    name = MagicMock()
    line = MagicMock()

    with patched as (m_parse, ):
        m_parse.return_value = eol, name
        assert (
            finder._get_file(line)
            == (name
                if (eol
                    and (
                        match_binaries
                        or eol not in ["-text", "none"]))
                else None))


@pytest.mark.parametrize("matched", [True, False])
def test_git_finder__parse_line(patches, matched):
    finder = DummyGitDirectoryFileFinder("PATH")
    patched = patches(
        ("AGitDirectoryFileFinder.matcher",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.directory.abstract.directory")
    line = MagicMock()
    _matched = MagicMock() if matched else None

    with patched as (m_matcher, ):
        m_matcher.return_value.match.return_value = _matched
        assert (
            finder._parse_line(line)
            == (_matched.groups.return_value
                if matched
                else (None, None)))

    if matched:
        assert (
            _matched.groups.call_args
            == [(), {}])


def test_directory_utils_directory_context(patches):
    patched = patches(
        "pathlib",
        "os",
        prefix="aio.core.directory.utils")
    path = MagicMock()
    tracker = MagicMock()

    with patched as (m_plib, m_os):
        m_os.chdir.side_effect = lambda path: tracker(f"PATH: {path}")
        abspath = MagicMock(
            side_effect=lambda: (23 if tracker("ABSPATH") else None))
        m_plib.Path.return_value.absolute = abspath
        with directory.utils.directory_context(path):
            tracker("IN CONTEXT")

    assert (
        m_plib.Path.call_args
        == [(), {}])
    assert (
        abspath.call_args
        == [(), {}])
    assert (
        [x[0][0] for x in tracker.call_args_list]
        == ['ABSPATH',
            f"PATH: {path}",
            'IN CONTEXT',
            "PATH: 23"])
