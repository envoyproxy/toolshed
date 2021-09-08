
from unittest.mock import MagicMock, PropertyMock

import pytest

import abstracts

from envoy.base.utils import abstract


@abstracts.implementer(abstract.ABazelQuery)
class DummyBazelQuery:

    @property
    def path(self):
        return super().path


def test_bazel_query_constructor():
    with pytest.raises(TypeError):
        abstract.ABazelQuery()

    query = DummyBazelQuery()

    with pytest.raises(NotImplementedError):
        query.path


def test_bazel_query_query_kwargs(patches):
    query = DummyBazelQuery()
    patched = patches(
        ("ABazelQuery.path",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract")

    with patched as (m_path, ):
        assert (
            query.query_kwargs
            == dict(
                cwd=str(m_path.return_value),
                encoding="utf-8",
                capture_output=True))

    assert "path" not in query.__dict__


def test_bazel_query_query(patches):
    query = DummyBazelQuery()
    patched = patches(
        "ABazelQuery.handle_query_response",
        "ABazelQuery.run_query",
        prefix="envoy.base.utils.abstract")

    with patched as (m_handle, m_run):
        assert query.query("EXPRESSION") == m_handle.return_value

    assert (
        list(m_handle.call_args)
        == [(m_run.return_value, ), {}])
    assert (
        list(m_run.call_args)
        == [("EXPRESSION", ), {}])


@pytest.mark.parametrize("failed", [True, False])
def test_bazel_query_handle_query_response(patches, failed):
    query = DummyBazelQuery()
    patched = patches(
        "ABazelQuery.query_failed",
        prefix="envoy.base.utils.abstract")
    response = MagicMock()

    with patched as (m_failed, ):
        m_failed.return_value = failed
        if failed:
            with pytest.raises(abstract.BazelQueryError) as e:
                query.handle_query_response(response)
        else:
            assert (
                query.handle_query_response(response)
                == response.stdout.strip.return_value.split.return_value)

    if failed:
        assert (
            e.value.args[0]
            == (f"\n{response.stdout.strip.return_value}"
                f"{response.stderr.strip.return_value}"))
        assert not response.stdout.called
        return

    assert (
        list(response.stdout.strip.call_args)
        == [(), {}])
    assert (
        list(response.stdout.strip.return_value.split.call_args)
        == [("\n", ), {}])


def test_bazel_query_query_command():
    assert (
        DummyBazelQuery().query_command("EXPRESSION")
        == ("bazel", "query", "EXPRESSION"))


@pytest.mark.parametrize("returncode", [0, 1])
@pytest.mark.parametrize(
    "message",
    ["OK",
     "[bazel release",
     "  [bazel release",
     "  [bazel release NOT OK",
     "OK  [bazel release"])
def test_bazel_query_query_failed(returncode, message):
    query = DummyBazelQuery()
    response = MagicMock()
    response.returncode = returncode
    response.stdout = message
    assert (
        query.query_failed(response)
        if returncode or message.strip().startswith("[bazel release")
        else not query.query_failed(response))


def test_bazel_query_run_query(patches):
    query = DummyBazelQuery()
    patched = patches(
        "subprocess",
        "ABazelQuery.query_command",
        ("ABazelQuery.query_kwargs",
         dict(new_callable=PropertyMock)),
        prefix="envoy.base.utils.abstract")
    kwargs = dict(FOO1="bar", FOO2="baz")

    with patched as (m_sub, m_command, m_kwargs):
        m_kwargs.return_value = kwargs
        assert (
            query.run_query("EXPRESSION")
            == m_sub.run.return_value)

    assert (
        list(m_sub.run.call_args)
        == [(m_command.return_value, ), kwargs])
    assert (
        list(m_command.call_args)
        == [("EXPRESSION", ), {}])
