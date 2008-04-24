#!/usr/bin/env python
#
#   model/dates.py
#   TurboHvZ
#
#   Copyright (C) 2008 Ross Light
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from datetime import datetime, timedelta

import pkg_resources
pkg_resources.require("pytz")

from turbogears import config
import pytz

__author__ = 'Ross Light'
__date__ = 'April 18, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['now',
           'as_local',
           'as_utc',
           'to_local',
           'to_utc',
           'make_aware',
           'date_prop',
           'calc_timedelta',]

def _get_local_timezone():
    return pytz.timezone(config.get('hvz.timezone', 'UTC'))

def now():
    """
    Creates a timezone-aware representation of now.
    
    :Returns: The UTC now
    :ReturnType: datetime.datetime
    """
    return as_utc(datetime.utcnow())

def as_local(date, tz=None):
    """
    Interprets (but does not convert) the date as being in the local timezone.
    
    :Parameters:
        date : datetime.datetime
            The date to interpret
        tz : datetime.tzinfo
            The timezone to interpret as.  If not given, then the timezone is
            read from the ``hvz.timezone`` configuration value.
    :Returns: The timezone-aware date
    :ReturnType: datetime.datetime
    """
    if tz is None:
        tz = _get_local_timezone()
    return tz.localize(date)

def as_utc(date):
    """
    Interprets (but does not convert) the date as UTC.
    
    :Parameters:
        date : datetime.datetime
            The date to interpret
    :Returns: The timezone-aware date
    :ReturnType: datetime.datetime
    """
    return date.replace(tzinfo=pytz.utc)

def to_local(date, tz=None):
    """
    Converts the date to the local timezone.
    
    :Parameters:
        date : datetime.datetime
            The date to convert.  If this date is naive, then it will be
            interpreted as UTC.
        tz : datetime.tzinfo
            The timezone to convert to.  If not given, then the timezone is
            read from the ``hvz.timezone`` configuration value.
    :Returns: The timezone-aware date
    :ReturnType: datetime.datetime
    """
    if tz is None:
        tz = _get_local_timezone()
    date = make_aware(date)
    return date.astimezone(tz)

def to_utc(date):
    """
    Converts the date to UTC.
    
    :Parameters:
        date : datetime.datetime
            The date to convert.  If this date is naive, then it will be
            interpreted as UTC.
    :Returns: The timezone-aware date
    :ReturnType: datetime.datetime
    """
    date = make_aware(date)
    return date.astimezone(pytz.utc)

def make_aware(date, local=False):
    """
    Ensures that a date is timezone-aware.
    
    :Parameters:
        date : datetime.datetime
            The date to interpret
    :Keywords:
        local : bool
            Whether this should default to a local time.
    :Returns: The timezone-aware date
    :ReturnType: datetime.datetime
    """
    if date.tzinfo is None:
        if local:
            date = as_local(date)
        else:
            date = as_utc(date)
    return date

def _get_date_prop(name):
    """
    Retrieves a date from the database, interpreting it as UTC.
    
    :Parameters:
        name : str
            Attribute name for the column
    :Returns: A function that can be used as a property getter
    :ReturnType: function
    """
    def get_prop(self):
        value = getattr(self, name)
        if value is None:
            return None
        else:
            return as_utc(value)
    return get_prop

def _set_date_prop(name, default_tz=pytz.utc):
    """
    Updates a date in the database, converting it to UTC.
    
    :Parameters:
        name : str
            Attribute name for the column
    :Keywords:
        default_tz : datetime.tzinfo
            Default timezone to intepret naive 
    :Returns: A function that can be used as a property setter
    :ReturnType: function
    """
    from turbogears.database import session
    def set_prop(self, value):
        if value is not None:
            if value.tzinfo is None:
                value = as_local(value, default_tz)
            value = to_utc(value)
            # WEIRD BUG: SQLAlchemy gets cranky because it tries to compare the
            #            accessor value to the non-accessor value in an attempt
            #            to preserve history (thus comparing naive to aware).
            #            In order to get around this, we set the dates to None,
            #            flush it, then set it correctly.  Don't ask me why I
            #            need this.
            setattr(self, name, None)
            session.flush()
        setattr(self, name, value)
    return set_prop

def date_prop(name, default_tz=pytz.utc):
    return property(_get_date_prop(name),
                    _set_date_prop(name, default_tz=default_tz))

def calc_timedelta(datetime1, datetime2, tz=None,
                    ignore_dates=None, ignore_weekdays=None):
    """
    Calculates the delta between two datetimes.
    
    Along with subtracting the two dates, this removes time on specific dates
    and weekdays.
    
    :Parameters:
        datetime1
            The first date and time
        datetime2
            The second date and time
    :Keywords:
        tz : datetime.tzinfo
            The timezone to calculate dates in, defaulting to the config value
            of ``hvz.timezone``.  If you get the wrong timezone, your results
            will possibly be **very incorrect**.  This is because the algorithm
            should be looking at dates in the players' timezone, which is
            rarely UTC.
        ignore_dates : list of datetime.date
            Days that are removed from the difference
        ignore_weekdays : list of int
            Weekdays that are removed from the difference (given as ISO weekday
            numbers)
    :Returns: The difference between the two dates
    :ReturnType: datetime.timedelta
    """
    assert datetime1 <= datetime2
    # Get arguments
    if tz is None:
        tz = _get_local_timezone()
    if ignore_dates is None:
        ignore_dates = []
    if ignore_weekdays is None:
        ignore_weekdays = []
    datetime1, datetime2 = to_local(datetime1, tz), to_local(datetime2, tz)
    # Calculate basic difference
    difference = datetime2 - datetime1
    # Find date range
    date1, date2 = (datetime1.date(), datetime2.date())
    # Loop through all dates in-between date1 and date2
    accum_date = date1
    while accum_date <= date2:
        if accum_date in ignore_dates or \
           accum_date.isoweekday() in ignore_weekdays:
            # This date is an ignore day, so let's decide what to do:
            if accum_date == date1:
                # This is the first date, so get the amount of time remaining
                # in the day on datetime1 and subtract it from the difference
                this_day = datetime1.replace(hour=0, minute=0, second=0,
                                             microsecond=0)
                next_day = this_day + timedelta(1)
                difference -= next_day - datetime1
            elif accum_date == date2:
                # This is the last date, so get the amount of time elapsed
                # in the day on datetime2 and subtract it from the difference
                this_day = datetime2.replace(hour=0, minute=0, second=0,
                                             microsecond=0)
                difference -= datetime2 - this_day
            else:
                # Woo-hoo!  This is a full ignore day, so let's do simple math.
                difference -= timedelta(1)
        # Okay, let's take up the next day
        accum_date += timedelta(1)
    # Ensure that difference >= 0
    # This prevents the weird case where 
    difference = max(timedelta(), difference)
    # Return result
    return difference
