
from unittest.mock import MagicMock, PropertyMock

import pytest

from envoy.gpg import identity, sign


@pytest.mark.parametrize("command", ["", None, "COMMAND", "OTHERCOMMAND"])
def test_util_constructor(command):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    args = ("PATH", maintainer, "LOG")
    if command is not None:
        args += (command, )
    util = sign.DirectorySigningUtil(*args)
    assert util._path == "PATH"
    assert util.maintainer == maintainer
    assert util.log == "LOG"
    assert util._command == (command or "")
    assert util.command_args == ()


@pytest.mark.parametrize("command_name", ["", None, "CMD", "OTHERCMD"])
@pytest.mark.parametrize("command", ["", None, "COMMAND", "OTHERCOMMAND"])
@pytest.mark.parametrize("which", ["", None, "PATH", "OTHERPATH"])
def test_util_command(patches, command_name, command, which):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    util = sign.DirectorySigningUtil(
        "PATH", maintainer, "LOG", command=command)
    patched = patches(
        "shutil",
        ("DirectorySigningUtil.package_type", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.util")
    if command_name is not None:
        util.command_name = command_name

    with patched as (m_shutil, m_type):
        m_shutil.which.return_value = which

        if not which and not command:
            with pytest.raises(sign.SigningError) as e:
                util.command

            assert (
                m_shutil.which.call_args
                == [(command_name or "",), {}])
            assert (
                e.value.args[0]
                == (f"Signing software missing ({m_type.return_value}): "
                    f"{command_name or ''}"))
            return

        result = util.command

    assert "command" in util.__dict__
    assert not m_type.called

    if command:
        assert not m_shutil.which.called
        assert result == command
        return

    assert (
        m_shutil.which.call_args
        == [(command_name or "",), {}])
    assert result == m_shutil.which.return_value


def test_util_sign(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    util = sign.DirectorySigningUtil("PATH", maintainer, "LOG")
    patched = patches(
        "DirectorySigningUtil.sign_pkg",
        ("DirectorySigningUtil.pkg_files", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.util")

    with patched as (m_sign, m_pkgs):
        m_pkgs.return_value = ("PKG1", "PKG2", "PKG3")
        assert not util.sign()

    assert (
        m_sign.call_args_list
        == [[('PKG1',), {}],
            [('PKG2',), {}],
            [('PKG3',), {}]])


def test_util_sign_command(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    util = sign.DirectorySigningUtil("PATH", maintainer, "LOG")
    patched = patches(
        ("DirectorySigningUtil.command", dict(new_callable=PropertyMock)),
        ("DirectorySigningUtil.command_args", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.util")

    with patched as (m_command, m_args):
        m_args.return_value = ("ARG1", "ARG2", "ARG3")
        assert (
            util.sign_command("PACKAGE")
            == ((m_command.return_value, )
                + m_args.return_value + ("PACKAGE", )))


@pytest.mark.parametrize("returncode", [0, 1])
def test_util_sign_pkg(patches, returncode):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    util = sign.DirectorySigningUtil("PATH", maintainer, "LOG")
    util.log = MagicMock()
    pkg_file = MagicMock()
    patched = patches(
        "subprocess",
        "DirectorySigningUtil.sign_command",
        ("DirectorySigningUtil.package_type", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.util")

    with patched as (m_subproc, m_command, m_type):
        m_subproc.run.return_value.returncode = returncode
        if returncode:
            with pytest.raises(sign.SigningError) as e:
                util.sign_pkg(pkg_file)
        else:
            assert not util.sign_pkg(pkg_file)

    assert (
        util.log.notice.call_args
        == [(f"Sign package ({m_type.return_value}): {pkg_file.name}",), {}])
    assert (
        m_command.call_args
        == [(pkg_file,), {}])
    assert (
        m_subproc.run.call_args
        == [(m_command.return_value,),
            {'capture_output': True,
             'encoding': 'utf-8'}])

    if not returncode:
        assert (
            util.log.success.call_args
            == [((f"Signed package ({m_type.return_value}): "
                  f"{pkg_file.name}"),), {}])
        return
    assert (
        e.value.args[0]
        == (m_subproc.run.return_value.stdout
            + m_subproc.run.return_value.stderr))


@pytest.mark.parametrize("ext", ["EXT1", "EXT2"])
@pytest.mark.parametrize("package_type", [None, "", "TYPE1", "TYPE2"])
def test_util_package_type(ext, package_type):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    util = sign.DirectorySigningUtil("PATH", maintainer, "LOG")
    util.ext = ext
    util._package_type = package_type
    assert util.package_type == package_type or ext


def test_util_path(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    util = sign.DirectorySigningUtil("PATH", maintainer, "LOG")
    patched = patches(
        "pathlib",
        prefix="envoy.gpg.sign.util")
    with patched as (m_plib, ):
        assert util.path == m_plib.Path.return_value

    assert (
        m_plib.Path.call_args
        == [(util._path,), {}])


@pytest.mark.parametrize(
    "files",
    [[],
     ["abc", "xyz"],
     ["abc.EXT", "xyz.EXT", "abc.FOO", "abc.BAR"],
     ["abc.NOTEXT", "xyz.NOTEXT"]])
def test_util_pkg_files(patches, files):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    util = sign.DirectorySigningUtil("PATH", maintainer, "LOG")
    patched = patches(
        ("DirectorySigningUtil.ext", dict(new_callable=PropertyMock)),
        ("DirectorySigningUtil.path", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.util")
    with patched as (m_ext, m_path):
        _glob = {}

        for _path in files:
            _mock = MagicMock()
            _mock.name = _path
            _glob[_path] = _mock
        m_path.return_value.glob.return_value = _glob.values()

        m_ext.return_value = "EXT"
        result = util.pkg_files

    expected = [fname for fname in files if fname.endswith(".EXT")]

    assert (
        m_path.return_value.glob.call_args
        == [("*",), {}])
    assert "pkg_files" not in util.__dict__
    assert (
        result
        == tuple(_glob[k] for k in expected))
