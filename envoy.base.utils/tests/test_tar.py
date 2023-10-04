from unittest.mock import MagicMock

import pytest

from envoy.base import utils


@pytest.mark.parametrize(
    "path",
    ["x.foo", "x.bar", "x.tar", "x.tar.xz", "x.xz"])
def test_is_tarlike(patches, path):
    matches = False
    for ext in utils.TAR_EXTS:
        if path.endswith(ext):
            matches = True
            break
    assert utils.is_tarlike(path) == matches


@pytest.mark.parametrize("mode", [None, "r", "w"])
@pytest.mark.parametrize(
    "path",
    ["foo", "foo.tar", "foo.tar.gz", "foo.tar.xz", "foo.tar.bz2"])
def test_tar_mode(mode, path):
    m_path = MagicMock()
    m_path.__str__.return_value = path
    expected = mode or "r"
    suffixes = ["gz", "bz2", "xz"]
    for suffix in suffixes:
        if str(path).endswith(f".{suffix}"):
            expected = f"{mode or 'r'}:{suffix}"
            break
    kwargs = {}
    if mode:
        kwargs["mode"] = mode
    assert (
        utils.tar_mode(m_path, **kwargs)
        == expected)


@pytest.mark.parametrize("tarballs", [0, 3])
@pytest.mark.parametrize("mappings", [0, 3])
@pytest.mark.parametrize("matching", [True, False])
@pytest.mark.parametrize("inmem", [None, True, False])
def test_util_extract(patches, tarballs, mappings, matching, inmem, iters):
    kwargs = dict(inmem=inmem) if inmem is not None else {}
    inmem = inmem if inmem is not None else True
    patched = patches(
        "pathlib",
        "_extract",
        "_mv_paths",
        "_rm_paths",
        "_open",
        prefix="envoy.base.utils.tar")
    tarballs = iters(tuple, cb=lambda i: f"TARB{i}", count=tarballs)
    mappings = iters(dict, count=mappings)
    matching = MagicMock() if matching else None

    with patched as (m_plib, m_extract, m_mv, m_rm, m_open):
        _extraction = [MagicMock(), MagicMock()]
        m_open.return_value.__enter__.return_value = _extraction
        if tarballs:
            assert (
                utils.extract(
                    "PATH", *tarballs,
                    mappings=mappings,
                    matching=matching,
                    **kwargs)
                == m_plib.Path.return_value)
        else:
            with pytest.raises(utils.ExtractError) as e:
                utils.extract(
                    "PATH", *tarballs,
                    mappings=mappings,
                    matching=matching,
                    **kwargs)

    if not tarballs:
        assert (
            e.value.args[0]
            == 'No tarballs specified for extraction to PATH')
        assert not m_open.called
        assert not m_mv.called
        assert not m_rm.called
        assert not m_extract.called
        if matching:
            assert not matching.match.called
        return
    assert (
        m_plib.Path.call_args
        == [("PATH", ), {}])
    assert (
        m_open.call_args_list
        == [[(tarb, inmem), {}] for tarb in tarballs])
    assert (
        m_extract.call_args_list
        == [[(m_plib.Path.return_value, *_extraction, matching, mappings), {}]
            for tarb in tarballs])
    assert (
        m_mv.call_args
        == [(m_plib.Path.return_value, mappings), {}])
    assert (
        m_rm.call_args
        == [(m_plib.Path.return_value, matching), {}])


@pytest.mark.parametrize("zst", [True, False])
def test_util_pack(patches, zst):
    patched = patches(
        "str",
        "_pack",
        "_pack_zst",
        prefix="envoy.base.utils.tar")
    path = MagicMock()
    out = MagicMock()
    include = MagicMock()

    with patched as (m_str, m_pack, m_zst):
        m_str.return_value.endswith.return_value = zst
        assert not utils.pack(path, out, include)

    assert (
        m_str.call_args
        == [(out, ), {}])
    assert (
        m_str.return_value.endswith.call_args
        == [(".zst", ), {}])
    if zst:
        assert (
            m_zst.call_args
            == [(path, out), dict(include=include)])
        return
    assert (
        m_pack.call_args
        == [(path, out), dict(include=include)])


