import datetime


def str_to_timestamp(s: str | None) -> int | None:
    return None if s is None else int(
        datetime.datetime.fromisoformat(s).timestamp())


def iso_fmt(d: datetime.datetime) -> str:
    return d.isoformat(timespec='seconds').replace('+00:00', 'Z')
