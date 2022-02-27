
import asyncio
import atexit
import logging
import logging.handlers
from functools import cached_property
from queue import SimpleQueue
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
    # TODO: Remove!

    def __init__(self, logger: logging.Logger, stop: Callable) -> None:
        self._logger = logger
        self._stop = stop

    def __getattr__(self, k: str) -> Any:
        return getattr(self._logger, k)

    def stop(self) -> None:
        self._stop()


class QueueLogger:
    """Wraps a `logging.Logger` with a listening queue.

    Calling the `start` method returns the original `Logger`, with the
    listener started.

    If you set `stop_on_exit` to `False`, you must `stop` the listener
    yourself to ensure the logging queue is cleared.
    """

    def __init__(
            self,
            logger: logging.Logger,
            stop_on_exit: bool = True,
            respect_handler_level: bool = True) -> None:
        self._logger = logger
        self.respect_handler_level = respect_handler_level
        self.stop_on_exit = stop_on_exit

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
    def queue(self) -> SimpleQueue:
        return self.queue_class()

    @property
    def queue_class(self) -> Type[SimpleQueue]:
        return SimpleQueue

    @cached_property
    def listener(self) -> logging.handlers.QueueListener:
        return self.listener_class(
            self.queue,
            *self.handlers,
            respect_handler_level=self.respect_handler_level)

    @cached_property
    def logger(self) -> logging.Logger:
        """Wrapped `Logger` with `handler` added."""
        self._logger.addHandler(self.handler)
        return self._logger

    def start(self) -> logging.Logger:
        self.listener.start()
        if self.stop_on_exit:
            atexit.register(self.listener.stop)
        return self.logger
