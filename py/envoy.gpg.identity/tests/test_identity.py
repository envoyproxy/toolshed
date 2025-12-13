from unittest.mock import MagicMock, PropertyMock

import pytest

from envoy.gpg import identity


@pytest.mark.parametrize("name", ["NAME", None])
@pytest.mark.parametrize("email", ["EMAIL", None])
@pytest.mark.parametrize("log", ["LOG", None])
@pytest.mark.parametrize("gnupg_home", ["HOME", None])
@pytest.mark.parametrize("gen_key", [None, True, False])
def test_identity_constructor(patches, name, email, log, gnupg_home, gen_key):
    patched = patches(
        "GPGIdentity.gen_key_if_missing",
        prefix="envoy.gpg.identity.identity")
    kwargs = {}
    if gnupg_home is not None:
        kwargs["gnupg_home"] = gnupg_home
    if gen_key is not None:
        kwargs["gen_key"] = gen_key

    with patched as (m_missing, ):
        gpg = identity.GPGIdentity(
            name, email, log, **kwargs)

    assert gpg.provided_name == name
    assert gpg.provided_email == (email or "")
    assert gpg._log == log
    assert gpg._gnupg_home == gnupg_home
    assert gpg.gen_key == (gen_key or False)


def test_identity_dunder_str(patches):
    gpg = identity.GPGIdentity()
    patched = patches(
        ("GPGIdentity.uid", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_uid, ):
        m_uid.return_value = "SOME BODY"
        assert str(gpg) == "SOME BODY"


def test_identity_email(patches):
    gpg = identity.GPGIdentity()
    patched = patches(
        "parseaddr",
        ("GPGIdentity.uid", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_parse, m_uid):
        assert gpg.email == m_parse.return_value.__getitem__.return_value

    assert (
        m_parse.return_value.__getitem__.call_args
        == [(1,), {}])
    assert (
        m_parse.call_args
        == [(m_uid.return_value,), {}])
    assert "email" in gpg.__dict__


def test_identity_fingerprint(patches):
    gpg = identity.GPGIdentity()
    patched = patches(
        ("GPGIdentity.signing_key", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_key, ):
        assert gpg.fingerprint == m_key.return_value.__getitem__.return_value

    assert (
        m_key.return_value.__getitem__.call_args
        == [('fingerprint',), {}])

    assert "fingerprint" not in gpg.__dict__


@pytest.mark.parametrize("name", ["NAME", None])
@pytest.mark.parametrize("email", ["EMAIL", None])
def test_identity_gen_key_data(patches, name, email):
    gpg = identity.GPGIdentity()
    patched = patches(
        ("GPGIdentity.gpg", dict(new_callable=PropertyMock)),
        ("GPGIdentity.provided_email", dict(new_callable=PropertyMock)),
        ("GPGIdentity.provided_name", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_gpg, m_email, m_name):
        m_email.return_value = email
        m_name.return_value = name

        if not (name and email):
            with pytest.raises(identity.GPGError) as e:
                gpg.gen_key_data
            assert (
                e.value.args[0]
                == ("Both `name` and `email` must be provided to generate a "
                    f"key. name: {name}, email: {email}"))
        else:
            assert (
                gpg.gen_key_data
                == m_gpg.return_value.gen_key_input.return_value)

    assert "gen_key_data" not in gpg.__dict__

    if not (name and email):
        assert not m_gpg.called
        return
    assert (
        m_gpg.return_value.gen_key_input.call_args
        == [(),
            dict(name_real=name,
                 name_email=email,
                 key_type="RSA",
                 key_length=2048,
                 no_protection=True)])


def test_identity_gpg(patches):
    gpg = identity.GPGIdentity()
    patched = patches(
        "gnupg.GPG",
        ("GPGIdentity.gnupg_home", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_gpg, m_home):
        assert gpg.gpg == m_gpg.return_value

    assert (
        m_gpg.call_args
        == [(), dict(gnupghome=m_home.return_value)])

    assert "gpg" in gpg.__dict__


@pytest.mark.parametrize("home", [None, "HOME"])
@pytest.mark.parametrize("exists", [True, False])
def test_identity_gnupg_home(patches, home, exists):
    gpg = identity.GPGIdentity()
    patched = patches(
        "os",
        ("GPGIdentity.home", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")
    home = (
        MagicMock()
        if home
        else None)
    gpg._gnupg_home = home

    with patched as (m_os, m_home):
        home_path = (
            m_home.return_value.joinpath.return_value
            if not home
            else home)
        home_path.exists.return_value = exists
        assert (
            gpg.gnupg_home
            == home_path)

    assert "gnupg_home" not in gpg.__dict__
    assert (
        m_os.environ.__setitem__.call_args
        == [("GNUPGHOME", str(home_path)), {}])
    assert (
        home_path.exists.call_args
        == [(), {}])
    if not exists:
        assert (
            home_path.mkdir.call_args
            == [(), {}])
    else:
        assert not home_path.mkdir.called
    if home:
        assert not m_home.called
        return
    assert (
        m_home.return_value.joinpath.call_args
        == [('.gnupg', ), {}])


@pytest.mark.parametrize("gpg1", [None, "GPG"])
@pytest.mark.parametrize("gpg2", [None, "GPG2"])
def test_identity_gpg_bin(patches, gpg1, gpg2):
    gpg = identity.GPGIdentity()
    patched = patches(
        "pathlib",
        "shutil",
        prefix="envoy.gpg.identity.identity")

    def _get_bin(_cmd):
        if _cmd == "gpg2" and gpg2:
            return gpg2
        if _cmd == "gpg" and gpg1:
            return gpg1

    with patched as (m_plib, m_shutil):
        m_shutil.which.side_effect = _get_bin
        if gpg2 or gpg1:
            assert gpg.gpg_bin == m_plib.Path.return_value
        else:
            assert not gpg.gpg_bin

    if gpg2 or gpg1:
        assert (
            m_plib.Path.call_args
            == [(gpg2 or gpg1, ), {}])
    else:
        assert not m_plib.Path.called

    if gpg2:
        assert (
            m_shutil.which.call_args_list
            == [[('gpg2',), {}]])
        return
    assert (
        m_shutil.which.call_args_list
        == [[('gpg2',), {}], [('gpg',), {}]])


def test_identity_home(patches):
    gpg = identity.GPGIdentity()
    patched = patches(
        "os",
        "pathlib",
        "pwd",
        prefix="envoy.gpg.identity.identity")

    with patched as (m_os, m_plib, m_pwd):
        assert gpg.home == m_plib.Path.return_value

    # m_os.environ.__getitem__.return_value
    assert (
        m_plib.Path.call_args
        == [(m_os.environ.get.return_value, ), {}])
    assert (
        m_os.environ.get.call_args
        == [('HOME', m_pwd.getpwuid.return_value.pw_dir), {}])
    assert (
        m_pwd.getpwuid.call_args
        == [(m_os.getuid.return_value,), {}])
    assert (
        m_os.getuid.call_args
        == [(), {}])

    assert "home" in gpg.__dict__


@pytest.mark.parametrize("log", ["LOGGER", None])
def test_identity_log(patches, log):
    gpg = identity.GPGIdentity()
    patched = patches(
        "logging",
        prefix="envoy.gpg.identity.identity")

    gpg._log = log

    with patched as (m_log, ):
        if log:
            assert gpg.log == log
            assert not m_log.getLogger.called
        else:
            assert gpg.log == m_log.getLogger.return_value
            assert (
                m_log.getLogger.call_args
                == [(gpg.__class__.__name__, ), {}])


@pytest.mark.parametrize("name", ["NAME", None])
@pytest.mark.parametrize("email", ["EMAIL", None])
def test_identity_identity_id(patches, name, email):
    gpg = identity.GPGIdentity()
    patched = patches(
        "formataddr",
        ("GPGIdentity.provided_name", dict(new_callable=PropertyMock)),
        ("GPGIdentity.provided_email", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_format, m_name, m_email):
        m_name.return_value = name
        m_email.return_value = email
        result = gpg.provided_id

    assert "provided_id" in gpg.__dict__

    if name and email:
        assert (
            m_format.call_args
            == [(('NAME', 'EMAIL'),), {}])
        assert (
            m_format.return_value.replace.call_args
            == [('"', ''), {}])
        assert result == m_format.return_value.replace.return_value
        return

    assert not m_format.called
    assert result == name or email


def test_identity_name(patches):
    gpg = identity.GPGIdentity()
    patched = patches(
        "parseaddr",
        ("GPGIdentity.uid", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_parse, m_uid):
        assert gpg.name == m_parse.return_value.__getitem__.return_value

    assert (
        m_parse.return_value.__getitem__.call_args
        == [(0,), {}])
    assert (
        m_parse.call_args
        == [(m_uid.return_value,), {}])
    assert "name" in gpg.__dict__


@pytest.mark.parametrize("key", ["KEY1", "KEY2", "KEY5"])
@pytest.mark.parametrize("name", ["NAME", None])
@pytest.mark.parametrize("email", ["EMAIL", None])
def test_identity_signing_key(patches, key, name, email):
    gpg = identity.GPGIdentity()
    _keys = ["KEY1", "KEY2", "KEY3"]
    patched = patches(
        "GPGIdentity.match",
        ("GPGIdentity.gpg", dict(new_callable=PropertyMock)),
        ("GPGIdentity.provided_id", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_match, m_gpg, m_id):
        if not name and not email:
            m_id.return_value = None
        m_match.side_effect = lambda k: (k == key and f"MATCH {k}")
        m_gpg.return_value.list_keys.return_value = _keys
        if key in _keys:
            assert gpg.signing_key == f"MATCH {key}"
            _match_attempts = _keys[:_keys.index(key) + 1]
        else:
            with pytest.raises(identity.GPGError) as e:
                gpg.signing_key
            if name or email:
                assert (
                    e.value.args[0]
                    == f"No key found for '{m_id.return_value}'")
            else:
                assert (
                    e.value.args[0]
                    == 'No available key')
            _match_attempts = _keys

    assert (
        m_gpg.return_value.list_keys.call_args
        == [(True, ), dict(keys=m_id.return_value)])
    assert (
        m_match.call_args_list
        == [[(k,), {}] for k in _match_attempts])


def test_identity_uid(patches):
    gpg = identity.GPGIdentity()
    patched = patches(
        ("GPGIdentity.signing_key", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_key, ):
        assert gpg.uid == m_key.return_value.__getitem__.return_value

    assert (
        m_key.return_value.__getitem__.call_args
        == [('uid',), {}])

    assert "uid" not in gpg.__dict__


def test_identity_export_key(patches):
    gpg = identity.GPGIdentity()
    patched = patches(
        ("GPGIdentity.gpg", dict(new_callable=PropertyMock)),
        ("GPGIdentity.signing_key", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_gpg, m_key):
        assert (
            gpg.export_key()
            == m_gpg.return_value.export_keys.return_value)

    assert (
        m_gpg.return_value.export_keys.call_args
        == [(), dict(keyids=[m_key.return_value.__getitem__.return_value])])
    assert (
        m_key.return_value.__getitem__.call_args
        == [("keyid", ), {}])


@pytest.mark.parametrize("raises", [None, Exception, identity.GPGError])
@pytest.mark.parametrize("fingerprint", [None, "FINGERPRINT"])
def test_identity_gen_key_if_missing(patches, raises, fingerprint):
    gpg = identity.GPGIdentity()
    patched = patches(
        ("GPGIdentity.gen_key_data", dict(new_callable=PropertyMock)),
        ("GPGIdentity.gpg", dict(new_callable=PropertyMock)),
        ("GPGIdentity.signing_key", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_data, m_gpg, m_key):
        if raises is not None:
            m_key.side_effect = raises
        m_gpg.return_value.gen_key.return_value.fingerprint = fingerprint

        if raises == Exception:
            with pytest.raises(raises):
                gpg.gen_key_if_missing()
        elif raises and not fingerprint:
            with pytest.raises(identity.GPGError) as e:
                gpg.gen_key_if_missing()
            assert e.value.args[0] == "Failed to generate key"
        else:
            assert not gpg.gen_key_if_missing()

    if raises != identity.GPGError:
        assert not m_gpg.called
        assert not m_data.called
        return
    assert (
        m_gpg.return_value.gen_key.call_args
        == [(m_data.return_value, ), {}])


@pytest.mark.parametrize("name", ["NAME", None])
@pytest.mark.parametrize("email", ["EMAIL", None])
@pytest.mark.parametrize("match", ["MATCH", None])
@pytest.mark.parametrize("log", [True, False])
@pytest.mark.parametrize("gen_key", [True, False])
def test_identity_match(patches, name, email, match, log, gen_key):
    gpg = identity.GPGIdentity()
    patched = patches(
        "GPGIdentity._match_key",
        ("GPGIdentity.gen_key", dict(new_callable=PropertyMock)),
        ("GPGIdentity.provided_id", dict(new_callable=PropertyMock)),
        ("GPGIdentity.log", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")
    key = dict(uids=["UID1", "UID2"])

    with patched as (m_match, m_gen, m_id, m_log):
        if not log:
            m_log.return_value = None
        m_match.return_value = match
        m_gen.return_value = gen_key
        m_id.return_value = name or email
        result = gpg.match(key)

    if not name and not email:
        assert not m_match.called
        if gen_key:
            assert not m_log.called
            assert not result
            return
        if log:
            assert (
                m_log.return_value.warning.call_args
                == [(('No GPG name/email supplied, '
                      'signing with first available key'),),
                    {}])
        assert (
            result
            == {'uids': ['UID1', 'UID2'], 'uid': 'UID1'})
        return
    assert (
        m_match.call_args
        == [(key["uids"],), {}])
    if log:
        assert not m_log.return_value.warning.called
    if match:
        assert (
            result
            == {'uids': ['UID1', 'UID2'], 'uid': 'MATCH'})
    else:
        assert not result


@pytest.mark.parametrize("uids", [[], ["UID1"], ["UID1", "UID2"]])
@pytest.mark.parametrize("email", [None, "UID1", "UID1", "UID2", "UID3"])
def test_identity__match_email(patches, uids, email):
    gpg = identity.GPGIdentity()
    patched = patches(
        "parseaddr",
        ("GPGIdentity.provided_email", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_parse, m_email):
        m_parse.side_effect = lambda _email: ("NAME", _email)
        m_email.return_value = email
        result = gpg._match_email(uids)

    if email in uids:
        assert result == email
        assert (
            m_parse.call_args_list
            == [[(uid,), {}] for uid in uids[:uids.index(email) + 1]])
        return

    assert not result
    assert (
        m_parse.call_args_list
        == [[(uid,), {}] for uid in uids])


@pytest.mark.parametrize("name", ["NAME", None])
@pytest.mark.parametrize("email", ["EMAIL", None])
def test_identity__match_key(patches, name, email):
    gpg = identity.GPGIdentity()
    patched = patches(
        "GPGIdentity._match_email",
        "GPGIdentity._match_name",
        "GPGIdentity._match_uid",
        ("GPGIdentity.provided_email", dict(new_callable=PropertyMock)),
        ("GPGIdentity.provided_name", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")
    key = dict(uids=["UID1", "UID2"])

    with patched as (m_email, m_name, m_uid, m_pemail, m_pname):
        m_pemail.return_value = email
        m_pname.return_value = name
        result = gpg._match_key(key)

    if name and email:
        assert (
            m_uid.call_args
            == [(dict(uids=key["uids"]),), {}])
        assert not m_email.called
        assert not m_name.called
        assert result == m_uid.return_value
    elif name:
        assert (
            m_name.call_args
            == [(dict(uids=key["uids"]),), {}])
        assert not m_email.called
        assert not m_uid.called
        assert result == m_name.return_value
    elif email:
        assert (
            m_email.call_args
            == [(dict(uids=key["uids"]),), {}])
        assert not m_name.called
        assert not m_uid.called
        assert result == m_email.return_value


@pytest.mark.parametrize("uids", [[], ["UID1"], ["UID1", "UID2"]])
@pytest.mark.parametrize("name", [None, "UID1", "UID1", "UID2", "UID3"])
def test_identity__match_name(patches, uids, name):
    gpg = identity.GPGIdentity()
    patched = patches(
        "parseaddr",
        ("GPGIdentity.provided_name", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_parse, m_name):
        m_parse.side_effect = lambda _name: (_name, "EMAIL")
        m_name.return_value = name
        result = gpg._match_name(uids)

    if name in uids:
        assert result == name
        assert (
            m_parse.call_args_list
            == [[(uid,), {}] for uid in uids[:uids.index(name) + 1]])
        return

    assert not result
    assert (
        m_parse.call_args_list
        == [[(uid,), {}] for uid in uids])


@pytest.mark.parametrize("uid", ["UID1", "UID7"])
def test_identity__match_uid(patches, uid):
    gpg = identity.GPGIdentity()
    uids = [f"UID{i}" for i in range(5)]
    matches = uid in uids
    patched = patches(
        ("GPGIdentity.provided_id", dict(new_callable=PropertyMock)),
        prefix="envoy.gpg.identity.identity")

    with patched as (m_id, ):
        m_id.return_value = uid
        if matches:
            assert gpg._match_uid(uids) == uid
        else:
            assert not gpg._match_uid(uids)
