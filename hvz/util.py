#!/usr/bin/env python
#
#   util.py
#   HvZ
#

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['abslink',
           'absurl',
           'change_params',
           'display',
           'display_date',
           'display_weekday',
           'game_link',
           'insecurelink',
           'insecureurl',
           'plain2html',
           'securelink',
           'secureurl',
           'str2bool',
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

def display(widget, *args, **kw):
    """Display a widget in Genshi"""
    data = widget.render(format='html', *args, **kw)
    return genshi.HTML(turbogears.util.to_unicode(data))

def display_date(date):
    """Format dates uniformly"""
    if isinstance(date, datetime.datetime):
        from model import to_local
        return unicode(to_local(date).replace(microsecond=0).isoformat())
    elif isinstance(date, datetime.date):
        return unicode(date.isoformat())
    elif isinstance(date, datetime.time):
        return unicode(date.replace(microsecond=0, tzinfo=None).isoformat())
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

def user_link(user, action='view', **params):
    if isinstance(user, (int, long)):
        pass
    elif hasattr(user, 'player_id'):
        user = user.player_id
    else:
        user = user.user_id
    base = '/user/%s/%s' % (quote(action, ''), quote(str(user), ''))
    return _make_app_link(base, params)

def add_template_variables(vars):
    hvzNamespace = DictObj(game_link=game_link,
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
                  securelink=securelink,
                  secureurl=secureurl,)
    return vars.update(lookup)

turbogears.view.variable_providers.append(add_template_variables)
