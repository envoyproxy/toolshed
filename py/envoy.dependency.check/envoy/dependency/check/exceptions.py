
# Thrown on errors related to release date or version.
class ReleaseDateVersionError(Exception):
    pass


# Errors that happen during issue creation.
class DependencyUpdateError(Exception):
    pass


class BadGithubURL(Exception):
    pass


class GithubTokenError(Exception):
    pass


class DependencyMetadataError(Exception):
    """Raised when the loaded dependency metadata fails validation."""


class NotGithubDependency(Exception):
    pass


class NoReleaseAssetError(Exception):
    pass
