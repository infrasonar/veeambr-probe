import datetime


def str_to_timestamp(s: str | None) -> int | None:
    return None if s is None else int(
        datetime.datetime.fromisoformat(s).timestamp())
