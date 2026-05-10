
# Thrown on errors related to release date or version.
class ReleaseDateVersionError(Exception):
    pass


# Errors that happen during issue creation.
class DependencyUpdateError(Exception):
    pass


class BadGithubURL(Exception):
    pass


class NotGithubDependency(Exception):
    pass


class NoReleaseAssetError(Exception):
    pass