@pytest.mark.parametrize("inmem", [None, True, False])
def test_util_repack(patches, inmem, iters):
    kwargs = dict(inmem=inmem) if inmem is not None else {}
    inmem = inmem if inmem is not None else True
    patched = patches(
        "untar",
        "pack",
        prefix="envoy.base.utils.tar")
    paths = iters(cb=MagicMock)
    out = MagicMock()
    include = MagicMock()
    matching = MagicMock()
    mappings = MagicMock()

    with patched as (m_untar, m_pack):
        repack = utils.repack(
            out,
            *paths,
            matching=matching,
            mappings=mappings,
            include=include,
            **kwargs)
        with repack as tardir:
            assert not m_pack.called

    assert (
        tardir
        == m_untar.return_value.__enter__.return_value)
    assert (
        m_untar.call_args
        == [tuple(paths),
            dict(matching=matching,
                 mappings=mappings,
                 inmem=inmem)])
    assert (
        m_pack.call_args
        == [(tardir, out), dict(include=include)])


@pytest.mark.parametrize(
    "tarballs",
    [(), tuple("TARB{i}" for i in range(0, 3))])
@pytest.mark.parametrize("inmem", [None, True, False])
def test_util_untar(patches, tarballs, inmem, iters):
    kwargs = dict(inmem=inmem) if inmem is not None else {}
    inmem = inmem if inmem is not None else True
    patched = patches(
        "tempfile.TemporaryDirectory",
        "extract",
        prefix="envoy.base.utils.tar")
    mappings = iters(dict)
    matching = MagicMock()

    with patched as (m_tmp, m_extract):
        untarred = utils.untar(
            *tarballs,
            matching=matching,
            mappings=mappings,
            **kwargs)
        with untarred as tmpdir:
            assert tmpdir == m_extract.return_value

    assert (
        m_tmp.call_args
        == [(), {}])
    assert (
        m_extract.call_args
        == [(m_tmp.return_value.__enter__.return_value, ) + tarballs,
            dict(matching=matching, mappings=mappings, inmem=inmem)])


@pytest.mark.parametrize("tarballs", [0, 3])
@pytest.mark.parametrize("mappings", [0, 3])
@pytest.mark.parametrize("matching", [True, False])
def test_util__extract(patches, tarballs, mappings, matching, iters):
    matching = MagicMock() if matching else matching
    path = MagicMock()
    prefix = MagicMock()
    tar = MagicMock()
    mappings = iters(dict, count=mappings)
    members = iters(cb=lambda x: MagicMock(return_value=x))
    tar.getmembers.return_value = members
    patched = patches(
        "logger",
        "_should_extract",
        prefix="envoy.base.utils.tar")

    with patched as (m_logger, m_should):
        m_should.side_effect = lambda x, y, z: x() % 2
        assert not utils.tar._extract(path, prefix, tar, matching, mappings)

    if not matching:
        assert (
            path.joinpath.call_args
            == [(prefix, ), {}])
        assert (
            tar.extractall.call_args
            == [(), dict(path=path.joinpath.return_value)])
        assert not tar.getmembers.called
        assert not tar.extract.called
        assert not m_should.called
        assert len(path.joinpath.call_args_list) == 1
        assert not m_logger.debug.called
        return
    assert not tar.extractall.called
    assert (
        m_should.call_args_list
        == [[(member, matching, mappings), {}]
            for member in members])
    assert (
        tar.extract.call_args_list
        == [[(member, ),
             dict(path=path.joinpath.return_value)]
            for member in members if member() % 2])
    assert (
        m_logger.debug.call_args_list
        == [[(f"Extracting: {member.name} "
              f"-> {path.joinpath.return_value}", ), {}]
            for member in members if member() % 2])


@pytest.mark.parametrize("mappings", [0, 3])
def test_util__mv_paths(patches, mappings, iters):
    path = MagicMock()
    mappings = iters(dict, count=mappings) if mappings else None
    patched = patches(
        "shutil",
        prefix="envoy.base.utils.tar")

    with patched as (m_shutil, ):
        assert not utils.tar._mv_paths(path, mappings)

    expected = []
    for src, dest in (mappings or {}).items():
        expected.append([(src, ), {}])
        expected.append([(dest, ), {}])
    assert (
        path.joinpath.call_args_list
        == expected)
    assert (
        path.joinpath.return_value.parent.mkdir.call_args_list
        == [[(), dict(exist_ok=True, parents=True)]
            for m in (mappings or {})])
    assert (
        m_shutil.move.call_args_list
        == [[(path.joinpath.return_value, path.joinpath.return_value), {}]
            for m in (mappings or {})])


