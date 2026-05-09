
import datetime


def dt_to_utc_isoformat(dt: datetime.datetime) -> str:
    """Convert a `datetime` -> UTC `date.isoformat`"""
    date = dt.replace(tzinfo=datetime.UTC)
    return date.date().isoformat()
