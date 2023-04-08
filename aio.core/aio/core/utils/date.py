
import datetime

import pytz


def dt_to_utc_isoformat(dt: datetime.datetime) -> str:
    """Convert a `datetime` -> UTC `date.isoformat`"""
    date = dt.replace(tzinfo=pytz.UTC)
    return date.date().isoformat()
