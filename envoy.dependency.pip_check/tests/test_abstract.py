from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from envoy.dependency import pip_check


class DummyPipChecker(pip_check.APipChecker):

    @property
    def path(self):
        return super().path


def test_abstract_pip_checker_constructor():
    checker = DummyPipChecker("path1", "path2", "path3")
    assert checker.checks == ("dependabot",)
    assert (
        checker.dependabot_config_path
        == pip_check.abstract.DEPENDABOT_CONFIG
        == ".github/dependabot.yml")
    assert (
        checker.requirements_filename
        == pip_check.abstract.REQUIREMENTS_FILENAME
        == "requirements.txt")
    assert checker.args.paths == ['path1', 'path2', 'path3']


def test_abstract_pip_checker_config_requirements():
    checker = DummyPipChecker("path1", "path2", "path3")

    config_mock = patch(
        "envoy.dependency.pip_check.abstract.APipChecker.dependabot_config",
        new_callable=PropertyMock)

    with config_mock as m_config:
        m_config.return_value.__getitem__.return_value = [
            {"package-ecosystem": "pip", "directory": "dir1"},
            {"package-ecosystem": "not-pip", "directory": "dir2"},
            {"package-ecosystem": "pip", "directory": "dir3"}]
        assert checker.config_requirements == {'dir1', 'dir3'}
        assert (
            m_config.return_value.__getitem__.call_args
            == [('updates',), {}])


