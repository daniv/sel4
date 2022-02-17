import re
from datetime import datetime, date, timezone, timedelta
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from pydantic import validate_arguments
from calendar import day_abbr, day_name, month_abbr, month_name
from time import localtime, strftime

from .functional import lazy
from .regex_helper import _lazy_re_compile


@validate_arguments
def is_aware(value: datetime):
    """
    Determine if a given datetime.datetime is aware.
    """
    return value.utcoffset() is not None


@validate_arguments
def is_naive(value: datetime):
    """
    Determine if a given datetime.datetime is naive.
    The concept is defined in Python's docs:
    https://docs.python.org/library/datetime.html#datetime.tzinfo
    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is None


_VALID_SIGNS = frozenset(['-', '+'])


def get_timedelta(delta: str) -> relativedelta:
    """
    Return timedelta from string.
    years=0, months=0, days=0, leapdays=0, weeks=0,
    hours=0, minutes=0, seconds=0, microseconds=0,
    :param str delta:
    >>> get_timedelta("")
    relativedelta(0)
    >>> get_timedelta("+1H")
    relativedelta(hours=1)
    >>> get_timedelta("+10H")
    relativedelta(hours=10)
    >>> get_timedelta("-10H")
    relativedelta(hours=-10)
    >>> get_timedelta("+1M")
    relativedelta(minutes=1)
    >>> get_timedelta("-1y")
    relativedelta(years-1)
    >>> get_timedelta("+10d+2H")
    relativedelta(days=10, hours=2)
    >>> get_timedelta("-10d2H")
    relativedelta(days=-10, hours=2)
    >>> get_timedelta("-21y+2m-1d+24H-23S")
    relativedelta(years=-21, months=2, days=-1, hours=24, second=-23)
    """
    if not delta:
        return relativedelta()

    if not isinstance(delta, str):
        raise TypeError("Expression is not a string")
    units = {
        "f": "microseconds",
        "S": "seconds",
        "M": "minutes",
        "H": "hours",
        "d": "days",
        "w": "weeks",
        "l": "leapdays",
        "m": "months",
        "y": "years",
    }
    relativedelta_kwargs = {}
    for part in filter(lambda p: p, re.split(r"([+-]\d+\w)", delta)):
        sign = part[0]
        assert sign in _VALID_SIGNS, f"Valid signs are '+/-' not \"{sign}\""
        part = part[1:]
        amount, unit = re.findall(r"(\d+)([ymlwdhHMSf])", part)[0]
        amount = int(amount)
        if sign == "-":
            amount = -amount
        key = units[unit]
        if key in relativedelta_kwargs:
            raise ValueError(f"The time period was already set --> {sign}{amount}{unit}")
        relativedelta_kwargs[units[unit]] = amount
    return relativedelta(**relativedelta_kwargs)


def get_relative_date(date_value: str, date_format: str = "%Y-%m-%d"):
    delta = get_timedelta(date_value)
    dt = datetime.now() + delta
    return dt.strftime(date_format)


tokens = _lazy_re_compile(r"H{1,2}|h{1,2}|m{1,2}|s{1,2}|S{1,6}"
                          r"|YYYY|YY|M{1,4}|D{1,4}|Z{1,2}|zz|A|X|x|E|Q|dddd|ddd|d")

pattern = _lazy_re_compile(r"(?:{0})|\[(?:{0}|!UTC)\]".format(tokens))


class DateTime(datetime):
    def __format__(self, spec):
        if spec.endswith("!UTC"):
            dt = self.astimezone(timezone.utc)
            spec = spec[:-4]
        else:
            dt = self

        if not spec:
            spec = "%Y-%m-%dT%H:%M:%S.%f%z"

        if "%" in spec:
            return datetime.__format__(dt, spec)

        year, month, day, hour, minute, second, weekday, yearday, _ = dt.timetuple()
        microsecond = dt.microsecond
        timestamp = dt.timestamp()
        tzinfo = dt.tzinfo or timezone(timedelta(seconds=0))
        offset = tzinfo.utcoffset(dt).total_seconds()
        sign = ("-", "+")[offset >= 0]
        h, m = divmod(abs(offset // 60), 60)

        rep = {
            "YYYY": "%04d" % year,
            "YY": "%02d" % (year % 100),
            "Q": "%d" % ((month - 1) // 3 + 1),
            "MMMM": month_name[month],
            "MMM": month_abbr[month],
            "MM": "%02d" % month,
            "M": "%d" % month,
            "DDDD": "%03d" % yearday,
            "DDD": "%d" % yearday,
            "DD": "%02d" % day,
            "D": "%d" % day,
            "dddd": day_name[weekday],
            "ddd": day_abbr[weekday],
            "d": "%d" % weekday,
            "E": "%d" % (weekday + 1),
            "HH": "%02d" % hour,
            "H": "%d" % hour,
            "hh": "%02d" % ((hour - 1) % 12 + 1),
            "h": "%d" % ((hour - 1) % 12 + 1),
            "mm": "%02d" % minute,
            "m": "%d" % minute,
            "ss": "%02d" % second,
            "s": "%d" % second,
            "S": "%d" % (microsecond // 100000),
            "SS": "%02d" % (microsecond // 10000),
            "SSS": "%03d" % (microsecond // 1000),
            "SSSS": "%04d" % (microsecond // 100),
            "SSSSS": "%05d" % (microsecond // 10),
            "SSSSSS": "%06d" % microsecond,
            "A": ("AM", "PM")[hour // 12],
            "Z": "%s%02d:%02d" % (sign, h, m),
            "ZZ": "%s%02d%02d" % (sign, h, m),
            "zz": tzinfo.tzname(dt) or "",
            "X": "%d" % timestamp,
            "x": "%d" % (int(timestamp) * 1000000 + microsecond),
        }

        def get(matcher):
            try:
                return rep[matcher.group(0)]
            except KeyError:
                return matcher.group(0)[1:-1]

        return pattern.sub(get, spec)
