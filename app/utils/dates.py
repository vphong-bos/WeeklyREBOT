from datetime import date, datetime, timedelta


def get_previous_week_range(today: date | None = None) -> tuple[date, date]:
    """
    Return previous Monday -> previous Sunday.
    Example: if today is 2026-05-10, returns 2026-04-27 -> 2026-05-03.
    """
    today = today or date.today()
    current_monday = today - timedelta(days=today.weekday())
    previous_monday = current_monday - timedelta(days=7)
    previous_sunday = previous_monday + timedelta(days=6)
    return previous_monday, previous_sunday


def parse_jira_datetime(value: str) -> datetime:
    """
    Jira datetime example: 2026-05-08T10:20:30.123+0700
    """
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")


def date_in_range(value: date | datetime, start: date, end: date) -> bool:
    if isinstance(value, datetime):
        value_date = value.date()
    else:
        value_date = value

    return start <= value_date <= end