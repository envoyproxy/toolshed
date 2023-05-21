
from typing import Optional, TypedDict


class AssetUploadResultDict(TypedDict, total=False):
    name: str
    url: str
    error: Optional[str]
