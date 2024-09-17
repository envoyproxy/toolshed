

class RunError(Exception):
    pass


class FixError(Exception):
    pass


class ConfigurationError(Exception):
    pass


class ExtensionsConfigurationError(ConfigurationError):
    pass
