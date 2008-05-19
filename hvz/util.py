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

from __future__ import division
from cgi import escape
import datetime
import re
from urllib import quote, quote_plus, unquote, urlencode
from urlparse import urlparse, urlunparse
from uuid import UUID

import cherrypy
import genshi
import turbogears
from turbogears.util import DictObj
from turbojson.jsonify import encode as jsencode

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['abslink',
           'absurl',
           'alliance_link',
           'bbcode',
           'change_params',
           'change_password_link',
           'display',
           'display_date',
           'display_file_size',
           'display_weekday',
           'game_link',
           'image_link',
           'insecurelink',
           'insecureurl',
           'login_link',
           'plain2html',
           'pluralize',
           'register_link',
           'securelink',
           'secureurl',
           'to_uuid',
           'user_link',
           'add_template_variables',]

_nl_pattern = re.compile(r'((?:\r\n)|[\r\n])')

def _make_app_link(base, params):
    """
    Creates an application link.
    
    If the key ``redirect`` is present in params, then the URI is returned as a
    relative-to-application link that can be passed into tg.url.
    
    :Parameters:
        base : str
            The format for the URI
        params : dict
            Additional parameters to append to the query
    :Returns: An application link
    :ReturnType: dict
    """
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
    """
    Create an absolute URL from a pre-constructed path.
    
    :Parameters:
        path : str
            The path to convert
    :Returns: The canonical URI
    :ReturnType: str
    """
    return cherrypy.request.base + path

def absurl(*args, **kw):
    """
    Create an absolute URL with the same signature as ``turbogears.url``.
    
    :Returns: The canonical URI
    :ReturnType: str
    """
    return abslink(turbogears.url(*args, **kw))

def alliance_link(alliance, action='view', **params):
    """
    Create a link to an alliance.
    
    Any additional keyword parameters are sent as GET parameters.
    
    :Parameters:
        alliance : `hvz.model.social.Alliance`
            The alliance to link to
        action : str
            The action to use
    :Returns: The link to the object
    :ReturnType: str
    """
    base = '/user/alliance/%s/%s' % (quote(action, ''),
                                     quote(str(alliance.alliance_id), ''))
    return _make_app_link(base, params)

def bbcode(code):
    """
    Renders BBCode as XHTML.
    
    :Parameters:
        code : unicode
            BBCode to render
    :Returns: Rendered XHTML
    :ReturnType: unicode
    """
    from hvz.markup import render_bbcode
    from hvz.controllers.base import log
    code = unicode(code)
    code = _nl_pattern.sub('\n', code)
    log.debug("Rendering with %r", code)
    return render_bbcode(unicode(code))

def change_params(url=None, d=None, **kw):
    """
    Change the parameters of a URL.
    
    :Parameters:
        url : str
            The URL to change.  If no URL is given, the current one is used.
        d : dict
            Parameters to change.
    :Returns: The modified URL
    :ReturnType: str
    """
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
    """
    Determines the proper URL to the change password page.
    
    :Returns: The URI for the page
    :ReturnType: str
    """
    if turbogears.config.get('hvz.secure_login', False):
        # Secure login
        return secureurl('/user/changepassword')
    else:
        # Insecure login
        return turbogears.url('/user/changepassword')

def display(widget, *args, **kw):
    """
    Display a widget in Genshi.
    
    Since TurboGears uses Kid, any ``widget.display(...)`` calls don't do "the
    right thing" for Genshi.  So instead, we call ``tg.display(widget, ...)``
    and that does "the right thing".
    
    :Parameters:
        widget : ``turbogears.widgets.Widget``
            A widget to render
    :Returns: Immediately usable Genshi markup
    :ReturnType: ``genshi.core.Stream``
    """
    data = widget.render(format='html', *args, **kw)
    return genshi.HTML(turbogears.util.to_unicode(data))

def display_date(date, utc=False):
    """
    Format dates uniformly.
    
    Despite the name, this works on all datetime module objects.
    
    :Parameters:
        date
            A date-like object to format
    :Keywords:
        utc : bool
            Whether the date should be in canonical UTC format
    :Returns: A human-readable version of the date
    :ReturnType: unicode
    """
    if isinstance(date, datetime.datetime):
        from model.dates import to_local, to_utc
        if utc:
            date = to_utc(date)
        else:
            date = to_local(date)
        return unicode(date.replace(microsecond=0).isoformat())
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
        comps = ["%i %s" % (value, pluralize(value, singular, plural))
                 for value, (singular, plural) in zip([d, h, m, s], names)
                 if value]
        if comps:
            return " ".join(comps)
        else:
            return "%i %s" % (0, _("seconds"))
    else:
        raise TypeError("display_date received a non-datetime %r" % date)

def display_file_size(size):
    """
    Formats a file size to something human-readable.
    
    :Parameters:
        size : int
            The file size (in bytes)
    :Returns: The human-readable file size
    :ReturnType: unicode
    """
    base = 1024
    if size < (base ** 1):
        return _("%i bytes") % (size)
    elif size < (base ** 2):
        return _("%g KiB") % (size / (base ** 1))
    elif size < (base ** 3):
        return _("%g MiB") % (size / (base ** 2))
    elif size < (base ** 4):
        return _("%g GiB") % (size / (base ** 3))
    elif size < (base ** 5):
        # Not sure why we need this, but you never know...
        return _("%g TiB") % (size / (base ** 4))
    else:
        # Okay, we really shouldn't be worrying about sizes this big...
        return _("%g PiB") % (size / (base ** 5))

