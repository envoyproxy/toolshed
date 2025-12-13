
from datetime import datetime


# these only deal with utc but are good enough for working with the
# github api

def dt_from_js_isoformat(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def dt_to_js_isoformat(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")