@pytest.mark.parametrize("isdict", [True, False])
def test_abstract_pip_checker_dependabot_config(patches, isdict):
    checker = DummyPipChecker("path1", "path2", "path3")
    patched = patches(
        "utils",
        ("APipChecker.path", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.pip_check.abstract")

    with patched as (m_utils, m_path):
        if isdict:
            m_utils.from_yaml.return_value = {}

        if isdict:
            assert checker.dependabot_config == m_utils.from_yaml.return_value
        else:
            with pytest.raises(pip_check.PipConfigurationError) as e:
                checker.dependabot_config

            assert (
                e.value.args[0]
                == ("Unable to parse dependabot config: "
                    f"{checker.dependabot_config_path}"))

    assert (
        m_path.return_value.joinpath.call_args
        == [(checker._dependabot_config, ), {}])
    assert (
        m_utils.from_yaml.call_args
        == [(m_path.return_value.joinpath.return_value,), {}])


def test_abstract_pip_checker_path(patches):
    checker = DummyPipChecker("path1", "path2", "path3")
    patched = patches(
        ("checker.Checker.path", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.pip_check.abstract")

    with patched as (m_super, ):
        assert checker.path == m_super.return_value


def test_abstract_pip_checker_ignored_dirs(patches):
    checker = DummyPipChecker("path1", "path2", "path3")
    patched = patches(
        "re",
        prefix="envoy.dependency.pip_check.abstract")

    with patched as (m_re, ):
        assert (
            checker.ignored_dirs
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [("|".join(pip_check.abstract.IGNORED_DIRS), ), {}])
    assert "ignored_dirs" in checker.__dict__


@pytest.mark.parametrize(
    "matches",
    [[], range(0, 3), range(0, 5), range(3, 7)])
def test_abstract_pip_checker_requirements_dirs(patches, matches):
    checker = DummyPipChecker("path1", "path2", "path3")
    patched = patches(
        ("APipChecker.path", dict(new_callable=PropertyMock)),
        "APipChecker.dir_matches",
        prefix="envoy.dependency.pip_check.abstract")
    dirs = [MagicMock() for i in range(0, 5)]
    expected = [d for i, d in enumerate(dirs) if i in matches]

    class Matcher:
        counter = 0

        def match_dirs(self, path):
            _matches = self.counter in matches
            self.counter += 1
            return _matches

    matcher = Matcher()

    with patched as (m_path, m_matches):
        m_matches.side_effect = matcher.match_dirs
        m_path.return_value.glob.return_value = dirs

        assert (
            checker.requirements_dirs
            == {f"/{f.parent.relative_to.return_value}"
                for f in expected})

    assert (
        m_matches.call_args_list
        == [[(d, ), {}] for d in dirs])

    for exp in expected:
        assert (
            exp.parent.relative_to.call_args
            == [(m_path.return_value,), {}])
    assert "requirements_dirs" in checker.__dict__


TEST_REQS = (
    (set(), set()),
    (set(["A", "B"]), set()),
    (set(["A", "B"]), set(["B", "C"])),
    (set(["A", "B", "C"]), set(["A", "B", "C"])),
    (set(), set(["B", "C"])))


@pytest.mark.parametrize("requirements", TEST_REQS)
async def test_abstract_pip_checker_check_dependabot(patches, requirements):
    config, dirs = requirements
    checker = DummyPipChecker("path1", "path2", "path3")

    patched = patches(
        ("APipChecker.config_requirements", dict(new_callable=PropertyMock)),
        ("APipChecker.requirements_dirs", dict(new_callable=PropertyMock)),
        ("APipChecker.requirements_filename", dict(new_callable=PropertyMock)),
        "APipChecker.dependabot_success",
        "APipChecker.dependabot_errors",
        prefix="envoy.dependency.pip_check.abstract")

    with patched as (m_config, m_dirs, m_fname, m_success, m_errors):
        m_config.return_value = config
        m_dirs.return_value = dirs
        assert not await checker.check_dependabot()

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


def test_abstract_pip_checker_dependabot_success(patches):
    checker = DummyPipChecker("path1", "path2", "path3")
    success = set(["C", "D", "B", "A"])

    patched = patches(
        "APipChecker.succeed",
        ("APipChecker.requirements_filename", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.pip_check.abstract")

    with patched as (m_succeed, m_fname):
        checker.dependabot_success(success)

    assert (
        m_succeed.call_args
        == [('dependabot',
             [f"{m_fname.return_value}: {x}" for x in sorted(success)]),  {}])


def test_abstract_pip_checker_dependabot_errors(patches):
    checker = DummyPipChecker("path1", "path2", "path3")
    errors = set(["C", "D", "B", "A"])
    msg = "ERROR MESSAGE"

    patched = patches(
        "APipChecker.error",
        ("APipChecker.name", dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.pip_check.abstract")

    with patched as (m_error, m_name):
        checker.dependabot_errors(errors, msg)

    assert (
        m_error.call_args_list
        == [[('dependabot', [f'ERROR MESSAGE: {x}']), {}]
            for x in sorted(errors)])


@pytest.mark.parametrize("name_matches", [True, False])
@pytest.mark.parametrize("dir_ignored", [True, False])
def test_abstract_pip_checker_dir_matches(patches, name_matches, dir_ignored):
    checker = DummyPipChecker("path1", "path2", "path3")
    patched = patches(
        ("APipChecker.ignored_dirs",
         dict(new_callable=PropertyMock)),
        ("APipChecker.path",
         dict(new_callable=PropertyMock)),
        ("APipChecker.requirements_filename",
         dict(new_callable=PropertyMock)),
        prefix="envoy.dependency.pip_check.abstract")
    path = MagicMock()
    path.name = "PATH_NAME"

    with patched as (m_ignored, m_path, m_filename):
        if name_matches:
            m_filename.return_value = "PATH_NAME"
        m_ignored.return_value.match.return_value = (
            True
            if dir_ignored
            else False)

        assert (
            checker.dir_matches(path)
            == (name_matches and not dir_ignored))

    if not name_matches:
        assert not m_ignored.called
        assert not path.parent.relative_to.called
        assert not m_path.called
        return
    assert (
        m_ignored.return_value.match.call_args
        == [(f"/{path.parent.relative_to.return_value}", ), {}])
    assert (
        path.parent.relative_to.call_args
        == [(m_path.return_value, ), {}])
