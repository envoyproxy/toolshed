
class ConcurrentError(Exception):
    """Raised when given inputs/awaitables are incorrect."""
    pass


class ConcurrentIteratorError(ConcurrentError):
    """Raised when iteration of provided awaitables fails."""
    pass


class ConcurrentExecutionError(ConcurrentError):
    """Raised when execution of a provided awaitable fails."""
    pass
