
import types
from unittest.mock import MagicMock, PropertyMock

import pytest

from envoy.gpg import identity, sign


# DebChangesFiles

def test_changes_constructor():
    changes = sign.DebChangesFiles("SRC")
    assert changes.src == "SRC"


def test_changes_dunder_iter(patches):
    path = MagicMock()
    changes = sign.DebChangesFiles(path)

    patched = patches(
        ("DebChangesFiles.files", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.deb")
    _files = ["FILE1", "FILE2", "FILE3"]

    with patched as (m_files, ):
        m_files.return_value = _files
        result = changes.__iter__()
        assert list(result) == _files

    assert isinstance(result, types.GeneratorType)
    assert (
        list(path.unlink.call_args)
        == [(), {}])


@pytest.mark.parametrize(
    "lines",
    [([], None),
     (["FOO", "BAR"], None),
     (["FOO", "BAR",
       "Distribution: distro1"], "distro1"),
     (["FOO", "BAR",
       "Distribution: distro1 distro2"], "distro1 distro2"),
     (["FOO", "BAR",
       "Distribution: distro1 distro2", "BAZ"], "distro1 distro2"),
     (["FOO", "BAR",
       "", "Distribution: distro1 distro2"], None)])
def test_changes_distributions(patches, lines):
    lines, expected = lines
    changes = sign.DebChangesFiles("SRC")
    patched = patches(
        "open",
        prefix="envoy.gpg.sign.deb")

    class DummyFile(object):
        line = 0

        def __init__(self, lines):
            self.lines = lines

        def readline(self):
            if len(self.lines) > self.line:
                line = self.lines[self.line]
                self.line += 1
                return line

    _file = DummyFile(lines)

    with patched as (m_open, ):
        readline = m_open.return_value.__enter__.return_value.readline
        readline.side_effect = _file.readline
        if expected:
            assert changes.distributions == expected
        else:
            with pytest.raises(sign.SigningError) as e:
                changes.distributions
            assert (
                e.value.args[0]
                == "Did not find Distribution field in changes file SRC")

    if "" in lines:
        lines = lines[:lines.index("")]

    if expected:
        breakon = 0
        for line in lines:
            if line.startswith("Distribution:"):
                break
            breakon += 1
        lines = lines[:breakon]
    count = len(lines) + 1
    assert (
        list(list(c)
             for c
             in readline.call_args_list)
        == [[(), {}]] * count)


def test_changes_files(patches):
    changes = sign.DebChangesFiles("SRC")

    patched = patches(
        "DebChangesFiles.changes_file",
        ("DebChangesFiles.distributions", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.deb")

    with patched as (m_changes, m_distros):
        m_distros.return_value = "DISTRO1 DISTRO2 DISTRO3"
        result = changes.files
        assert list(result) == [m_changes.return_value] * 3

    assert isinstance(result, types.GeneratorType)
    assert (
        list(list(c) for c in m_changes.call_args_list)
        == [[('DISTRO1',), {}],
            [('DISTRO2',), {}],
            [('DISTRO3',), {}]])


def test_changes_changes_file(patches):
    path = MagicMock()
    changes = sign.DebChangesFiles(path)
    patched = patches(
        "DebChangesFiles.changes_file_path",
        ("DebChangesFiles.distributions", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.deb")

    with patched as (m_path, m_distros):
        assert (
            changes.changes_file("DISTRO")
            == m_path.return_value)

    assert (
        list(m_path.call_args)
        == [('DISTRO',), {}])
    assert (
        list(m_path.return_value.write_text.call_args)
        == [(path.read_text.return_value.replace.return_value,), {}])
    assert (
        list(path.read_text.call_args)
        == [(), {}])
    assert (
        list(path.read_text.return_value.replace.call_args)
        == [(m_distros.return_value, "DISTRO"), {}])


def test_changes_file_path():
    path = MagicMock()
    changes = sign.DebChangesFiles(path)
    assert changes.changes_file_path("DISTRO") == path.with_suffix.return_value
    assert (
        list(path.with_suffix.call_args)
        == [('.DISTRO.changes',), {}])


# DebSigningUtil

@pytest.mark.parametrize("args", [(), ("ARG1", ), ("ARG2", )])
def test_debsign_constructor(patches, args):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    debsign = sign.DebSigningUtil("PATH", maintainer, "LOG", *args)

    assert isinstance(debsign, sign.DirectorySigningUtil)
    assert debsign.ext == "changes"
    assert debsign.command_name == "debsign"
    assert debsign._package_type == "deb"
    assert debsign.changes_files == sign.DebChangesFiles
    assert debsign._path == "PATH"
    assert debsign.maintainer == maintainer
    assert debsign.log == "LOG"


def test_debsign_command_args(patches):
    maintainer = MagicMock()
    debsign = sign.DebSigningUtil("PATH", maintainer, "LOG")
    assert (
        debsign.command_args
        == ("-k", maintainer.fingerprint))
    assert "command_args" in debsign.__dict__


def test_debsign_pkg_files(patches):
    packager = sign.PackageSigningRunner("x", "y", "z")
    maintainer = identity.GPGIdentity(packager)
    debsign = sign.DebSigningUtil("PATH", maintainer, "LOG")
    patched = patches(
        "chain",
        ("DirectorySigningUtil.pkg_files", dict(new_callable=PropertyMock)),
        ("DebSigningUtil.changes_files", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.sign.deb")

    with patched as (m_chain, m_pkg, m_changes):
        m_pkg.return_value = ("FILE1", "FILE2", "FILE3")
        m_chain.from_iterable.side_effect = lambda _iter: list(_iter)
        assert (
            debsign.pkg_files
            == (m_changes.return_value.return_value, ) * 3)

    assert m_chain.from_iterable.called
    assert (
        list(list(c) for c in m_changes.return_value.call_args_list)
        == [[('FILE1',), {}], [('FILE2',), {}], [('FILE3',), {}]])
