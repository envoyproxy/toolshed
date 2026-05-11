
import pytest

from envoy.docs.sphinx_runner.cmd import cmd, main


@pytest.mark.parametrize(
    "args",
    [[], tuple(f"ARG{i}" for i in range(0, 5))])
def test_main(patches, args):
    patched = patches(
        "SphinxRunner",
        prefix="envoy.docs.sphinx_runner.cmd")

    with patched as (m_runner, ):
        assert main(*args) == m_runner.return_value.return_value

    assert (
        m_runner.call_args
        == [tuple(args), {}])
    assert (
        m_runner.return_value.call_args
        == [(), {}])


def test_cmd(iters, patches):
    patched = patches(
        "sys",
        "main",
        prefix="envoy.docs.sphinx_runner.cmd")
    args = iters(tuple)

    with patched as (m_sys, m_main):
        m_sys.argv.__getitem__.return_value = args
        assert not cmd()

    # sys.exit(main(*sys.argv[1:]))
    assert (
        m_sys.exit.call_args
        == [(m_main.return_value, ), {}])
    assert (
        m_main.call_args
        == [args, {}])
    assert (
        m_sys.argv.__getitem__.call_args
        == [(slice(1, None), ), {}])
