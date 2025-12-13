
import asyncio
import logging
from queue import SimpleQueue
from unittest.mock import MagicMock, PropertyMock

import pytest

from aio.core import log


@pytest.mark.parametrize("respect", [None, True, False])
@pytest.mark.parametrize("stop_on_exit", [None, True, False])
def test_queue_logger_constructor(respect, stop_on_exit):
    kwargs = {}
    if respect is not None:
        kwargs["respect_handler_level"] = respect
    if stop_on_exit is not None:
        kwargs["stop_on_exit"] = stop_on_exit

    logger = log.QueueLogger("LOGGER", **kwargs)
    assert logger._logger == "LOGGER"
    assert (
        logger.respect_handler_level
        == (respect if respect is not None else True))
    assert (
        logger.stop_on_exit
        == (stop_on_exit if stop_on_exit is not None else True))
    assert logger.handler_class == log.QueueHandler
    assert "handler_class" not in logger.__dict__
    assert logger.queue_class == SimpleQueue
    assert "queue_class" not in logger.__dict__
    assert logger.listener_class == logging.handlers.QueueListener
    assert "listener_class" not in logger.__dict__


def test_queue_logger_handler(patches):
    logger = log.QueueLogger("LOGGER")
    patched = patches(
        ("QueueLogger.handler_class",
         dict(new_callable=PropertyMock)),
        ("QueueLogger.queue",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.log.logging")

    with patched as (m_class, m_queue):
        assert (
            logger.handler
            == m_class.return_value.return_value)

    assert (
        m_class.return_value.call_args
        == [(m_queue.return_value, ), {}])
    assert "handler" in logger.__dict__


@pytest.mark.parametrize("handler", range(0, 6))
def test_queue_logger_handlers(patches, handler):
    logger = log.QueueLogger("LOGGER")
    patched = patches(
        ("QueueLogger.handler",
         dict(new_callable=PropertyMock)),
        ("QueueLogger.logger",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.log.logging")
    handlers = range(0, 5)

    with patched as (m_handler, m_logger):
        m_handler.return_value = handler
        m_logger.return_value.handlers.__getitem__.return_value = handlers
        assert (
            logger.handlers
            == [h
                for h
                in handlers
                if h is not handler])

    assert (
        m_logger.return_value.removeHandler.call_args_list
        == [[(h, ), {}]
            for h
            in handlers
            if h is not handler])
    assert "handlers" in logger.__dict__


def test_queue_logger_queue(patches):
    logger = log.QueueLogger("LOGGER")
    patched = patches(
        ("QueueLogger.queue_class",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.log.logging")

    with patched as (m_class, ):
        assert (
            logger.queue
            == m_class.return_value.return_value)

    assert (
        m_class.return_value.call_args
        == [(), {}])
    assert "queue" in logger.__dict__


@pytest.mark.parametrize("respect", [None, True, False])
def test_queue_logger_listener(iters, patches, respect):
    kwargs = {}
    if respect is not None:
        kwargs["respect_handler_level"] = respect
    logger = log.QueueLogger("LOGGER", **kwargs)
    patched = patches(
        ("QueueLogger.handlers",
         dict(new_callable=PropertyMock)),
        ("QueueLogger.listener_class",
         dict(new_callable=PropertyMock)),
        ("QueueLogger.queue",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.log.logging")
    handlers = iters()

    with patched as (m_handlers, m_class, m_q):
        m_handlers.return_value = handlers
        assert (
            logger.listener
            == m_class.return_value.return_value)

    assert (
        m_class.return_value.call_args
        == [(m_q.return_value, *handlers),
            dict(respect_handler_level=(
                respect if respect is not None else True))])

    assert "listener" in logger.__dict__


def test_queue_logger_logger(patches):
    wrapped_logger = MagicMock()
    logger = log.QueueLogger(wrapped_logger)
    patched = patches(
        ("QueueLogger.handler",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.log.logging")

    with patched as (m_handler, ):
        assert (
            logger.logger
            == wrapped_logger)

    assert (
        wrapped_logger.addHandler.call_args
        == [(m_handler.return_value, ), {}])


@pytest.mark.parametrize("stop_on_exit", [True, False])
def test_queue_logger_start(patches, stop_on_exit):
    logger = log.QueueLogger("LOGGER", stop_on_exit=stop_on_exit)
    patched = patches(
        "atexit",
        ("QueueLogger.listener",
         dict(new_callable=PropertyMock)),
        ("QueueLogger.logger",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.log.logging")

    with patched as (m_atexit, m_listener, m_logger):
        assert (
            logger.start()
            == m_logger.return_value)

    if not stop_on_exit:
        assert not m_atexit.register.called
    else:
        assert (
            m_atexit.register.call_args
            == [(m_listener.return_value.stop, ), {}])


def test_queue_handler_constructor():
    assert isinstance(log.QueueHandler("QUEUE"), logging.handlers.QueueHandler)


@pytest.mark.parametrize("raises", [None, asyncio.CancelledError, Exception])
def test_queue_handler_emit(patches, raises):
    handler = log.QueueHandler("QUEUE")
    patched = patches(
        "QueueHandler.enqueue",
        "QueueHandler.handleError",
        prefix="aio.core.log.logging")
    record = MagicMock()

    with patched as (m_enqueue, m_error):
        if raises:
            exception = raises("BOOM")
            m_enqueue.side_effect = exception

        if raises == asyncio.CancelledError:
            with pytest.raises(asyncio.CancelledError) as e:
                handler.emit(record)
        else:
            assert not handler.emit(record)

    assert (
        m_enqueue.call_args
        == [(record, ), {}])
    if raises == asyncio.CancelledError:
        assert not m_error.called
        assert e.value == exception
        return
    if not raises:
        assert not m_error.called
        return
    assert (
        m_error.call_args
        == [(record, ), {}])