def display_weekday(day):
    """
    Turn an ISO weekday to a name.
    
    :Parameters:
        day : int
            An ISO weekday
    :Returns: The localized name of that day
    :ReturnType: unicode
    """
    lookup = {1: _("Monday"),
              2: _("Tuesday"),
              3: _("Wednesday"),
              4: _("Thursday"),
              5: _("Friday"),
              6: _("Saturday"),
              7: _("Sunday"),}
    return lookup[day]

def game_link(game, action='view', **params):
    """
    Create a link to a game.
    
    Any additional keyword parameters are sent as GET parameters.
    
    :Parameters:
        game : `hvz.model.game.Game` or int
            The game to link to
        action : str
            The action to use
    :Returns: The link to the object
    :ReturnType: str
    """
    if isinstance(game, (int, long)):
        pass
    else:
        game = game.game_id
    base = '/game/%s/%s' % (quote(action, ''), quote(str(game), ''))
    return _make_app_link(base, params)

def image_link(image, **params):
    """
    Create a link to an image.
    
    Any additional keyword parameters are sent as GET parameters.
    
    :Parameters:
        image : `hvz.model.images.Image` or UUID
            The image to link to
    :Returns: The link to the object
    :ReturnType: str
    """
    from hvz.model.images import Image
    if isinstance(image, Image):
        image_uuid = image.uuid
    else:
        image_uuid = to_uuid(image)
    base = '/image/%s' % (quote(str(image_uuid), ''))
    return _make_app_link(base, params)

def insecurelink(path):
    """
    Create an insecure URL from a pre-constructed path.
    
    :Parameters:
        path : str
            The path to convert
    :Returns: The insecure, absolute URI
    :ReturnType: str
    """
    baseURL = cherrypy.request.base
    # Replace URL's protocol with http
    baseURL = 'http' + baseURL[baseURL.index(':'):]
    return baseURL + path

def insecureurl(*args, **kw):
    """
    Create an insecure URL with the same signature as ``turbogears.url``.
    
    :Returns: The insecure, absolute URI
    :ReturnType: str
    """
    return insecurelink(turbogears.url(*args, **kw))

def login_link():
    """
    Returns the proper URL to the login page.
    
    :Returns: The URI for the page
    :ReturnType: str
    """
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
    """
    Returns the proper URL to the register page.
    
    :Returns: The URI for the page
    :ReturnType: str
    """
    if turbogears.config.get('hvz.secure_login', False):
        # Secure login
        return secureurl('/user/register')
    else:
        # Insecure login
        return turbogears.url('/user/register')

def securelink(path):
    """
    Create a secure URL from a pre-constructed path.
    
    :Parameters:
        path : str
            The path to convert
    :Returns: The secure, absolute URI
    :ReturnType: str
    """
    baseURL = cherrypy.request.base
    # Replace URL's protocol with https
    baseURL = 'https' + baseURL[baseURL.index(':'):]
    return baseURL + path

def secureurl(*args, **kw):
    """
    Create a secure URL with the same signature as ``turbogears.url``.
    
    :Returns: The secure, absolute URI
    :ReturnType: str
    """
    return securelink(turbogears.url(*args, **kw))

def to_uuid(value):
    """
    Converts an object to a UUID.
    
    :Parameters:
        value
            A value to convert to a UUID
    :Raises TypeError: If the value could not be converted
    :Returns: The UUID equivalent of the value
    :ReturnType: uuid.UUID
    """
    if isinstance(value, UUID) or value is None:
        return value
    elif isinstance(value, basestring):
        if len(value) == 16:
            return UUID(bytes=value)
        else:
            return UUID(value)
    elif isinstance(value, (int, long)):
        return UUID(int=value)
    elif isinstance(value, (list, tuple)):
        return UUID(fields=value)
    else:
        raise TypeError("Unrecognized type for UUID, got '%s'" %
                        (type(value).__name__))

def user_link(user, action='view', **params):
    """
    Create a link to a user.
    
    Any additional keyword parameters are sent as GET parameters.
    
    :Parameters:
        user : `hvz.model.identity.User`
            The user to link to
        action : str
            The action to use
    :Returns: The link to the object
    :ReturnType: str
    """
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

def add_template_variables(template_vars):
    """
    Adds functions to the template ``tg`` namespace.
    
    :Parameters:
        template_vars : dict
            The variable namespace to update
    :Returns: The updated namespace
    :ReturnType: dict
    """
    hvzNamespace = DictObj(alliance_link=alliance_link,
                           change_password_link=change_password_link,
                           game_link=game_link,
                           image_link=image_link,
                           login_link=login_link,
                           register_link=register_link,
                           user_link=user_link,)
    lookup = dict(hvz=hvzNamespace,
                  abslink=abslink,
                  absurl=absurl,
                  bbcode=bbcode,
                  change_params=change_params,
                  display=display,
                  display_date=display_date,
                  display_file_size=display_file_size,
                  display_weekday=display_weekday,
                  insecurelink=insecurelink,
                  insecureurl=insecureurl,
                  jsencode=jsencode,
                  plain2html=plain2html,
                  pluralize=pluralize,
                  securelink=securelink,
                  secureurl=secureurl,)
    return template_vars.update(lookup)

turbogears.view.variable_providers.append(add_template_variables)
