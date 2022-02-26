
import asyncio
import logging
import logging.handlers
from functools import cached_property
from queue import Queue
from typing import Any, Callable, List, Type


class QueueHandler(logging.handlers.QueueHandler):

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.enqueue(record)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.handleError(record)


class StoppableLogger:
    """Wraps a `logging.Logger` with a stop method."""

    def __init__(self, logger: logging.Logger, stop: Callable) -> None:
        self._logger = logger
        self._stop = stop

    def __getattr__(self, k: str) -> Any:
        return getattr(self._logger, k)

    def stop(self) -> None:
        self._stop()


class QueueLogger:
    """Wraps a `logging.Logger` with a listening queue.

    Calling the `start` method returns a `StoppableLogger`, which wraps
    the original `Logger` and expects to be stopped.
    """

    def __init__(
            self,
            logger: logging.Logger,
            respect_handler: bool = True) -> None:
        self._logger = logger
        self.respect_handler = respect_handler

    @cached_property
    def handler(self) -> QueueHandler:
        return self.handler_class(self.queue)

    @property
    def handler_class(self) -> Type[QueueHandler]:
        return QueueHandler

    @cached_property
    def handlers(self) -> List[logging.Handler]:
        """Logging handlers removed from the original logger."""
        handlers: List[logging.Handler] = []
        for h in self.logger.handlers[:]:
            if h is not self.handler:
                self.logger.removeHandler(h)
                handlers.append(h)
        return handlers

    @property
    def listener_class(self) -> Type[logging.handlers.QueueListener]:
        return logging.handlers.QueueListener

    @cached_property
    def queue(self) -> Queue:
        return self.queue_class(-1)

    @property
    def queue_class(self) -> Type[Queue]:
        return Queue

    @cached_property
    def listener(self) -> logging.handlers.QueueListener:
        return self.listener_class(
            self.queue,
            *self.handlers,
            respect_handler_level=self.respect_handler)

    @cached_property
    def logger(self) -> logging.Logger:
        """Wrapped `Logger` with `handler` added."""
        self._logger.addHandler(self.handler)
        return self._logger

    def start(self) -> StoppableLogger:
        self.listener.start()
        return StoppableLogger(self.logger, self.listener.stop)
