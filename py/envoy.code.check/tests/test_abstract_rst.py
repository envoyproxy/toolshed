
from unittest.mock import MagicMock, PropertyMock

import pytest

from envoy.code import check


def test_rst_punctuation_check_constructor():
    checker = check.APunctuationCheck()
    assert isinstance(checker, check.interface.IRSTCheck)


@pytest.mark.parametrize("correct", [True, False])
def test_rst_punctuation_check_dunder_call(patches, correct):
    checker = check.APunctuationCheck()
    checker.error_message = MagicMock()
    patched = patches(
        "APunctuationCheck._check_punctuation",
        prefix="envoy.code.check.abstract.rst")
    text = MagicMock()

    with patched as (m_check, ):
        m_check.return_value = correct

        assert (
            checker(text)
            == (checker.error_message.format.return_value
                if not correct
                else None))

    if not correct:
        assert (
            checker.error_message.format.call_args
            == [(), dict(snippet=text.__getitem__.return_value)])
        assert (
            text.__getitem__.call_args
            == [(slice(-30, None), ), {}])
    else:
        assert not checker.error_message.format.called
        assert not text.__getitem__.called


def test_rst_punctuation_check_punctuation_re(patches):
    checker = check.APunctuationCheck()
    patched = patches(
        "re",
        "PUNCTUATION_RE",
        prefix="envoy.code.check.abstract.rst")

    with patched as (m_re, m_regex):
        assert (
            checker.punctuation_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [(m_regex, m_re.DOTALL), {}])
    assert "punctuation_re" in checker.__dict__


