
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

import dependatool


class DummyDependatoolPipCheck(dependatool.pip.ADependatoolPipCheck):
    pass


def test_pip_abstract_check_constructor():
    check = DummyDependatoolPipCheck("CHECKER")
    assert (
        check.requirements_filename
        == dependatool.pip.abstract.REQUIREMENTS_FILENAME
        == "requirements.txt")
    assert "requirements_filename" not in check.__dict__
    assert check.checker == "CHECKER"


def test_pip_abstract_check_config():
    checker = MagicMock()
    check = DummyDependatoolPipCheck(checker)
    checker.config.__getitem__.return_value = [
        {"package-ecosystem": "pip", "directory": "dir1"},
        {"package-ecosystem": "not-pip", "directory": "dir2"},
        {"package-ecosystem": "pip", "directory": "dir3"}]
    assert check.config == {'dir1', 'dir3'}
    assert (
        checker.config.__getitem__.call_args
        == [('updates',), {}])


@pytest.mark.parametrize(
    "matches",
    [[], range(0, 3), range(0, 5), range(3, 7)])
async def test_pip_abstract_check_requirements_dirs(patches, matches):
    checker = MagicMock()
    check = DummyDependatoolPipCheck(checker)
    patched = patches(
        "os",
        "ADependatoolPipCheck.dir_matches",
        prefix="dependatool.pip.abstract")
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
            await check.requirements_dirs
            == {m_os.path.dirname.return_value
                for f in expected}
            == getattr(
                check,
                dependatool.ADependatoolPipCheck.requirements_dirs.cache_name)[
                    "requirements_dirs"])

    assert (
        m_matches.call_args_list
        == [[(d, ), {}] for d in dirs])

    assert (
        m_os.path.dirname.call_args_list
        == [[(f"/{m}", ), {}]
            for m in expected])


TEST_REQS = (
    (set(), set()),
    (set(["A", "B"]), set()),
    (set(["A", "B"]), set(["B", "C"])),
    (set(["A", "B", "C"]), set(["A", "B", "C"])),
    (set(), set(["B", "C"])))


@pytest.mark.parametrize("requirements", TEST_REQS)
async def test_pip_abstract_check_check(patches, requirements):
    config, dirs = requirements
    check = DummyDependatoolPipCheck("CHECKER")
    patched = patches(
        ("ADependatoolPipCheck.config",
         dict(new_callable=PropertyMock)),
        ("ADependatoolPipCheck.requirements_dirs",
         dict(new_callable=PropertyMock)),
        ("ADependatoolPipCheck.requirements_filename",
         dict(new_callable=PropertyMock)),
        "ADependatoolPipCheck.success",
        "ADependatoolPipCheck.errors",
        prefix="dependatool.pip.abstract")

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
              (f"Missing {m_fname.return_value} dir, "
               "specified in dependabot config")),
             {}]
            in list(m_errors.call_args_list))

    if dirs - config:
        assert (
            [(dirs - config,
              f"Missing dependabot config for {m_fname.return_value} in dir"),
             {}]
            in list(m_errors.call_args_list))

    if not config - dirs and not dirs - config:
        assert not m_errors.called


def test_pip_abstract_check_errors(patches):
    checker = MagicMock()
    check = DummyDependatoolPipCheck(checker)
    errors = set(["C", "D", "B", "A"])
    msg = "ERROR MESSAGE"
    assert not check.errors(errors, msg)
    assert (
        checker.error.call_args_list
        == [[("pip", [f'ERROR MESSAGE: {x}']), {}]
            for x in sorted(errors)])


@pytest.mark.parametrize("name_matches", [True, False])
@pytest.mark.parametrize("dir_ignored", [True, False])
def test_pip_abstract_check_dir_matches(patches, name_matches, dir_ignored):
    checker = MagicMock()
    check = DummyDependatoolPipCheck(checker)
    patched = patches(
        "os",
        ("ADependatoolPipCheck.requirements_filename",
         dict(new_callable=PropertyMock)),
        prefix="dependatool.pip.abstract")
    path = MagicMock()

    with patched as (m_os, m_filename):
        if name_matches:
            m_os.path.basename.return_value = m_filename.return_value
        checker.ignored_dirs.match.return_value = (
            True
            if dir_ignored
            else False)
        assert (
            check.dir_matches(path)
            == (name_matches and not dir_ignored))

    assert m_os.path.basename.call_args == [(path, ), {}]
    if not name_matches:
        assert not checker.ignored_dirs.match.called
        assert not checker.path.parent.relative_to.called
        assert not m_os.path.dirname.called
        return
    assert (
        checker.ignored_dirs.match.call_args
        == [(m_os.path.dirname.return_value, ), {}])
    assert (
        m_os.path.dirname.call_args
        == [(f"/{path}", ), {}])


def test_pip_abstract_check_success(patches):
    checker = MagicMock()
    check = DummyDependatoolPipCheck(checker)
    success = set(["C", "D", "B", "A"])

    patched = patches(
        ("ADependatoolPipCheck.requirements_filename",
         dict(new_callable=PropertyMock)),
        prefix="dependatool.pip.abstract")

    with patched as (m_fname, ):
        assert not check.success(success)

    assert (
        checker.succeed.call_args
        == [("pip",
             [f"{m_fname.return_value}: {x}" for x in sorted(success)]),  {}])
