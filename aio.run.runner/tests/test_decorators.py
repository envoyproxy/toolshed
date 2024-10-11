
from unittest.mock import MagicMock, PropertyMock

import pytest

from aio.run import runner


class Error1(Exception):

    def __str__(self):
        return ""

    pass


class Error2(Exception):
    pass


def _failing_runner(errors):

    class DummyFailingRunner:
        # this dummy runner calls the _runner mock
        # when its run/run_async methods are called
        # and optionally raises some type of error
        # to ensure they are caught as expected

        log = PropertyMock()
        _runner = MagicMock()

        def __init__(self, raises=None):
            self.raises = raises

        @runner.catches(errors)
        async def run(self, *args, **kwargs):
            result = self._runner(*args, **kwargs)
            if self.raises:
                raise self.raises("AN ERROR OCCURRED")
            return result

    return DummyFailingRunner


@pytest.mark.parametrize(
    "errors",
    [Error1, (Error1, Error2)])
@pytest.mark.parametrize(
    "raises",
    [None, Error1, Error2])
@pytest.mark.parametrize(
    "args",
    [(), ("ARG1", "ARG2")])
@pytest.mark.parametrize(
    "kwargs",
    [{}, dict(key1="VAL1", key2="VAL2")])
async def test_catches(errors, raises, args, kwargs):
    run = _failing_runner(errors)(raises)
    should_fail = (
        raises
        and not (
            raises == errors
            or (isinstance(errors, tuple)
                and raises in errors)))

    assert run.run.__wrapped__.__catches__ == errors

    if should_fail:
        result = 1
        with pytest.raises(raises):
            await run.run(*args, **kwargs)
    else:
        result = (
            await run.run(*args, **kwargs))

    assert (
        run._runner.call_args
        == [args, kwargs])

    if not should_fail and raises:
        assert result == 1
        error = run.log.error.call_args[0][0]
        _error = raises("AN ERROR OCCURRED")
        assert (
            error
            == (str(_error) or repr(_error)))
        assert (
            run.log.error.call_args
            == [(error,), {}])
    else:
        assert not run.log.error.called

    if raises:
        assert result == 1
    else:
        assert result == run._runner.return_value


def _cleanup_runner(raises):

    class DummyCleanupRunner:
        # this dummy runner calls the _runner mock
        # when its run/async_fun methods are called
        # and optionally raises some type of error
        # to ensure they are caught as expected

        log = PropertyMock()
        _runner = MagicMock()

        @runner.cleansup
        async def run(self, *args, **kwargs):
            result = self._runner(*args, **kwargs)
            if raises:
                raise Exception("AN ERROR OCCURRED")
            return result

    return DummyCleanupRunner()


@pytest.mark.parametrize("raises", [True, False])
async def test_cleansup(iters, raises):
    run = _cleanup_runner(raises)
    args = iters(count=3)
    kwargs = iters(dict, count=3)

    assert run.run.__wrapped__.__cleansup__ is True

    run.cleanup = MagicMock()
    if raises:
        with pytest.raises(Exception):
            await run.run(*args, **kwargs)
    else:
        assert (
            await run.run(*args, **kwargs)
            == run._runner.return_value)

    assert (
        run._runner.call_args
        == [tuple(args), kwargs])
    assert (
        run.cleanup.call_args
        == [(), {}])
