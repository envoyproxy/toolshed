
from unittest.mock import MagicMock, PropertyMock

import pytest

from aio.run import runner
from envoy.gpg import identity, sign


def test_packager_constructor():
    packager = sign.PackageSigningRunner("x", "y", "z")
    assert isinstance(packager, runner.Runner)
    assert packager.maintainer_class == identity.GPGIdentity
    assert packager._signing_utils == ()
    assert packager.signing_key_path == sign.runner.SIGNING_KEY_PATH
    assert "signing_key_path" not in packager.__dict__


def test_packager_cls_register_util():
    assert sign.PackageSigningRunner._signing_utils == ()

    class Util1(object):
        pass

    class Util2(object):
        pass

    sign.PackageSigningRunner.register_util("util1", Util1)
    assert (
        sign.PackageSigningRunner._signing_utils
        == (('util1', Util1),))

    sign.PackageSigningRunner.register_util("util2", Util2)
    assert (
        sign.PackageSigningRunner._signing_utils
        == (('util1', Util1),
            ('util2', Util2),))


def test_packager_extract(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        ("PackageSigningRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")

    with patched as (m_args, ):
        assert packager.extract == m_args.return_value.extract

    assert "extract" not in packager.__dict__


def test_packager_gen_key(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        ("PackageSigningRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")

    with patched as (m_args, ):
        assert packager.gen_key == m_args.return_value.gen_key

    assert "gen_key" not in packager.__dict__


@pytest.mark.parametrize("gen_key", [True, False])
def test_packager_gnupg_home(patches, gen_key):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        "pathlib",
        ("PackageSigningRunner.gen_key",
         dict(new_callable=PropertyMock)),
        ("PackageSigningRunner.gnupg_tempdir",
         dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")

    with patched as (m_plib, m_gen, m_temp):
        m_gen.return_value = gen_key
        assert (
            packager.gnupg_home
            == (m_plib.Path.return_value
                if gen_key
                else None))

    assert "gnupg_home" not in packager.__dict__
    if not gen_key:
        assert not m_plib.Path.called
        assert not m_temp.called
        return
    assert (
        m_plib.Path.call_args
        == [(m_temp.return_value.name, ), {}])


def test_packager_gnupg_tempdir(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        "tempfile",
        prefix="envoy.gpg.sign.runner")

    with patched as (m_temp, ):
        assert (
            packager.gnupg_tempdir
            == m_temp.TemporaryDirectory.return_value)
    assert "gnupg_tempdir" in packager.__dict__


def test_packager_maintainer(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        ("PackageSigningRunner.gen_key",
         dict(new_callable=PropertyMock)),
        ("PackageSigningRunner.gnupg_home",
         dict(new_callable=PropertyMock)),
        ("PackageSigningRunner.log",
         dict(new_callable=PropertyMock)),
        ("PackageSigningRunner.maintainer_class",
         dict(new_callable=PropertyMock)),
        ("PackageSigningRunner.maintainer_email",
         dict(new_callable=PropertyMock)),
        ("PackageSigningRunner.maintainer_name",
         dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")

    with patched as (m_gen, m_home, m_log, m_class, m_email, m_name):
        assert packager.maintainer == m_class.return_value.return_value

    assert (
        m_class.return_value.call_args
        == [(m_name.return_value,
             m_email.return_value,
             m_log.return_value),
            dict(gnupg_home=m_home.return_value,
                 gen_key=m_gen.return_value)])

    assert "maintainer" in packager.__dict__


def test_packager_maintainer_email(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        ("PackageSigningRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")

    with patched as (m_args, ):
        assert (
            packager.maintainer_email
            == m_args.return_value.maintainer_email)

    assert "maintainer_email" not in packager.__dict__


def test_packager_maintainer_name(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")

    patched = patches(
        ("PackageSigningRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")

    with patched as (m_args, ):
        assert packager.maintainer_name == m_args.return_value.maintainer_name

    assert "maintainer_name" not in packager.__dict__


def test_packager_package_type(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")

    patched = patches(
        ("PackageSigningRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")

    with patched as (m_args, ):
        assert packager.package_type == m_args.return_value.package_type

    assert "package_type" not in packager.__dict__


def test_packager_path(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        "pathlib",
        ("PackageSigningRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")

    with patched as (m_plib, m_args):
        assert packager.path == m_plib.Path.return_value

    assert (
        m_plib.Path.call_args
        == [(m_args.return_value.path, ), {}])
    assert "path" not in packager.__dict__


def test_packager_tar(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        ("PackageSigningRunner.args", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")

    with patched as (m_args, ):
        assert packager.tar == m_args.return_value.tar

    assert "tar" not in packager.__dict__


def test_packager_signing_utils():
    packager = sign.PackageSigningRunner("x", "y", "z")
    _utils = (("NAME1", "UTIL1"), ("NAME2", "UTIL2"))
    packager._signing_utils = _utils
    assert packager.signing_utils == dict(_utils)
    assert "signing_utils" in packager.__dict__


def test_packager_add_arguments():
    packager = sign.PackageSigningRunner("x", "y", "z")
    parser = MagicMock()
    packager.add_arguments(parser)
    assert (
        parser.add_argument.call_args_list
        == [[('--verbosity', '-v'),
             {'choices': ['debug', 'info', 'warn', 'error'],
              'default': 'info',
              'help': 'Application log level'}],
            [('--log-level', '-l'),
             {'choices': ['debug', 'info', 'warn', 'error'],
              'default': 'warn',
              'help': 'Log level for non-application logs'}],
            [('path',),
             {'default': '',
              'help': 'Path to the directory containing packages to sign'}],
            [('--extract',),
             {'action': 'store_true',
              'help': (
                  'If set, treat the path as a tarball containing directories '
                  'according to package_type')}],
            [('--tar',),
             {'help': 'Path to save the signed packages as tar file'}],
            [('--type',),
             {'choices': ['util1', 'util2', ''],
              'default': '',
              'help': 'Package type to sign'}],
            [('--maintainer-name',),
             {'default': '',
              'help': (
                  'Maintainer name to match when searching for a GPG key '
                  'to match with')}],
            [('--maintainer-email',),
             {'default': '',
              'help': (
                  'Maintainer email to match when searching for a GPG key '
                  'to match with')}],
           [('--gen-key',),
            {'action': 'store_true',
             'help': 'If set, create the signing key (requires '
                     '`--maintainer-name` and `--maintainer-email`) '}]])


def test_packager_add_key(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        "utils",
        "pathlib",
        ("PackageSigningRunner.maintainer",
         dict(new_callable=PropertyMock)),
        ("PackageSigningRunner.signing_key_path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")
    path = MagicMock()

    with patched as (m_utils, m_plib, m_maintainer, m_keypath):
        assert not packager.add_key(path)

    assert (
        m_utils.typed.call_args
        == [(m_plib.Path, path), {}])
    m_path = m_utils.typed.return_value
    assert (
        m_path.joinpath.call_args
        == [(m_keypath.return_value, ), {}])
    assert (
        m_path.joinpath.return_value.write_text.call_args
        == [(m_maintainer.return_value.export_key.return_value, ), {}])
    assert (
        m_maintainer.return_value.export_key.call_args
        == [(), {}])


def test_packager_archive(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        "tarfile",
        "utils",
        ("PackageSigningRunner.tar", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")

    with patched as (m_tarfile, m_utils, m_tar):
        assert not packager.archive("PATH")

    assert (
        m_tarfile.open.call_args
        == [(m_tar.return_value, m_utils.tar_mode.return_value), {}])
    assert (
        m_utils.tar_mode.call_args
        == [(m_tar.return_value, ), dict(mode="w")])
    assert (
        m_tarfile.open.return_value.__enter__.return_value.add.call_args
        == [('PATH',), {'arcname': '.'}])


@pytest.mark.parametrize("indict", [True, False])
async def test_packager_cleanup(patches, indict):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        ("PackageSigningRunner.gnupg_tempdir",
         dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")
    if indict:
        packager.__dict__["gnupg_tempdir"] = "GNUPG TEMPDIR"

    with patched as (m_temp, ):
        assert not await packager.cleanup()

    assert "gnupg_tempdir" not in packager.__dict__
    if not indict:
        assert not m_temp.called
        return
    assert (
        m_temp.return_value.cleanup.call_args
        == [(), {}])


def test_packager_get_signing_util(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        ("PackageSigningRunner.log",
         dict(new_callable=PropertyMock)),
        ("PackageSigningRunner.maintainer",
         dict(new_callable=PropertyMock)),
        ("PackageSigningRunner.signing_utils",
         dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")
    path = MagicMock()

    with patched as (m_log, m_maintainer, m_utils):
        assert (
            packager.get_signing_util(path)
            == m_utils.return_value.__getitem__.return_value.return_value)

    assert (
        m_utils.return_value.__getitem__.call_args
        == [(path.name,), {}])
    assert (
        m_utils.return_value.__getitem__.return_value.call_args
        == [(path, m_maintainer.return_value, m_log.return_value), {}])


@pytest.mark.parametrize("extract", [True, False])
async def test_packager_run(patches, extract):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        "PackageSigningRunner.sign_tarball",
        "PackageSigningRunner.sign_directory",
        ("PackageSigningRunner.extract", dict(new_callable=PropertyMock)),
        ("PackageSigningRunner.log", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")

    assert (
        packager.run.__wrapped__.__catches__
        == (identity.GPGError, sign.SigningError))

    with patched as (m_tarb, m_dir, m_extract, m_log):
        m_extract.return_value = extract
        assert not await packager.run()

    assert (
        m_log.return_value.success.call_args
        == [('Successfully signed packages',), {}])

    if extract:
        assert (
            m_tarb.call_args
            == [(), {}])
        assert not m_dir.called
        return
    assert not m_tarb.called
    assert (
        m_dir.call_args
        == [(), {}])


def test_packager_sign(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        "PackageSigningRunner.get_signing_util",
        ("PackageSigningRunner.log", dict(new_callable=PropertyMock)),
        ("PackageSigningRunner.maintainer", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")
    path = MagicMock()

    with patched as (m_util, m_log, m_maintainer):
        assert not packager.sign(path)

    assert (
        m_log.return_value.notice.call_args
        == [((f"Signing {path.name}s ({m_maintainer.return_value}) "
              f"{path}"),), {}])
    assert (
        m_util.call_args
        == [(path, ), {}])
    assert (
        m_util.return_value.sign.call_args
        == [(), {}])


@pytest.mark.parametrize("utils", [[], ["a", "b", "c"]])
@pytest.mark.parametrize("listdir", [[], ["a", "b"], ["b", "c"], ["c", "d"]])
def test_packager_sign_all(patches, listdir, utils):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        "PackageSigningRunner.sign",
        ("PackageSigningRunner.signing_utils",
         dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")
    path = MagicMock()

    with patched as (m_sign, m_utils):
        _glob = {}

        for _path in listdir:
            _mock = MagicMock()
            _mock.name = _path
            _glob[_path] = _mock
        path.glob.return_value = _glob.values()
        m_utils.return_value = utils
        assert not packager.sign_all(path)

    assert (
        path.glob.call_args
        == [('*',), {}])
    expected = [x for x in listdir if x in utils]
    assert (
        m_sign.call_args_list
        == [[(_glob[k], ), {}] for k in expected])


@pytest.mark.parametrize("tar", [True, False])
def test_packager_sign_directory(patches, tar):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        "PackageSigningRunner.archive",
        "PackageSigningRunner.sign",
        ("PackageSigningRunner.path", dict(new_callable=PropertyMock)),
        ("PackageSigningRunner.tar", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")

    with patched as (m_archive, m_sign, m_path, m_tar):
        m_tar.return_value = tar
        assert not packager.sign_directory()

    assert (
        m_sign.call_args
        == [(m_path.return_value, ), {}])
    if not tar:
        assert not m_archive.called
        return

    assert (
        m_archive.call_args
        == [(m_path.return_value, ), {}])


@pytest.mark.parametrize("tar", [True, False])
def test_packager_sign_tarball(patches, tar):
    packager = sign.PackageSigningRunner("x", "y", "z")
    patched = patches(
        "utils",
        "PackageSigningRunner.add_key",
        "PackageSigningRunner.archive",
        "PackageSigningRunner.sign_all",
        ("PackageSigningRunner.path", dict(new_callable=PropertyMock)),
        ("PackageSigningRunner.tar", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.runner")

    with patched as (m_utils, m_addkey, m_archive, m_sign, m_path, m_tar):
        m_tar.return_value = tar
        if not tar:
            with pytest.raises(sign.SigningError) as e:
                packager.sign_tarball()
        else:
            assert not packager.sign_tarball()

    if not tar:
        assert (
            e.value.args[0]
            == ("You must set a `--tar` file to save to when "
                "`--extract` is set"))
        assert not m_utils.untar.called
        assert not m_addkey.called
        assert not m_sign.called
        assert not m_archive.called
        return

    assert (
        m_utils.untar.call_args
        == [(m_path.return_value,), {}])
    assert (
        m_sign.call_args
        == [(m_utils.untar.return_value.__enter__.return_value,), {}])
    assert (
        m_addkey.call_args
        == [(m_utils.untar.return_value.__enter__.return_value,), {}])
    assert (
        m_archive.call_args
        == [(m_utils.untar.return_value.__enter__.return_value,), {}])
