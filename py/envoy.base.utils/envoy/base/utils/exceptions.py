
from typing import Any


class TypeCastingError(TypeError):

    def __init__(self, *args,  value: Any = None) -> None:
        self.value = value
        super().__init__(*args)


class ChangelogError(Exception):
    pass


class ChangelogParseError(Exception):
    pass


class ReleaseError(Exception):
    pass


class DevError(Exception):
    pass


class CommitError(Exception):
    pass


class PublishError(Exception):
    pass


class ChecksumError(Exception):
    pass


class SignatureError(Exception):
    pass
