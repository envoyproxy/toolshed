
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from envoy.code import check


class _DummyRuntimeGuardsCheck(check.ARuntimeGuardsCheck):
    pass


class DummyRuntimeGuardsCheck(_DummyRuntimeGuardsCheck):

    def __init__(self):
        pass


def test_runtimeguardscheck_constructor(patches):
    patched = patches(
        "abstract.AProjectCodeCheck.__init__",
        prefix="envoy.code.check.abstract.runtime_guards")

    with patched as (m_super, ):
        m_super.return_value = None
        guards = _DummyRuntimeGuardsCheck("PROJECT")

    assert isinstance(guards, check.AProjectCodeCheck)
    assert (
        m_super.call_args
        == [("PROJECT", ), {}])


async def test_runtimeguardscheck_configured(iters, patches):
    guards = DummyRuntimeGuardsCheck()
    patched = patches(
        "set",
        ("ARuntimeGuardsCheck._grepped",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.runtime_guards")
    grepped = iters(cb=lambda i: MagicMock())

    with patched as (m_set, m_grepped):
        m_grepped.side_effect = AsyncMock(return_value=grepped)
        assert (
            await guards.configured
            == m_set.return_value
            == getattr(
                guards,
                check.ARuntimeGuardsCheck.configured.cache_name)["configured"])
        resultgen = m_set.call_args[0][0]
        resultlist = list(resultgen)

    assert isinstance(resultgen, types.GeneratorType)
    assert (
        resultlist
        == [(g.split.return_value.__getitem__
                    .return_value.__getitem__.return_value)
            for g
            in grepped])
    assert (
        m_set.call_args
        == [(resultgen, ), {}])
    for g in grepped:
        assert (
            g.split.call_args
            == [(":", ), {}])
        assert (
            g.split.return_value.__getitem__.call_args
            == [(1, ), {}])
        assert (
            g.split.return_value.__getitem__.return_value.__getitem__.call_args
            == [(slice(14, -2), ), {}])


def test_runtimeguardscheck_expected_missing(patches):
    guards = DummyRuntimeGuardsCheck()
    patched = patches(
        "set",
        "EXPECTED_MISSING_GUARDS",
        prefix="envoy.code.check.abstract.runtime_guards")

    with patched as (m_set, m_missing):
        assert (
            guards.expected_missing
            == m_set.return_value)

    assert (
        m_set.call_args
        == [(m_missing, ), {}])
    assert "expected_missing" in guards.__dict__


async def test_runtimeguardscheck_mentioned(iters, patches):
    guards = DummyRuntimeGuardsCheck()
    patched = patches(
        ("ARuntimeGuardsCheck._changes",
         dict(new_callable=PropertyMock)),
        "ARuntimeGuardsCheck._find_mention",
        prefix="envoy.code.check.abstract.runtime_guards")

    def find_mention(x):
        return iters(set, cb=lambda i: f"X{i}", start=x, count=3)

    async def changes():
        for x in range(0, 10):
            yield x

    with patched as (m_changes, m_mention):
        m_changes.side_effect = changes
        m_mention.side_effect = find_mention
        assert (
            await guards.mentioned
            == set(f"X{i}" for i in range(0, 12)))

    assert not hasattr(
        guards,
        check.ARuntimeGuardsCheck.mentioned.cache_name)


async def test_runtimeguardscheck_missing(patches):
    guards = DummyRuntimeGuardsCheck()
    patched = patches(
        "set",
        ("ARuntimeGuardsCheck.configured",
         dict(new_callable=PropertyMock)),
        ("ARuntimeGuardsCheck.mentioned",
         dict(new_callable=PropertyMock)),
        ("ARuntimeGuardsCheck.expected_missing",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.runtime_guards")

    with patched as (m_set, m_config, m_mentioned, m_missing):
        m_config.side_effect = AsyncMock(return_value=23)
        m_mentioned.side_effect = AsyncMock(return_value=7)
        m_missing.return_value = 3
        assert (
            await guards.missing
            == m_set.return_value
            == getattr(
                guards,
                check.ARuntimeGuardsCheck.missing.cache_name)["missing"])

    assert (
        m_set.call_args
        == [(13, ), {}])


def test_runtimeguardscheck_reloadable_match_re(patches):
    guards = DummyRuntimeGuardsCheck()
    patched = patches(
        "re",
        "RELOADABLE_MATCH_RE",
        prefix="envoy.code.check.abstract.runtime_guards")

    with patched as (m_re, m_match_re):
        assert (
            guards.reloadable_match_re
            == m_re.compile.return_value)

    assert (
        m_re.compile.call_args
        == [(m_match_re, ), {}])
    assert "reloadable_match_re" in guards.__dict__


async def test_runtimeguardscheck_status(iters, patches):
    guards = DummyRuntimeGuardsCheck()
    patched = patches(
        "sorted",
        ("ARuntimeGuardsCheck.configured",
         dict(new_callable=PropertyMock)),
        ("ARuntimeGuardsCheck.expected_missing",
         dict(new_callable=PropertyMock)),
        ("ARuntimeGuardsCheck.missing",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.runtime_guards")
    configured = iters(cb=lambda i: MagicMock(), count=20)
    missing = iters(cb=lambda i: configured[i], start=3, count=7)
    expected_missing = iters(cb=lambda i: configured[i], start=7, count=6)
    results = []

    with patched as (m_sort, m_config, m_exp_missing, m_missing):
        _config = AsyncMock()
        m_config.side_effect = _config
        _missing = AsyncMock(return_value=missing)
        m_missing.side_effect = _missing
        m_exp_missing.return_value = expected_missing
        m_sort.return_value = configured

        async for guard, status in guards.status:
            results.append((guard, status))

    assert (
        results
        == [(g,
             (False
              if g in missing
              else (None
                    if g in expected_missing
                    else True)))
            for g in configured])

    assert (
        m_sort.call_args
        == [(_config.return_value, ), {}])
    assert not hasattr(
        guards,
        check.ARuntimeGuardsCheck.status.cache_name)


async def test_runtimeguardscheck__changes(iters):
    guards = DummyRuntimeGuardsCheck()
    guards.project = MagicMock()
    changelogs = []
    all_items = []
    for i in range(0, 5):
        changelog = MagicMock()
        data = MagicMock()
        changelog.data = AsyncMock(return_value=data)()
        items = {
            f"K{i}_{x}": iters(cb=lambda i: MagicMock())
            for x in range(0, 5)}
        for v in items.values():
            all_items.extend(v)
        items["date"] = "DATE"
        data.items.return_value = items.items()
        changelogs.append(changelog)
    guards.project.changelogs.values.return_value = changelogs
    results = []

    async for result in guards._changes:
        results.append(result)

    assert (
        results
        == [i.__getitem__.return_value for i in all_items])
    for i in all_items:
        assert (
            i.__getitem__.call_args
            == [("change", ), {}])
    assert not hasattr(
        guards,
        check.ARuntimeGuardsCheck._changes.cache_name)


def test_runtimeguardscheck__grepped(patches):
    guards = DummyRuntimeGuardsCheck()
    guards.directory = MagicMock()
    patched = patches(
        "RELOADABLE_GUARD_GREP_RE",
        "RUNTIME_GUARDS_CONFIG_PATH",
        prefix="envoy.code.check.abstract.runtime_guards")

    with patched as (m_re, m_config):
        assert (
            guards._grepped
            == guards.directory.grep.return_value)

    assert (
        guards.directory.grep.call_args
        == [(["-E", m_re], m_config), {}])
    assert "_grepped" not in guards.__dict__


def test_runtimeguardscheck__find_mention(iters, patches):
    guards = DummyRuntimeGuardsCheck()
    guards.directory = MagicMock()
    patched = patches(
        "set",
        ("ARuntimeGuardsCheck.reloadable_match_re",
         dict(new_callable=PropertyMock)),
        prefix="envoy.code.check.abstract.runtime_guards")
    change = MagicMock()
    found = iters(cb=lambda i: MagicMock())

    with patched as (m_set, m_re):
        m_re.return_value.findall.return_value = found
        assert (
            guards._find_mention(change)
            == m_set.return_value)
        resultgen = m_set.call_args[0][0]
        resultlist = list(resultgen)

    assert isinstance(resultgen, types.GeneratorType)
    assert (
        resultlist
        == [f.strip.return_value.replace.return_value
            for f in found])
    assert (
        m_set.call_args
        == [(resultgen, ), {}])
    for f in found:
        assert (
            f.strip.call_args
            == [("`", ), {}])
        assert (
            f.strip.return_value.replace.call_args
            == [(".", "_"), {}])
    assert (
        m_re.return_value.findall.call_args
        == [(change, ), {}])