@pytest.mark.parametrize("matches", [True, False])
@pytest.mark.parametrize("endlist", [True, False])
def test_rst_punctuation_check__check_punctuation(patches, matches, endlist):
    checker = check.APunctuationCheck()
    patched = patches(
        ("APunctuationCheck.punctuation_re",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.rst")
    text = MagicMock()
    (text.split.return_value.__getitem__
               .return_value.startswith
               .return_value) = endlist

    with patched as (m_re, ):
        m_re.return_value.match.return_value = matches
        assert (
            checker._check_punctuation(text)
            == (matches or endlist))

    assert (
        m_re.return_value.match.call_args
        == [(text, ), {}])
    if matches:
        assert not text.split.called
        return
    assert (
        text.split.call_args
        == [("\n", ), {}])
    assert (
        text.split.return_value.__getitem__.call_args
        == [(-1, ), {}])
    assert (
        text.split.return_value.__getitem__.return_value.startswith.call_args
        == [("  *", ), {}])


def test_rst_reflinks_check_constructor():
    checker = check.AReflinksCheck()
    assert isinstance(checker, check.interface.IRSTCheck)


@pytest.mark.parametrize("invalid_reflink", [None, False, "REFLINK"])
def test_rst_reflinks_check_dunder_call(patches, invalid_reflink):
    checker = check.AReflinksCheck()
    checker.error_message = MagicMock()
    patched = patches(
        ("AReflinksCheck.invalid_reflink_re",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.rst")
    text = MagicMock()

    with patched as (m_re, ):
        m_re.return_value.findall.return_value = invalid_reflink
        assert (
            checker(text)
            == (checker.error_message
                if invalid_reflink
                else None))


def test_rst_reflinks_check_invalid_reflink_re(patches):
    checker = check.AReflinksCheck()
    patched = patches(
        "re",
        "INVALID_REFLINK_RE",
        prefix="envoy.code.check.abstract.rst")

    with patched as (m_re, m_regex):
        assert (
            checker.invalid_reflink_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [(m_regex, ), {}])
    assert "invalid_reflink_re" in checker.__dict__


def test_rst_backticks_check_constructor():
    checker = check.ABackticksCheck()
    assert isinstance(checker, check.interface.IRSTCheck)


@pytest.mark.parametrize(
    "single_ticks",
    [None,
     False,
     [f"TICK{i}" for i in range(0, 5)]])
def test_rst_backticks_check_dunder_call(patches, single_ticks):
    checker = check.ABackticksCheck()
    checker.error_message = MagicMock()
    patched = patches(
        "ABackticksCheck._find_single_ticks",
        prefix="envoy.code.check.abstract.rst")
    text = MagicMock()

    with patched as (m_find, ):
        m_find.return_value = single_ticks
        assert (
            checker(text)
            == (checker.error_message.format.return_value
                if single_ticks
                else None))

    assert (
        m_find.call_args
        == [(text, ), {}])
    if not single_ticks:
        assert not checker.error_message.format.called
        return
    assert (
        checker.error_message.format.call_args
        == [(), dict(single_ticks=", ".join(single_ticks))])


def test_rst_backticks_check_link_ticks_re(patches):
    checker = check.ABackticksCheck()
    patched = patches(
        "re",
        "LINK_TICKS_RE",
        prefix="envoy.code.check.abstract.rst")

    with patched as (m_re, m_regex):
        assert (
            checker.link_ticks_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [(m_regex, ), {}])
    assert "link_ticks_re" in checker.__dict__


def test_rst_backticks_check_ref_ticks_re(patches):
    checker = check.ABackticksCheck()
    patched = patches(
        "re",
        "REF_TICKS_RE",
        prefix="envoy.code.check.abstract.rst")

    with patched as (m_re, m_regex):
        assert (
            checker.ref_ticks_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [(m_regex, ), {}])
    assert "ref_ticks_re" in checker.__dict__


def test_rst_backticks_check_single_tick_re(patches):
    checker = check.ABackticksCheck()
    patched = patches(
        "re",
        "SINGLE_TICK_RE",
        prefix="envoy.code.check.abstract.rst")

    with patched as (m_re, m_regex):
        assert (
            checker.single_tick_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [(m_regex, ), {}])
    assert "single_tick_re" in checker.__dict__


def test_rst_backticks__find_single_ticks(iters, patches):
    checker = check.ABackticksCheck()
    patched = patches(
        ("ABackticksCheck.single_tick_re",
         dict(new_callable=PropertyMock)),
        "ABackticksCheck._strip_valid_refs",
        prefix="envoy.code.check.abstract.rst")
    text = MagicMock()
    bad_ticks = iters(cb=lambda i: MagicMock())

    with patched as (m_re, m_strip):
        m_re.return_value.findall.return_value = bad_ticks
        assert (
            checker._find_single_ticks(text)
            == [bad.__getitem__.return_value
                for bad
                in bad_ticks])

    assert (
        m_re.return_value.findall.call_args
        == [(m_strip.return_value, ), {}])
    assert (
        m_strip.call_args
        == [(text, ), {}])
    for bad in bad_ticks:
        assert (
            bad.__getitem__.call_args
            == [(slice(1, -1), ), {}])


def test_rst_backticks__strip_valid_refs(iters, patches):
    checker = check.ABackticksCheck()
    patched = patches(
        ("ABackticksCheck.link_ticks_re",
         dict(new_callable=PropertyMock)),
        ("ABackticksCheck.ref_ticks_re",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.rst")
    text = MagicMock()
    link_ticks = iters(cb=lambda i: f"L{i}", count=3)
    ref_ticks = iters(cb=lambda i: f"R{i}", count=3)

    with patched as (m_link_re, m_ref_re):
        m_ref_re.return_value.findall.return_value = ref_ticks
        m_link_re.return_value.findall.return_value = link_ticks
        assert (
            checker._strip_valid_refs(text)
            == (text.replace.return_value
                    .replace.return_value
                    .replace.return_value
                    .replace.return_value
                    .replace.return_value
                    .replace.return_value))
    assert (
        text.replace.call_args
        == [(ref_ticks[0], ""), {}])
    assert (
        (text.replace.return_value
             .replace.call_args)
        == [(ref_ticks[1], ""), {}])
    assert (
        (text.replace.return_value
             .replace.return_value
             .replace.call_args)
        == [(ref_ticks[2], ""), {}])
    assert (
        (text.replace.return_value
             .replace.return_value
             .replace.return_value
             .replace.call_args)
        == [(link_ticks[0], ""), {}])
    assert (
        (text.replace.return_value
             .replace.return_value
             .replace.return_value
             .replace.return_value
             .replace.call_args)
        == [(link_ticks[1], ""), {}])
    assert (
        (text.replace.return_value
             .replace.return_value
             .replace.return_value
             .replace.return_value
             .replace.return_value
             .replace.call_args)
        == [(link_ticks[2], ""), {}])