@pytest.mark.parametrize("prefix", [True, False])
@pytest.mark.parametrize("zst", [True, False])
@pytest.mark.parametrize("inmem", [None, True, False])
def test_util__open(patches, prefix, zst, inmem):
    args = (inmem, ) if inmem is not None else ()
    inmem = inmem if inmem is not None else True
    patched = patches(
        "str",
        "tarfile",
        "_opener",
        "_open_zst",
        prefix="envoy.base.utils.tar")
    path = MagicMock()
    splitted = [MagicMock(), MagicMock()]
    str_path = MagicMock()

    with patched as (m_str, m_tar, m_open, m_zst):
        m_str.return_value = str_path
        m_str.return_value.__contains__.return_value = prefix
        m_str.return_value.split.return_value = splitted
        if prefix:
            _prefix = splitted[0]
            _path = splitted[1]
        else:
            _prefix = ""
            _path = m_str.return_value
        _path.endswith.return_value = zst
        assert (
            utils.tar._open(path, *args)
            == m_open.return_value)

    assert (
        m_str.call_args
        == [(path, ), {}])
    assert (
        m_str.return_value.__contains__.call_args
        == [(":", ), {}])
    if not prefix:
        assert not m_str.return_value.split.called
    else:
        assert (
            m_str.return_value.split.call_args
            == [(":", ), {}])
    assert (
        _path.endswith.call_args
        == [(".zst", ), {}])
    if zst:
        assert not m_tar.open.called
        assert (
            m_open.call_args
            == [(m_zst.return_value, _prefix), {}])
        assert (
            m_zst.call_args
            == [(_path, inmem), {}])
        return
    assert (
        m_tar.open.call_args
        == [(_path, ), {}])
    assert (
        m_open.call_args
        == [(m_tar.open.return_value, _prefix), {}])
    assert not m_zst.called


@pytest.mark.parametrize("inmem", [None, True, False])
def test_util__open_zst(patches, inmem):
    args = (inmem, ) if inmem is not None else ()
    inmem = inmem if inmem is not None else True
    patched = patches(
        "io",
        "pathlib",
        "tarfile",
        "tempfile",
        "zstandard",
        prefix="envoy.base.utils.tar")
    path = MagicMock()
    infile = MagicMock()

    with patched as (m_io, m_plib, m_tar, m_temp, m_zst):
        (m_plib.Path.return_value
                    .expanduser.return_value
                    .open.return_value
                    .__enter__.return_value) = infile
        assert (
            utils.tar._open_zst(path, *args)
            == m_tar.open.return_value)

    assert (
        m_plib.Path.call_args
        == [(path, ), {}])
    assert (
        m_plib.Path.return_value.expanduser.call_args
        == [(), {}])
    assert (
        m_zst.ZstdDecompressor.call_args
        == [(), {}])
    if inmem:
        assert (
            m_io.BytesIO.call_args
            == [(), {}])
        assert not m_temp.TemporaryFile.called
        file_handler = m_io.BytesIO.return_value
    else:
        assert (
            m_temp.TemporaryFile.call_args
            == [(), dict(suffix=".tar")])
        assert not m_io.BytesIO.called
        file_handler = m_temp.TemporaryFile.return_value
    assert (
        (m_plib.Path.return_value
                    .expanduser.return_value
                    .open.call_args)
        == [("rb", ), {}])
    assert (
        m_zst.ZstdDecompressor.return_value.copy_stream.call_args
        == [(infile, file_handler), {}])
    assert (
        file_handler.seek.call_args
        == [(0, ), {}])
    assert (
        m_tar.open.call_args
        == [(), dict(fileobj=file_handler)])


@pytest.mark.parametrize("prefix", [True, False])
@pytest.mark.parametrize("fileobj", [True, False])
def test_util__opener(prefix, fileobj):
    tarball = MagicMock()
    prefix = MagicMock() if prefix else prefix
    _fileobj = MagicMock()
    tdict = dict(fileobj=_fileobj) if fileobj else {}
    tarball.__enter__.return_value.__dict__ = tdict

    with utils.tar._opener(tarball, prefix) as result:
        assert not _fileobj.close.called

    if fileobj:
        assert (
            _fileobj.close.call_args
            == [(), {}])
    else:
        assert not _fileobj.close.called
    assert result == (prefix, tarball.__enter__.return_value)


@pytest.mark.parametrize("matching", [True, False])
def test_util__rm_paths(patches, iters, matching):
    path = MagicMock()
    matching = MagicMock() if matching else matching
    if matching:
        matching.match.side_effect = lambda x: x % 2
    patched = patches(
        "shutil",
        prefix="envoy.base.utils.tar")

    def _glob(x):
        m = MagicMock()
        m.name = x
        return m
    globs = iters(cb=lambda x: _glob(x))
    path.glob.return_value = globs

    with patched as (m_shutil, ):
        assert not utils.tar._rm_paths(path, matching)

    if not matching:
        assert not path.glob.called
        assert not m_shutil.rmtree.called
        return
    assert (
        path.glob.call_args
        == [("*", ), {}])
    assert (
        matching.match.call_args_list
        == [[(g.name, ), {}]
            for g in globs])
    assert (
        m_shutil.rmtree.call_args_list
        == [[(g, ), {}]
            for g in globs
            if not g.name % 2])


