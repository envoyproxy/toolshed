import hashlib
from unittest.mock import MagicMock, PropertyMock

import pytest

from envoy.gpg import identity, sign


@pytest.mark.parametrize("command", ["", None, "COMMAND", "OTHERCOMMAND"])
def test_binsign_constructor(command):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    args = ("PATH", maintainer, "LOG")
    if command is not None:
        args += (command, )
    binsign = sign.BinarySigningUtil(*args)

    assert isinstance(binsign, sign.DirectorySigningUtil)
    assert binsign._package_type == "bin"
    assert binsign._path == "PATH"
    assert binsign.maintainer == maintainer
    assert binsign.log == "LOG"
    assert binsign._command == (command or "")


@pytest.mark.parametrize("files", [(), ("FILE1", ), ("FILE1", "FILE2")])
def test_binsign_pkg_files(patches, files):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    binsign = sign.BinarySigningUtil("PATH", maintainer, "LOG")
    patched = patches(
        ("BinarySigningUtil.path", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.bin")

    with patched as (m_path, ):
        m_path.return_value.glob.return_value = iter(files)
        result = binsign.pkg_files

    assert result == m_path.return_value.glob.return_value
    assert "pkg_files" in binsign.__dict__
    assert (
        m_path.return_value.glob.call_args
        == [("*",), {}])


@pytest.mark.parametrize("files", [(), ("FILE1", ), ("FILE1", "FILE2")])
def test_binsign_shas(patches, files):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    binsign = sign.BinarySigningUtil("PATH", maintainer, "LOG")
    patched = patches(
        "BinarySigningUtil.sha256sum",
        ("BinarySigningUtil.pkg_files", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.bin")

    with patched as (m_sha, m_files):
        m_files.return_value = files
        m_sha.side_effect = [f"SHA{i}" for i in range(len(files))]
        assert binsign.shas == {
            path: f"SHA{i}"
            for i, path
            in enumerate(files)}

    assert "shas" in binsign.__dict__
    assert (
        m_sha.call_args_list
        == [[(path,), {}] for path in files])


def test_binsign_checksum_path(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    binsign = sign.BinarySigningUtil("PATH", maintainer, "LOG")
    patched = patches(
        ("BinarySigningUtil.path", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.bin")

    with patched as (m_path, ):
        assert (
            binsign.checksum_path
            == m_path.return_value.joinpath.return_value)

    assert (
        m_path.return_value.joinpath.call_args
        == [("checksums.txt.asc",), {}])


@pytest.mark.parametrize(
    "shas",
    [{},
     {"FILE1": "SHA1"},
     {"FILE1": "SHA1", "FILE2": "SHA2"}])
def test_binsign_checksums(patches, shas):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    binsign = sign.BinarySigningUtil("PATH", maintainer, "LOG")
    patched = patches(
        ("BinarySigningUtil.shas", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.bin")

    with patched as (m_shas, ):
        m_shas.return_value = shas
        assert (
            binsign.checksums
            == "\n".join(f"{sha}  {path}" for path, sha in shas.items()))


def test_binsign_sign(patches):
    maintainer = MagicMock()
    binsign = sign.BinarySigningUtil("PATH", maintainer, "LOG")
    signed = b"SIGNED"
    patched = patches(
        "print",
        ("BinarySigningUtil.checksum_path", dict(new_callable=PropertyMock)),
        ("BinarySigningUtil.checksums", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.bin")

    with patched as (m_print, m_path, m_sums):
        maintainer.gpg.sign.return_value.data = signed
        assert not binsign.sign()

    assert (
        maintainer.gpg.sign.call_args
        == [(m_sums.return_value,), {"clearsign": True}])
    assert (
        m_print.call_args
        == [(signed.decode("utf-8"),), {}])
    assert (
        m_path.return_value.write_bytes.call_args
        == [(signed,), {}])


@pytest.mark.parametrize("data", [b"", b"abc", b"123"])
def test_binsign_sha256sum(patches, data):
    maintainer = MagicMock()
    binsign = sign.BinarySigningUtil("PATH", maintainer, "LOG")
    binsign.log = MagicMock()
    pkg_file = MagicMock()
    pkg_file.name = "PACKAGE"
    pkg_file.read_bytes.return_value = data
    sha = hashlib.sha256(data).hexdigest()
    patched = patches(
        ("BinarySigningUtil.package_type", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.bin")

    with patched as (m_type, ):
        assert binsign.sha256sum(pkg_file) == sha

    assert (
        binsign.log.notice.call_args
        == [((f"Sign package ({m_type.return_value}): "
              f"{pkg_file.name} {sha}"),), {}])
