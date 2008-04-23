#!/usr/bin/env python
#
#   util.py
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

"""Utility functions provided to templates and the rest of the project"""

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['abslink',
           'absurl',
           'change_params',
           'change_password_link',
           'display',
           'display_date',
           'display_weekday',
           'game_link',
           'insecurelink',
           'insecureurl',
           'login_link',
           'plain2html',
           'pluralize',
           'register_link',
           'securelink',
           'secureurl',
           'str2bool',
           'to_uuid',
           'user_link',
           'add_template_variables',]

from cgi import escape
import datetime
import re
from urllib import quote, quote_plus, unquote, urlencode
from urlparse import urlparse, urlunparse

import cherrypy
import genshi
import turbogears
from turbogears.util import DictObj
from turbojson.jsonify import encode as jsencode

_nl_pattern = re.compile(r'((?:\r\n)|[\r\n])')

def _make_app_link(base, params):
    redirect = params.pop('redirect', False)
    # The redirect parameter allows you to use the return value in a
    # redirect function call
    if redirect:
        query = urlencode(params)
        if query:
            return base + '?' + urlencode(params)
        else:
            return base
    else:
        return turbogears.url(base, params)

def abslink(path):
    """Create an absolute URL from a pre-constructed path."""
    return cherrypy.request.base + path

def absurl(*args, **kw):
    """Create an absolute URL with the same signature as tg.url."""
    return abslink(turbogears.url(*args, **kw))

def change_params(url=None, d=None, **kw):
    if url is None:
        newValues = cherrypy.request.params.copy()
    else:
        parse_result = list(urlparse(url))
        query = parse_result[4]
        newValues = cherrypy.lib.httptools.parseQueryString(query)
    if d is not None:
        newValues.update(d)
    newValues.update(kw)
    if url is None:
        if newValues:
            return '?' + urlencode(newValues)
        else:
            return ''
    else:
        parse_result[4] = urlencode(newValues)
        return urlunparse(parse_result)

def change_password_link():
    """Returns the proper URL to the change password page."""
    if turbogears.config.get('hvz.secure_login', False):
        # Secure login
        return secureurl('/user/changepassword')
    else:
        # Insecure login
        return turbogears.url('/user/changepassword')

def display(widget, *args, **kw):
    """Display a widget in Genshi"""
    data = widget.render(format='html', *args, **kw)
    return genshi.HTML(turbogears.util.to_unicode(data))

def display_date(date):
    """Format dates uniformly"""
    if isinstance(date, datetime.datetime):
        from model.dates import to_local
        return unicode(to_local(date).replace(microsecond=0).isoformat())
    elif isinstance(date, datetime.date):
        return unicode(date.isoformat())
    elif isinstance(date, datetime.time):
        return unicode(date.replace(microsecond=0, tzinfo=None).isoformat())
    elif isinstance(date, datetime.timedelta):
        names = [(_("day"), _("days")),
                 (_("hour"), _("hours")),
                 (_("minute"), _("minutes")),
                 (_("second"), _("seconds")),]
        d, s = date.days, date.seconds
        h, s = s // (60 * 60), s % (60 * 60)
        m, s = s // 60, s % 60
        comps = ["%s %s" % (value, pluralize(value, singular, plural))
                 for value, (singular, plural) in zip([d, h, m, s], names)
                 if value]
        return " ".join(comps)
    else:
        raise TypeError("display_date received a non-datetime %r" % date)

def display_weekday(day):
    """Turn an ISO weekday to a name"""
    lookup = {1: _("Monday"),
              2: _("Tuesday"),
              3: _("Wednesday"),
              4: _("Thursday"),
              5: _("Friday"),
              6: _("Saturday"),
              7: _("Sunday"),}
    return lookup[day]

def game_link(game, action='view', **params):
    if isinstance(game, (int, long)):
        pass
    else:
        game = game.game_id
    base = '/game/%s/%s' % (quote(action, ''), quote(str(game), ''))
    return _make_app_link(base, params)