@pytest.mark.parametrize("matching", [True, False])
@pytest.mark.parametrize("matches", [True, False])
@pytest.mark.parametrize("mappings", [[], range(3), ["X", "Y", "Z"]])
def test_util__should_extract(patches, matching, matches, mappings):
    member = MagicMock()
    member.name = "Y"
    matching = MagicMock() if matching else matching
    if matching:
        matching.match.return_value = matches
    patched = patches(
        "bool",
        prefix="envoy.base.utils.tar")

    with patched as (m_bool, ):
        assert (
            utils.tar._should_extract(member, matching, mappings)
            == m_bool.return_value)

    assert (
        m_bool.call_args
        == [((matching and matches) or (member.name in mappings), ), {}])


@pytest.mark.parametrize("zst", [True, False])
def test_util__pack(patches, zst):
    patched = patches(
        "tarfile",
        "tar_mode",
        "_prune",
        prefix="envoy.base.utils.tar")
    path = MagicMock()
    out = MagicMock()
    include = MagicMock()

    with patched as (m_tar, m_mode, m_prune):
        assert not utils.tar._pack(path, out, include)

    assert (
        m_tar.open.call_args
        == [(out, ),
            dict(mode=m_mode.return_value)])
    assert (
        m_mode.call_args
        == [(out, ),
            dict(mode="w")])
    assert (
        m_tar.open.return_value.__enter__.return_value.add.call_args
        == [(m_prune.return_value, ),
            dict(arcname=".")])
    assert (
        m_prune.call_args
        == [(path, include), {}])


@pytest.mark.parametrize("zst", [True, False])
def test_util__pack_zst(patches, zst):
    patched = patches(
        "io",
        "open",
        "tarfile",
        "zstandard",
        "_prune",
        prefix="envoy.base.utils.tar")
    path = MagicMock()
    out = MagicMock()
    include = MagicMock()

    with patched as (m_io, m_open, m_tar, m_zst, m_prune):
        assert not utils.tar._pack_zst(path, out, include)

    assert (
        m_io.BytesIO.call_args
        == [(), {}])
    assert (
        m_zst.ZstdCompressor.call_args
        == [(), dict(threads=-1)])
    assert (
        m_tar.open.call_args
        == [(),
            dict(fileobj=m_io.BytesIO.return_value,
                 mode="w")])
    assert (
        m_tar.open.return_value.__enter__.return_value.add.call_args
        == [(m_prune.return_value, ), dict(arcname=".")])
    assert (
        m_prune.call_args
        == [(path, include), {}])
    assert (
        m_io.BytesIO.return_value.seek.call_args
        == [(0, ), {}])
    assert (
        m_open.call_args
        == [(out, "wb"), {}])
    assert (
        m_zst.ZstdCompressor.return_value.copy_stream.call_args
        == [(m_io.BytesIO.return_value,
             m_open.return_value.__enter__.return_value),
            {}])


@pytest.mark.parametrize("include", [True, False])
def test_util__prune(patches, include, iters):
    patched = patches(
        "pathlib",
        "shutil",
        prefix="envoy.base.utils.tar")
    path = MagicMock()
    include = MagicMock() if include else include
    if include:
        include.match.side_effect = lambda x: bool(x % 3)

    def submock(i):
        mock = MagicMock()
        mock.is_dir.return_value = bool(i % 2)
        mock.name = i
        return mock

    globs = iters(cb=submock, count=10)

    with patched as (m_plib, m_shutil):
        m_plib.Path.return_value.glob.return_value = globs
        assert (
            utils.tar._prune(path, include)
            == m_plib.Path.return_value)

    assert (
        m_plib.Path.call_args
        == [(path, ), {}])
    if not include:
        assert not m_plib.Path.return_value.glob.called
        assert not m_shutil.called
        return
    assert (
        m_plib.Path.return_value.glob.call_args
        == [("*", ), {}])
    assert (
        include.match.call_args_list
        == [[(g.name, ), {}]
            for g in globs])
    assert (
        include.match.call_args_list
        == [[(g.name, ), {}]
            for g in globs])
    assert (
        m_shutil.rmtree.call_args_list
        == [[(g, ), {}]
            for g in globs if (not g.name % 3 and g.name % 2)])
    for sub in globs:
        if sub.name % 3:
            assert not sub.is_dir.called
            assert not sub.unlink.called
            return
        assert (
            sub.is_dir.call_args
            == [(), {}])
        if sub.name % 2:
            assert not sub.unlink.called
            return
        assert (
            sub.unlink.call_args
            == [(), {}])
