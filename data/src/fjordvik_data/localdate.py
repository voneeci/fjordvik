"""The local date of a telemetry timestamp.

Daily telemetry has one row per pump per local date in Europe/Helsinki. A
timestamp must carry its time zone, so the day it belongs to is never a guess:
the 23-hour day in spring and the 25-hour day in autumn each land on one date.

Windows has no system time zone data: install the tzdata library there (it is in
this part's dev libraries).
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from fjordvik_data import config as c


def local_date(timestamp: datetime) -> date:
    """The date in Europe/Helsinki at a timezone-aware timestamp."""
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("a telemetry timestamp must be timezone-aware")
    return timestamp.astimezone(ZoneInfo(c.TELEMETRY_TIME_ZONE)).date()
