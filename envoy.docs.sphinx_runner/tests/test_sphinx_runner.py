from unittest.mock import MagicMock, PropertyMock

import pytest

from envoy.docs import sphinx_runner


class DummySphinxRunner(sphinx_runner.SphinxRunner):

    def __init__(self):
        pass


def test_sphinx_runner_constructor():
    runner = DummySphinxRunner()
    assert runner._build_sha == "UNKNOWN"
    assert runner._build_dir == "."


@pytest.mark.parametrize("docs_tag", [None, "", "SOME_DOCS_TAG"])
def test_sphinx_runner_blob_sha(patches, docs_tag):
    runner = DummySphinxRunner()
    patched = patches(
        ("SphinxRunner.build_sha", dict(new_callable=PropertyMock)),
        ("SphinxRunner.docs_tag", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_sha, m_tag):
        m_tag.return_value = docs_tag
        if docs_tag:
            assert runner.blob_sha == docs_tag
        else:
            assert runner.blob_sha == m_sha.return_value
    assert "blob_sha" not in runner.__dict__


def test_sphinx_runner_build_dir(patches):
    runner = DummySphinxRunner()
    patched = patches(
        "pathlib",
        ("SphinxRunner.tempdir", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_plib, m_temp):
        assert runner.build_dir == m_plib.Path.return_value

    assert (
        m_plib.Path.call_args
        == [(m_temp.return_value.name, ), {}])
    assert "build_dir" not in runner.__dict__


@pytest.mark.parametrize("build_sha", [None, "", "SOME_BUILD_SHA"])
def test_sphinx_runner_build_sha(patches, build_sha):
    runner = DummySphinxRunner()
    patched = patches(
        ("SphinxRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_args, ):
        m_args.return_value.build_sha = build_sha
        if build_sha:
            assert runner.build_sha == build_sha
        else:
            assert runner.build_sha == "UNKNOWN"

    assert "build_sha" not in runner.__dict__


def test_sphinx_runner_colors(patches):
    runner = DummySphinxRunner()
    patched = patches(
        "Fore",
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_colors, ):
        assert (
            runner.colors
            == dict(
                chrome=m_colors.LIGHTYELLOW_EX,
                key=m_colors.LIGHTCYAN_EX,
                value=m_colors.LIGHTMAGENTA_EX))

    assert "colors" in runner.__dict__


def test_sphinx_runner_config_file(patches):
    runner = DummySphinxRunner()
    patched = patches(
        "utils",
        ("SphinxRunner.config_file_path", dict(new_callable=PropertyMock)),
        ("SphinxRunner.configs", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_utils, m_fpath,  m_configs):
        assert (
            runner.config_file
            == m_utils.to_yaml.return_value)

    assert (
        m_utils.to_yaml.call_args
        == [(m_configs.return_value, m_fpath.return_value), {}])
    assert "config_file" in runner.__dict__


def test_sphinx_runner_config_file_path(patches):
    runner = DummySphinxRunner()
    patched = patches(
        ("SphinxRunner.build_dir", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_build, ):
        assert (
            runner.config_file_path
            == m_build.return_value.joinpath.return_value)

    assert (
        m_build.return_value.joinpath.call_args
        == [('build.yaml',), {}])
    assert "config_file_path" not in runner.__dict__


@pytest.mark.parametrize("validate", [True, False])
def test_sphinx_runner_configs(patches, validate):
    runner = DummySphinxRunner()
    mapping = dict(
        version_string="version_string",
        release_level="release_level",
        blob_sha="blob_sha",
        version_number="version_number",
        docker_image_tag_name="docker_image_tag_name",
        validator_path="validator_path",
        descriptor_path="descriptor_path",
        validate_fragments="validate_fragments")

    patched = patches(
        *[(f"SphinxRunner.{v}", dict(new_callable=PropertyMock))
          for v in mapping.values()],
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as _mocks:
        _mocks[-1].return_value = validate
        result = runner.configs

    _configs = {}
    for k, v in mapping.items():
        _v = _mocks[list(mapping.values()).index(v)].return_value
        if k == "validate_fragments":
            continue
        if k in ["validator_path", "descriptor_path"]:
            if not validate:
                continue
            _v = str(_v)
        _configs[k] = _v
    if not validate:
        _configs["skip_validation"] = "true"
    assert result == _configs
    assert "configs" in runner.__dict__


def test_sphinx_runner_descriptor_path(patches):
    runner = DummySphinxRunner()
    patched = patches(
        "pathlib",
        ("SphinxRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_plib, m_args):
        assert (
            runner.descriptor_path
            == m_plib.Path.return_value)

    assert (
        m_plib.Path.call_args
        == [(m_args.return_value.descriptor_path,), {}])
    assert "descriptor_path" not in runner.__dict__


def test_sphinx_runner_docker_image_tag_name(patches):
    runner = DummySphinxRunner()
    patched = patches(
        "re",
        ("SphinxRunner.version_number", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_re, m_version):
        assert (
            runner.docker_image_tag_name
            == m_re.sub.return_value)

    assert (
        m_re.sub.call_args
        == [('([0-9]+\\.[0-9]+)\\.[0-9]+.*', 'v\\1-latest',
             m_version.return_value), {}])
    assert "docker_image_tag_name" not in runner.__dict__


def test_sphinx_runner_docs_tag(patches):
    runner = DummySphinxRunner()
    patched = patches(
        ("SphinxRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_args, ):
        assert runner.docs_tag == m_args.return_value.docs_tag

    assert "docs_tag" not in runner.__dict__


def test_sphinx_runner_html_dir(patches):
    runner = DummySphinxRunner()
    patched = patches(
        ("SphinxRunner.build_dir", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_build, ):
        assert runner.html_dir == m_build.return_value.joinpath.return_value

    assert (
        m_build.return_value.joinpath.call_args
        == [('generated', 'html'), {}])
    assert "html_dir" in runner.__dict__


def test_sphinx_runner_output_path(patches):
    runner = DummySphinxRunner()
    patched = patches(
        "pathlib",
        ("SphinxRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_plib, m_args):
        assert runner.output_path == m_plib.Path.return_value

    assert (
        m_plib.Path.call_args
        == [(m_args.return_value.output_path, ), {}])
    assert "output_path" not in runner.__dict__


def test_sphinx_runner_overwrite(patches):
    runner = DummySphinxRunner()
    patched = patches(
        ("SphinxRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_args, ):
        assert runner.overwrite == m_args.return_value.overwrite

    assert "overwrite" not in runner.__dict__


@pytest.mark.parametrize("major", [2, 3, 4])
@pytest.mark.parametrize("minor", [5, 6, 7, 8, 9])
def test_sphinx_runner_py_compatible(patches, major, minor):
    runner = DummySphinxRunner()
    patched = patches(
        "bool",
        "sys",
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_bool, m_sys):
        m_sys.version_info.major = major
        m_sys.version_info.minor = minor
        assert runner.py_compatible == m_bool.return_value
    expected = (
        True
        if major == 3 and minor >= 8
        else False)
    assert (
        m_bool.call_args
        == [(expected,), {}])
    assert "py_compatible" not in runner.__dict__


@pytest.mark.parametrize("docs_tag", [None, "", "SOME_DOCS_TAG"])
def test_sphinx_runner_release_level(patches, docs_tag):
    runner = DummySphinxRunner()
    patched = patches(
        ("SphinxRunner.docs_tag", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_tag, ):
        m_tag.return_value = docs_tag
        if docs_tag:
            assert runner.release_level == "tagged"
        else:
            assert runner.release_level == "pre-release"
    assert "release_level" not in runner.__dict__


@pytest.mark.parametrize("rst_tar", [None, "", "SOME_DOCS_TAG"])
def test_sphinx_runner_rst_dir(patches, rst_tar):
    runner = DummySphinxRunner()
    patched = patches(
        "pathlib",
        "utils",
        ("SphinxRunner.build_dir", dict(new_callable=PropertyMock)),
        ("SphinxRunner.rst_tar", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_plib, m_utils, m_dir, m_rst):
        m_rst.return_value = rst_tar
        assert runner.rst_dir == m_dir.return_value.joinpath.return_value

    assert (
        m_dir.return_value.joinpath.call_args
        == [('generated', 'rst'), {}])

    if rst_tar:
        assert (
            m_utils.extract.call_args
            == [(m_dir.return_value.joinpath.return_value, rst_tar), {}])
    else:
        assert not m_utils.extract.called
    assert "rst_dir" in runner.__dict__


def test_sphinx_runner_rst_tar(patches):
    runner = DummySphinxRunner()
    patched = patches(
        "pathlib",
        ("SphinxRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_plib, m_args):
        assert runner.rst_tar == m_plib.Path.return_value

    assert (
        m_plib.Path.call_args
        == [(m_args.return_value.rst_tar, ), {}])
    assert "rst_tar" not in runner.__dict__


def test_sphinx_runner_sphinx_args(patches):
    runner = DummySphinxRunner()
    patched = patches(
        ("SphinxRunner.html_dir", dict(new_callable=PropertyMock)),
        ("SphinxRunner.rst_dir", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_html, m_rst):
        assert (
            runner.sphinx_args
            == ['-W', '--keep-going', '--color', '-b', 'html',
                str(m_rst.return_value),
                str(m_html.return_value)])

    assert "sphinx_args" not in runner.__dict__


@pytest.mark.parametrize("validator_path", ["", None, "VALIDATOR"])
@pytest.mark.parametrize("validate", [True, False])
def test_sphinx_runner_validate_fragments(patches, validator_path, validate):
    runner = DummySphinxRunner()
    patched = patches(
        ("SphinxRunner.args", dict(new_callable=PropertyMock)),
        ("SphinxRunner.validator_path", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_args, m_validator):
        m_args.return_value.validate_fragments = validate
        m_validator.return_value = validator_path
        assert runner.validate_fragments == bool(validator_path or validate)


def test_sphinx_runner_validator_path(patches):
    runner = DummySphinxRunner()
    patched = patches(
        "pathlib",
        ("SphinxRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_plib, m_args):
        assert (
            runner.validator_path
            == m_plib.Path.return_value)

    assert (
        m_plib.Path.call_args
        == [(m_args.return_value.validator_path,), {}])
    assert "validator_path" not in runner.__dict__


def test_sphinx_runner_version_file(patches):
    runner = DummySphinxRunner()
    patched = patches(
        "pathlib",
        ("SphinxRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_plib, m_args):
        assert runner.version_file == m_plib.Path.return_value

    assert (
        m_plib.Path.call_args
        == [(m_args.return_value.version_file, ), {}])
    assert "version_file" not in runner.__dict__


@pytest.mark.parametrize("version", ["", None, "VERSION"])
def test_sphinx_runner_version_number(patches, version):
    runner = DummySphinxRunner()
    patched = patches(
        ("SphinxRunner.args", dict(new_callable=PropertyMock)),
        ("SphinxRunner.version_file", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_args, m_file):
        m_args.return_value.version = version
        assert (
            runner.version_number
            == (m_file.return_value.read_text.return_value.strip.return_value
                if not version
                else version))

    if version:
        assert not m_file.called
        return
    assert (
        m_file.return_value.read_text.call_args
        == [(), {}])
    assert (
        m_file.return_value.read_text.return_value.strip.call_args
        == [(), {}])

    assert "version_number" in runner.__dict__


@pytest.mark.parametrize("docs_tag", [None, "", "SOME_DOCS_TAG"])
def test_sphinx_runner_version_string(patches, docs_tag):
    runner = DummySphinxRunner()
    patched = patches(
        ("SphinxRunner.docs_tag", dict(new_callable=PropertyMock)),
        ("SphinxRunner.build_sha", dict(new_callable=PropertyMock)),
        ("SphinxRunner.version_number", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_tag, m_sha, m_version):
        m_tag.return_value = docs_tag
        if docs_tag:
            assert runner.version_string == f"tag-{docs_tag}"
        else:
            assert (
                runner.version_string
                == (f"{m_version.return_value}-"
                    f"{m_sha.return_value.__getitem__.return_value}"))
            assert (
                m_sha.return_value.__getitem__.call_args
                == [(slice(None, 6, None),), {}])

    assert "version_string" not in runner.__dict__


def test_sphinx_runner_add_arguments(patches):
    runner = DummySphinxRunner()
    parser = MagicMock()
    patched = patches(
        "runner.Runner.add_arguments",
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_super, ):
        runner.add_arguments(parser)

    assert (
        m_super.call_args
        == [(parser, ), {}])
    assert (
        parser.add_argument.call_args_list
        == [[('--build_sha',), {}],
            [('--docs_tag',), {}],
            [('--version_file',), {}],
            [('--validator_path',), {}],
            [('--descriptor_path',), {}],
            [('--version',), {}],
            [('--validate_fragments',),
             {'action': 'store_true',
              'default': False}],
            [('--overwrite',),
             {'action': 'store_true',
              'default': False}],
            [('rst_tar',), {}],
            [('output_path',), {}]])


@pytest.mark.parametrize("fails", [True, False])
def test_sphinx_runner_build_html(patches, fails):
    runner = DummySphinxRunner()
    patched = patches(
        "sphinx_build",
        ("SphinxRunner.sphinx_args", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_sphinx, m_args):
        m_sphinx.side_effect = lambda s: fails
        e = None
        if fails:
            with pytest.raises(sphinx_runner.SphinxBuildError) as e:
                runner.build_html()
        else:
            runner.build_html()

    assert (
        m_sphinx.call_args
        == [(m_args.return_value,), {}])

    if fails:
        assert e.value.args == ('BUILD FAILED',)
    else:
        assert not e


def test_sphinx_runner_build_summary(patches):
    runner = DummySphinxRunner()
    patched = patches(
        "print",
        "SphinxRunner._color",
        ("SphinxRunner.configs", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_print, m_color, m_configs):
        m_configs.return_value.items.return_value = (("a", "A"), ("b", "B"))
        runner.build_summary()

    assert (
        m_print.call_args_list
        == [[(), {}],
            [(m_color.return_value,), {}],
            [(m_color.return_value,), {}],
            [(f"{m_color.return_value} {m_color.return_value}: "
              f"{m_color.return_value}",), {}],
            [(f"{m_color.return_value} {m_color.return_value}: "
              f"{m_color.return_value}",), {}],
            [(m_color.return_value,), {}],
            [(m_color.return_value,), {}],
            [(), {}]])
    assert (
        m_color.call_args_list
        == [[('#### Sphinx build configs #####################',), {}],
            [('###',), {}],
            [('###',), {}],
            [('a', 'key'), {}],
            [('A', 'value'), {}],
            [('###',), {}],
            [('b', 'key'), {}],
            [('B', 'value'), {}],
            [('###',), {}],
            [('###############################################',), {}]])


@pytest.mark.parametrize("py_compat", [True, False])
@pytest.mark.parametrize("release_level", ["pre-release", "tagged"])
@pytest.mark.parametrize("version_number", ["1.17", "1.23", "1.43"])
@pytest.mark.parametrize("docs_tag", ["v1.17", "v1.23", "v1.73"])
@pytest.mark.parametrize(
    "current", ["XXX v1.17 ZZZ", "AAA v1.23 VVV", "BBB v1.73 EEE"])
def test_sphinx_runner_check_env(
        patches, py_compat, release_level, version_number, docs_tag, current):
    runner = DummySphinxRunner()
    patched = patches(
        "platform",
        ("SphinxRunner.configs", dict(new_callable=PropertyMock)),
        ("SphinxRunner.version_number", dict(new_callable=PropertyMock)),
        ("SphinxRunner.docs_tag", dict(new_callable=PropertyMock)),
        ("SphinxRunner.py_compatible", dict(new_callable=PropertyMock)),
        ("SphinxRunner.rst_dir", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    fails = (
        not py_compat
        or (release_level == "tagged"
            and (f"v{version_number}" != docs_tag
                 or version_number not in current)))

    with patched as (m_platform, m_configs, m_version, m_tag, m_py, m_rst):
        m_py.return_value = py_compat
        m_configs.return_value.__getitem__.return_value = release_level
        m_version.return_value = version_number
        m_tag.return_value = docs_tag
        (m_rst.return_value.joinpath
         .return_value.read_text.return_value) = current

        if fails:
            with pytest.raises(sphinx_runner.SphinxEnvError) as e:
                runner.check_env()
        else:
            runner.check_env()

    if not py_compat:
        assert (
            e.value.args
            == ("ERROR: python version must be >= 3.8, "
                f"you have {m_platform.python_version.return_value}", ))
        return

    if release_level != "tagged":
        return

    if f"v{version_number}" != docs_tag:
        assert (
            e.value.args
            == ("Given git tag does not match the VERSION file content:"
                f"{docs_tag} vs v{version_number}", ))
        return

    assert (
        m_rst.return_value.joinpath.call_args
        == [("version_history", "current.rst"), {}])

    if version_number not in current:
        assert (
            e.value.args
            == (f"Git tag ({version_number}) not found "
                "in version_history/current.rst", ))


@pytest.mark.parametrize("exists", [True, False])
async def test_sphinx_runner_cleanup(patches, exists):
    runner = DummySphinxRunner()
    patched = patches(
        ("SphinxRunner.tempdir", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_temp, ):
        if exists:
            runner.__dict__["tempdir"] = m_temp.return_value
        assert not await runner.cleanup()

    assert "tempdir" not in runner.__dict__
    if exists:
        assert (
            m_temp.return_value.cleanup.call_args
            == [(), {}])
    else:
        assert not m_temp.called


@pytest.mark.parametrize("tarlike", [True, False])
@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("is_file", [True, False])
def test_sphinx_runner_save_html(patches, tarlike, exists, is_file):
    runner = DummySphinxRunner()
    patched = patches(
        "tarfile",
        "utils",
        "shutil",
        ("SphinxRunner.log", dict(new_callable=PropertyMock)),
        ("SphinxRunner.output_path", dict(new_callable=PropertyMock)),
        ("SphinxRunner.html_dir", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_tar, m_utils, m_shutil, m_log, m_out, m_html):
        m_utils.is_tarlike.return_value = tarlike
        m_out.return_value.exists.return_value = exists
        m_out.return_value.is_file.return_value = is_file
        runner.save_html()

    if exists:
        assert (
            m_log.return_value.warning.call_args
            == [(f"Output path ({m_out.return_value}) exists, "
                 "removing", ), {}])
        assert (
            m_out.return_value.is_file.call_args
            == [(), {}])
        if is_file:
            assert (
                m_out.return_value.unlink.call_args
                == [(), {}])
            assert not m_shutil.rmtree.called
        else:
            assert not m_out.return_value.unlink.called
            assert (
                m_shutil.rmtree.call_args
                == [(m_out.return_value, ), {}])

    else:
        assert not m_log.called
        assert not m_out.return_value.is_file.called
        assert not m_out.return_value.unlink.called
        assert not m_shutil.rmtree.called

    assert (
        m_utils.is_tarlike.call_args
        == [(m_out.return_value, ), {}])

    if not tarlike:
        assert not m_tar.open.called
        assert (
            m_shutil.copytree.call_args
            == [(m_html.return_value, m_out.return_value, ), {}])
        return

    assert not m_shutil.copytree.called
    assert (
        m_tar.open.call_args
        == [(m_out.return_value, 'w'), {}])
    assert (
        m_tar.open.return_value.__enter__.return_value.add.call_args
        == [(m_html.return_value,), {'arcname': '.'}])


@pytest.mark.parametrize("check_fails", [True, False])
@pytest.mark.parametrize("build_fails", [True, False])
async def test_sphinx_runner_run(patches, check_fails, build_fails):
    runner = DummySphinxRunner()
    patched = patches(
        "print",
        "os",
        "SphinxRunner.build_summary",
        "SphinxRunner.check_env",
        "SphinxRunner.build_html",
        "SphinxRunner.save_html",
        "SphinxRunner.validate_args",
        ("SphinxRunner.config_file", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    def _raise(error):
        raise error

    assert runner.run.__wrapped__.__cleansup__

    with patched as patchy:
        (m_print, m_os, m_summary,
         m_check, m_build, m_save, m_validate, m_config) = patchy
        if check_fails:
            _check_error = sphinx_runner.SphinxEnvError("CHECK FAILED")
            m_check.side_effect = lambda: _raise(_check_error)
        if build_fails:
            _build_error = sphinx_runner.SphinxBuildError("BUILD FAILED")
            m_build.side_effect = lambda: _raise(_build_error)
        assert (
            await runner.run()
            == (1 if (check_fails or build_fails) else None))

    assert (
        m_validate.call_args
        == [(), {}])
    assert (
        m_check.call_args
        == [(), {}])
    assert (
        m_os.environ.__setitem__.call_args
        == [('ENVOY_DOCS_BUILD_CONFIG', str(m_config.return_value)), {}])

    if check_fails:
        assert (
            m_print.call_args
            == [(_check_error,), {}])
        assert not m_summary.called
        assert not m_build.called
        assert not m_save.called
        return

    assert (
        m_summary.call_args
        == [(), {}])
    assert (
        m_build.call_args
        == [(), {}])

    if build_fails:
        assert (
            m_print.call_args
            == [(_build_error,), {}])
        assert not m_save.called
        return

    assert not m_print.called
    assert (
        m_save.call_args
        == [(), {}])


@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("overwrite", [True, False])
def test_sphinx_runner_validate_args(patches, exists, overwrite):
    runner = DummySphinxRunner()
    patched = patches(
        ("SphinxRunner.output_path", dict(new_callable=PropertyMock)),
        ("SphinxRunner.overwrite", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_out, m_overwrite):
        m_out.return_value.exists.return_value = exists
        m_overwrite.return_value = overwrite
        if exists and not overwrite:
            with pytest.raises(sphinx_runner.SphinxBuildError) as e:
                runner.validate_args()
            assert (
                e.value.args[0]
                == (f"Output path ({m_out.return_value}) exists and "
                    "`--overwrite` is not set`"))
        else:
            assert not runner.validate_args()

    assert (
        m_out.return_value.exists.call_args
        == [(), {}])
    if not exists:
        assert not m_overwrite.called
        return


@pytest.mark.parametrize("color", [None, "COLOR"])
def test_sphinx_runner__color(patches, color):
    runner = DummySphinxRunner()
    patched = patches(
        "Style",
        ("SphinxRunner.colors", dict(new_callable=PropertyMock)),
        prefix="envoy.docs.sphinx_runner.runner")

    with patched as (m_style, m_colors):
        assert (
            runner._color("MSG", color)
            == (f"{m_colors.return_value.__getitem__.return_value}"
                f"MSG{m_style.RESET_ALL}"))
    assert (
        m_colors.return_value.__getitem__.call_args
        == [(color or "chrome",), {}])
