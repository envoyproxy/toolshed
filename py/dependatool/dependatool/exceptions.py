

class PipConfigurationError(Exception):
    pass


class DependatoolConfigurationError(PipConfigurationError):
    """Raised when the dependabot configuration cannot be parsed."""
