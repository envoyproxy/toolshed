
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import dependatool


class DummyDependatoolGomodCheck(dependatool.gomod.ADependatoolGomodCheck):
    pass


def test_gomod_abstract_check_constructor():
    check = DummyDependatoolGomodCheck("CHECKER")
    assert (
        check._gomodfile_filename
        == dependatool.gomod.abstract.GOMODFILE_FILENAME)
    assert check.checker == "CHECKER"


def test_gomod_abstract_check_config():
    checker = MagicMock()
    check = DummyDependatoolGomodCheck(checker)
    checker.config.__getitem__.return_value = [
        {"package-ecosystem": "gomod", "directory": "dir1"},
        {"package-ecosystem": "not-gomod", "directory": "dir2"},
        {"package-ecosystem": "gomod", "directory": "dir3"}]
    assert check.config == {'dir1', 'dir3'}
    assert (
        checker.config.__getitem__.call_args
        == [('updates',), {}])


@pytest.mark.parametrize(
    "matches",
    [[], range(0, 3), range(0, 5), range(3, 7)])
async def test_gomod_abstract_check_gomodfile_dirs(patches, matches):
    checker = MagicMock()
    check = DummyDependatoolGomodCheck(checker)
    patched = patches(
        "os",
        "ADependatoolGomodCheck.dir_matches",
        prefix="dependatool.gomod.abstract")
    dirs = [MagicMock() for i in range(0, 5)]
    expected = [d for i, d in enumerate(dirs) if i in matches]

    class Matcher:
        counter = 0

        def match_dirs(self, path):
            _matches = self.counter in matches
            self.counter += 1
            return _matches

    matcher = Matcher()

    with patched as (m_os, m_matches):
        m_matches.side_effect = matcher.match_dirs
        checker.directory.files = AsyncMock(return_value=dirs)()
        assert (
            await check.gomodfile_dirs
            == {m_os.path.dirname.return_value
                for f in expected}
            == getattr(
                check,
                (dependatool.ADependatoolGomodCheck
                            .gomodfile_dirs.cache_name))[
                    "gomodfile_dirs"])

    assert (
        m_matches.call_args_list
        == [[(d, ), {}] for d in dirs])

    assert (
        m_os.path.dirname.call_args_list
        == [[(f"/{m}", ), {}]
            for m in expected])


def test_gomod_abstract_check_filename(patches):
    checker = MagicMock()
    check = DummyDependatoolGomodCheck(checker)
    patched = patches(
        "re",
        prefix="dependatool.gomod.abstract")

    with patched as (m_re, ):
        assert (
            check.gomodfile_filename
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [(check._gomodfile_filename, ), {}])


TEST_REQS = (
    (set(), set()),
    (set(["A", "B"]), set()),
    (set(["A", "B"]), set(["B", "C"])),
    (set(["A", "B", "C"]), set(["A", "B", "C"])),
    (set(), set(["B", "C"])))


@pytest.mark.parametrize("gomodfile", TEST_REQS)
async def test_gomod_abstract_check_check(patches, gomodfile):
    config, dirs = gomodfile
    check = DummyDependatoolGomodCheck("CHECKER")
    patched = patches(
        ("ADependatoolGomodCheck.config",
         dict(new_callable=PropertyMock)),
        ("ADependatoolGomodCheck.gomodfile_dirs",
         dict(new_callable=PropertyMock)),
        ("ADependatoolGomodCheck.gomodfile_filename",
         dict(new_callable=PropertyMock)),
        "ADependatoolGomodCheck.success",
        "ADependatoolGomodCheck.errors",
        prefix="dependatool.gomod.abstract")

    with patched as (m_config, m_dirs, m_fname, m_success, m_errors):
        m_config.return_value = config
        m_dirs.side_effect = AsyncMock(return_value=dirs)
        assert not await check.check()

    if config & dirs:
        assert (
            m_success.call_args
            == [(config & dirs, ), {}])
    else:
        assert not m_success.called
    if config - dirs:
        assert (
            [(config - dirs,
              (f"No {m_fname.return_value.pattern} found for "
               "specified dependabot config")),
             {}]
            in list(m_errors.call_args_list))

    if dirs - config:
        assert (
            [(dirs - config,
              "Missing dependabot config for "
              f"{m_fname.return_value.pattern} in dir"),
             {}]
            in list(m_errors.call_args_list))

    if not config - dirs and not dirs - config:
        assert not m_errors.called


def test_gomod_abstract_check_errors(patches):
    checker = MagicMock()
    check = DummyDependatoolGomodCheck(checker)
    errors = set(["C", "D", "B", "A"])
    msg = "ERROR MESSAGE"
    assert not check.errors(errors, msg)
    assert (
        checker.error.call_args_list
        == [[("gomod", [f'ERROR MESSAGE: {x}']), {}]
            for x in sorted(errors)])


@pytest.mark.parametrize("name_matches", [True, False])
@pytest.mark.parametrize("dir_ignored", [True, False])
@pytest.mark.parametrize("size", [0, 1, 2, 3])
def test_gomod_abstract_check_dir_matches(
        patches, name_matches, dir_ignored, size):
    checker = MagicMock()
    check = DummyDependatoolGomodCheck(checker)
    patched = patches(
        "bool",
        "os",
        ("ADependatoolGomodCheck.gomodfile_filename",
         dict(new_callable=PropertyMock)),
        prefix="dependatool.gomod.abstract")
    path = MagicMock()

    with patched as (m_bool, m_os, m_filename):
        m_bool.return_value = name_matches
        m_os.stat.return_value.st_size = size
        checker.ignored_dirs.match.return_value = (
            True
            if dir_ignored
            else False)
        assert (
            check.dir_matches(path)
            == (name_matches
                and size > 1
                and not dir_ignored))

    assert m_os.path.basename.call_args == [(path, ), {}]
    assert (
        m_bool.call_args
        == [(m_filename.return_value.match.return_value, ), {}])
    assert (
        m_filename.return_value.match.call_args
        == [(m_os.path.basename.return_value, ), {}])
    if not name_matches:
        assert not checker.ignored_dirs.match.called
        assert not m_os.path.dirname.called
        assert not m_os.stat.called
        return
    assert (
        m_os.stat.call_args
        == [(path, ), {}])
    if size < 2:
        assert not checker.ignored_dirs.match.called
        assert not m_os.path.dirname.called
        return
    assert (
        checker.ignored_dirs.match.call_args
        == [(m_os.path.dirname.return_value, ), {}])
    assert (
        m_os.path.dirname.call_args
        == [(f"/{path}", ), {}])


def test_gomod_abstract_check_success(patches):
    checker = MagicMock()
    check = DummyDependatoolGomodCheck(checker)
    success = set(["C", "D", "B", "A"])

    patched = patches(
        ("ADependatoolGomodCheck.gomodfile_filename",
         dict(new_callable=PropertyMock)),
        prefix="dependatool.gomod.abstract")

    with patched as (m_fname, ):
        assert not check.success(success)

    assert (
        checker.succeed.call_args
        == [("gomod",
             [f"{m_fname.return_value.pattern}: {x}"
              for x in sorted(success)]),  {}])
