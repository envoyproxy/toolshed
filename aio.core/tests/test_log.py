
import logging
from queue import Queue
from unittest.mock import MagicMock, PropertyMock

import pytest

from aio.core import log


def test_stoppable_logger_constructor():
    logger = log.StoppableLogger("LOGGER", "STOP")
    assert logger._logger == "LOGGER"
    assert logger._stop == "STOP"


def test_stoppable_logger_dunder_getattr(patches):
    wrapped_logger = MagicMock()
    logger = log.StoppableLogger(wrapped_logger, "STOP")
    patched = patches(
        "getattr",
        prefix="aio.core.log.logging")

    with patched as (m_getattr, ):
        assert (
            logger.SOMEATTR
            == m_getattr.return_value)

    assert (
        m_getattr.call_args
        == [(wrapped_logger, "SOMEATTR"), {}])


def test_stoppable_logger_stop():
    stop = MagicMock()
    logger = log.StoppableLogger("LOGGER", stop)
    assert not logger.stop()
    assert (
        stop.call_args
        == [(), {}])


@pytest.mark.parametrize("respect", [None, True, False])
def test_queue_logger_constructor(respect):
    kwargs = {}
    if respect is not None:
        kwargs["respect_handler"] = respect

    logger = log.QueueLogger("LOGGER", **kwargs)
    assert logger._logger == "LOGGER"
    assert logger.respect_handler == (respect if respect is not None else True)
    assert logger.handler_class == log.QueueHandler
    assert "handler_class" not in logger.__dict__
    assert logger.queue_class == Queue
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
        == [(-1, ), {}])
    assert "queue" in logger.__dict__


@pytest.mark.parametrize("respect", [None, True, False])
def test_queue_logger_listener(patches, respect):
    kwargs = {}
    if respect is not None:
        kwargs["respect_handler"] = respect
    logger = log.QueueLogger("LOGGER", **kwargs)
    patched = patches(
        ("QueueLogger.handlers",
         dict(new_callable=PropertyMock)),
        ("QueueLogger.listener_class",
         dict(new_callable=PropertyMock)),
        ("QueueLogger.queue",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.log.logging")
    handlers = [f"H{i}" for i in range(0, 5)]

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


def test_queue_logger_start(patches):
    logger = log.QueueLogger("LOGGER")
    patched = patches(
        "StoppableLogger",
        ("QueueLogger.listener",
         dict(new_callable=PropertyMock)),
        ("QueueLogger.logger",
         dict(new_callable=PropertyMock)),
        prefix="aio.core.log.logging")

    with patched as (m_stoppable, m_listener, m_logger):
        assert (
            logger.start()
            == m_stoppable.return_value)

    assert (
        m_stoppable.call_args
        == [(m_logger.return_value, m_listener.return_value.stop), {}])
