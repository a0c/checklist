from datetime import datetime
import pytz

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


def prs(dt):
    return dt and datetime.strptime(dt, DEFAULT_SERVER_DATETIME_FORMAT)


def fmt(dt):
    return datetime.strftime(dt, DEFAULT_SERVER_DATETIME_FORMAT)


def timezone_sydney():
    return pytz.timezone('Australia/Sydney')


def diff(start, end):
    """ diff with correction for daylight saving time """
    tz = timezone_sydney()
    correction = tz.localize(end).utcoffset() - tz.localize(start).utcoffset()
    return end - start + correction
