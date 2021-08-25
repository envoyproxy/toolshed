
from unittest.mock import MagicMock, PropertyMock

import pytest

from envoy.gpg import identity, sign


# RPMMacro

@pytest.mark.parametrize("overwrite", [[], None, True, False])
@pytest.mark.parametrize("kwargs", [{}, dict(K1="V1", K2="V2")])
def test_rpmmacro_constructor(patches, overwrite, kwargs):
    rpmmacro = (
        sign.RPMMacro("HOME", overwrite=overwrite, **kwargs)
        if overwrite != []
        else sign.RPMMacro("HOME", **kwargs))
    assert rpmmacro._macro_filename == ".rpmmacros"
    assert rpmmacro._home == "HOME"
    assert rpmmacro.overwrite == bool(overwrite or False)
    assert rpmmacro.kwargs == kwargs


def test_rpmmacro_home(patches):
    rpmmacro = sign.RPMMacro("HOME")
    patched = patches(
        "pathlib",
        prefix="envoy.gpg.sign.rpm")
    with patched as (m_plib, ):
        assert rpmmacro.home == m_plib.Path.return_value

    assert (
        list(m_plib.Path.call_args)
        == [(rpmmacro._home,), {}])


def test_rpmmacro_path(patches):
    rpmmacro = sign.RPMMacro("HOME")
    patched = patches(
        ("RPMMacro.home", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.rpm")
    with patched as (m_home, ):
        assert rpmmacro.path == m_home.return_value.joinpath.return_value

    assert (
        list(m_home.return_value.joinpath.call_args)
        == [(rpmmacro._macro_filename, ), {}])


@pytest.mark.parametrize("kwargs", [{}, dict(K1="V1", K2="V2")])
def test_rpmmacro_macro(patches, kwargs):
    rpmmacro = sign.RPMMacro("HOME", **kwargs)
    patched = patches(
        ("RPMMacro.template", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.rpm")
    with patched as (m_template, ):
        result = rpmmacro.macro

    expected = m_template.return_value
    for k, v in kwargs.items():
        assert (
            list(expected.replace.call_args)
            == [(f"__{k.upper()}__", v), {}])
        expected = expected.replace.return_value

    assert result == expected
    assert "macro" not in rpmmacro.__dict__


@pytest.mark.parametrize("overwrite", [True, False])
@pytest.mark.parametrize("exists", [True, False])
def test_rpmmacro_write(patches, overwrite, exists):
    rpmmacro = sign.RPMMacro("HOME")
    patched = patches(
        ("RPMMacro.macro", dict(new_callable=PropertyMock)),
        ("RPMMacro.path", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.rpm")
    rpmmacro.overwrite = overwrite

    with patched as (m_macro, m_path):
        m_path.return_value.exists.return_value = exists
        assert not rpmmacro.write()

    if not overwrite:
        assert (
            list(m_path.return_value.exists.call_args)
            == [(), {}])
    else:
        assert not m_path.return_value.exists.join.called

    if not overwrite and exists:
        assert not m_path.return_value.write_text.called
        return

    assert (
        list(m_path.return_value.write_text.call_args)
        == [(m_macro.return_value,), {}])


# RPMSigningUtil

@pytest.mark.parametrize("args", [(), ("ARG1", "ARG2")])
@pytest.mark.parametrize("kwargs", [{}, dict(K1="V1", K2="V2")])
def test_rpmsign_constructor(patches, args, kwargs):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    patched = patches(
        "RPMSigningUtil.setup",
        "DirectorySigningUtil.__init__",
        prefix="envoy.gpg.sign.rpm")

    with patched as (m_setup, m_super):
        rpmsign = sign.RPMSigningUtil("PATH", maintainer, *args, **kwargs)

    assert isinstance(rpmsign, sign.DirectorySigningUtil)
    assert rpmsign.ext == "rpm"
    assert rpmsign.command_name == "rpmsign"
    assert (
        list(m_setup.call_args)
        == [(), {}])
    assert (
        list(m_super.call_args)
        == [('PATH', maintainer) + args, kwargs])
    assert rpmsign.rpmmacro == sign.RPMMacro


@pytest.mark.parametrize("gpg2", [True, False])
def test_rpmsign_command(patches, gpg2):
    maintainer = MagicMock()
    patched = patches(
        "RPMSigningUtil.__init__",
        ("DirectorySigningUtil.command", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.rpm")

    with patched as (m_init, m_super):
        maintainer.gpg_bin.name = "gpg2" if gpg2 else "notgpg2"
        m_init.return_value = None
        rpmsign = sign.RPMSigningUtil("PATH", maintainer, "LOG")
        rpmsign.maintainer = maintainer

        if gpg2:
            assert rpmsign.command == m_super.return_value
        else:
            with pytest.raises(sign.SigningError) as e:
                rpmsign.command

            assert (
                e.value.args[0]
                == 'GPG2 is required to sign RPM packages')

    if gpg2:
        assert "command" in rpmsign.__dict__
    else:
        assert "command" not in rpmsign.__dict__


def test_rpmsign_command_args(patches):
    maintainer = MagicMock()
    patched = patches(
        "RPMSigningUtil.setup",
        prefix="envoy.gpg.sign.rpm")

    with patched as (m_setup,):
        rpmsign = sign.RPMSigningUtil("PATH", maintainer, "LOG")
        assert (
            rpmsign.command_args
            == ("--key-id", maintainer.fingerprint,
                "--addsign"))

    assert "command_args" in rpmsign.__dict__


class DummyRPMSigningUtil(sign.RPMSigningUtil):

    def __init__(self, path, maintainer):
        self._path = path
        self.maintainer = maintainer


def test_rpmsign_setup(patches):
    maintainer = MagicMock()
    rpmsign = DummyRPMSigningUtil("PATH", maintainer)
    patched = patches(
        ("RPMSigningUtil.rpmmacro", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.rpm")

    with patched as (m_macro, ):
        assert not rpmsign.setup()

    assert (
        list(m_macro.return_value.call_args)
        == [(maintainer.home,),
            {'maintainer': maintainer.name,
             'gpg_bin': maintainer.gpg_bin,
             'gpg_config': maintainer.gnupg_home}])


def test_rpmsign_sign_pkg(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    rpmsign = DummyRPMSigningUtil("PATH", maintainer)
    patched = patches(
        "DirectorySigningUtil.sign_pkg",
        prefix="envoy.gpg.sign.rpm")
    file = MagicMock()

    with patched as (m_sign, ):
        assert not rpmsign.sign_pkg(file)

    assert (
        list(file.chmod.call_args)
        == [(0o755, ), {}])
    assert (
        list(m_sign.call_args)
        == [(file,), {}])