def insecurelink(path):
    """Create an insecure URL from a pre-constructed path."""
    baseURL = cherrypy.request.base
    # Replace URL's protocol with http
    baseURL = 'http' + baseURL[baseURL.index(':'):]
    return baseURL + path

def insecureurl(*args, **kw):
    """Create an insecure URL with the same signature as tg.url."""
    return insecurelink(turbogears.url(*args, **kw))

def login_link():
    """Returns the proper URL to the login page."""
    if turbogears.config.get('hvz.secure_login', False):
        # Secure login
        return secureurl('/login')
    else:
        # Insecure login
        return turbogears.url('/login')

def plain2html(text):
    """
    Converts plain text into basic HTML markup.

    This takes the plain text, escapes any special characters, then
    converts newlines into ``<br/>`` sequences, all enclosed in a
    ``<p>`` element.

    :Parameters:
        text : str
            The text to convert
    :Returns: The HTML markup
    :ReturnType: str
    """
    text = escape(text)
    text = _nl_pattern.sub(r'<br />\1', text)
    text = '<p>' + text + '</p>'
    return text

def pluralize(value, singular, plural):
    """
    Pluralize a word correctly.
    
    :Parameters:
        value
            A numerical value to test for plurality.
        singular : unicode
            The singular form of the term
        plural : unicode
            The plural form of the term
    :Returns: The singular or plural, depending on ``value == 1``
    :ReturnType: unicode
    """
    if value == 1:
        return singular
    else:
        return plural

def register_link():
    """Returns the proper URL to the register page."""
    if turbogears.config.get('hvz.secure_login', False):
        # Secure login
        return secureurl('/user/register')
    else:
        # Insecure login
        return turbogears.url('/user/register')

def securelink(path):
    """Create a secure URL from a pre-constructed path."""
    baseURL = cherrypy.request.base
    # Replace URL's protocol with https
    baseURL = 'https' + baseURL[baseURL.index(':'):]
    return baseURL + path

def secureurl(*args, **kw):
    """Create a secure URL with the same signature as tg.url."""
    return securelink(turbogears.url(*args, **kw))

def str2bool(s, *args):
    if len(args) > 1:
        raise TypeError("str2bool takes 2 arguments at the most")
    s = s.strip().lower()
    if s == 'true':
        return True
    elif s == 'false':
        return False
    else:
        try:
            return bool(int(s, 10))
        except ValueError:
            if len(args) >= 1:
                return args[0]
            else:
                raise ValueError("Invalid bool: %r" % s)

def to_uuid(value):
    from uuid import UUID
    if isinstance(value, UUID) or value is None:
        return value
    elif isinstance(value, basestring):
        if len(value) == 16:
            return UUID(bytes=value)
        else:
            return UUID(value)
    elif isinstance(value, (int, long)):
        return UUID(int=value)
    else:
        raise TypeError("Unrecognized type for UUID, got '%s'" %
                        (type(value).__name__))

def user_link(user, action='view', **params):
    from hvz.model.identity import User
    if isinstance(user, User):
        base = '/user/%s/%s' % (quote(action, ''), quote(user.user_name, ''))
        return _make_app_link(base, params)
    elif isinstance(user, (int, long)):
        pass
    elif hasattr(user, 'player_id'):
        user = user.player_id
    else:
        user = user.user_id
    base = '/user/%s/%s' % (quote(action, ''), quote(str(user), ''))
    return _make_app_link(base, params)

def add_template_variables(vars):
    hvzNamespace = DictObj(change_password_link=change_password_link,
                           game_link=game_link,
                           login_link=login_link,
                           register_link=register_link,
                           user_link=user_link,)
    lookup = dict(hvz=hvzNamespace,
                  abslink=abslink,
                  absurl=absurl,
                  change_params=change_params,
                  display=display,
                  display_date=display_date,
                  display_weekday=display_weekday,
                  insecurelink=insecurelink,
                  insecureurl=insecureurl,
                  jsencode=jsencode,
                  plain2html=plain2html,
                  pluralize=pluralize,
                  securelink=securelink,
                  secureurl=secureurl,)
    return vars.update(lookup)

turbogears.view.variable_providers.append(add_template_variables)
