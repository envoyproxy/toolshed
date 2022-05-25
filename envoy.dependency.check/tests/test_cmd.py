
import pytest

from envoy.dependency.check import main, run


@pytest.mark.parametrize(
    "args",
    [[], tuple(f"ARG{i}" for i in range(0, 5))])
def test_cmd_main(patches, args):
    patched = patches(
        "DependencyChecker",
        prefix="envoy.dependency.check.cmd")

    with patched as (m_checker, ):
        assert main(*args) == m_checker.return_value.return_value

    assert (
        m_checker.call_args
        == [tuple(args), {}])
    assert (
        m_checker.return_value.call_args
        == [(), {}])


def test_cmd_run(iters, patches):
    patched = patches(
        "sys",
        "main",
        prefix="envoy.dependency.check.cmd")
    args = iters(tuple)

    with patched as (m_sys, m_main):
        m_sys.argv.__getitem__.return_value = args
        assert not run()

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
