"""The local date of a telemetry timestamp (phase rule D14): one date per pump
per day in Europe/Helsinki, with the 23-hour and 25-hour clock-change days of
2023 to 2025 on the right date."""

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from fjordvik_data import config as c
from fjordvik_data.localdate import local_date
from fjordvik_data.service import all_days

HELSINKI = ZoneInfo("Europe/Helsinki")
HOUR = timedelta(hours=1)
# The clocks go forward on the last Sunday of March and back on the last Sunday of October.
CLOCK_CHANGE_DAYS = {
    date(2023, 3, 26): 23, date(2023, 10, 29): 25,
    date(2024, 3, 31): 23, date(2024, 10, 27): 25,
    date(2025, 3, 30): 23, date(2025, 10, 26): 25,
}


def midnight(day: date) -> datetime:
    """The start of a local day in Helsinki, as a UTC timestamp."""
    return datetime(day.year, day.month, day.day, tzinfo=HELSINKI).astimezone(timezone.utc)


def test_the_time_zone_is_a_named_setting():
    assert c.TELEMETRY_TIME_ZONE == "Europe/Helsinki"


def test_clock_change_days_are_23_and_25_hours_long():
    for day, hours in CLOCK_CHANGE_DAYS.items():
        assert day.weekday() == 6, day
        assert midnight(day + timedelta(days=1)) - midnight(day) == hours * HOUR, day


@pytest.mark.parametrize("day, hours", CLOCK_CHANGE_DAYS.items())
def test_every_hour_of_a_clock_change_day_lands_on_its_date(day, hours):
    start = midnight(day)
    for n in range(hours):
        assert local_date(start + n * HOUR) == day, n
    assert local_date(start + hours * HOUR - timedelta(seconds=1)) == day
    assert local_date(start - timedelta(seconds=1)) == day - timedelta(days=1)
    assert local_date(start + hours * HOUR) == day + timedelta(days=1)


def test_the_same_instant_gives_the_same_date_from_any_time_zone():
    late = datetime(2025, 7, 14, 21, 30, tzinfo=timezone.utc)      # 00:30 on 15 July in Helsinki
    assert local_date(late) == date(2025, 7, 15)
    assert local_date(late.astimezone(ZoneInfo("Europe/Stockholm"))) == date(2025, 7, 15)
    assert local_date(late.astimezone(timezone(timedelta(hours=-5)))) == date(2025, 7, 15)
    winter = datetime(2025, 1, 14, 21, 30, tzinfo=timezone.utc)    # 23:30 on 14 January
    assert local_date(winter) == date(2025, 1, 14)


def test_hourly_timestamps_give_one_date_for_every_day_of_the_period():
    """An hourly feed over the whole period lands on exactly the days the telemetry
    has, 24 hours on each except the six clock-change days."""
    start, end = midnight(c.SERVICE_FIRST_DAY), midnight(c.SERVICE_LAST_DAY + timedelta(days=1))
    hours = Counter()
    stamp = start
    while stamp < end:
        hours[local_date(stamp)] += 1
        stamp += HOUR
    assert sorted(hours) == all_days()
    for day, count in hours.items():
        assert count == CLOCK_CHANGE_DAYS.get(day, 24), day


def test_a_timestamp_without_a_time_zone_is_refused():
    with pytest.raises(ValueError):
        local_date(datetime(2025, 3, 30, 3, 30))
