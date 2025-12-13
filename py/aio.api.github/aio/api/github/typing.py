
from typing import TypedDict


class AssetUploadResultDict(TypedDict, total=False):
    name: str
    url: str
    error: str | None
