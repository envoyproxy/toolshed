
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


class CPEError(Exception):
    pass


class CVEError(Exception):
    pass


class CVECheckError(Exception):
    pass
