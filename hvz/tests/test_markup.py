#!/usr/bin/env python
#
#   test_controllers.py
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

"""Test controller objects"""

import unittest

from hvz.markup import render_bbcode as render

__author__ = 'Ross Light'
__date__ = 'May 16, 2008'
__all__ = ['TestMarkup']

def test_literal_bracket():
    """Markup should render brackets literally"""
    result = render('[')
    assert result == '[', "Bracket denied!"
    result = render(':-[ [b]Hello, World![/b]')
    assert result == ':-[ <strong>Hello, World!</strong>', "Bracket denied!"

def test_linking():
    """Markup should hyperlink [link] tags"""
    desired = ("<a href=\"http://turbohvz.googlecode.com\" "
               "title=\"http://turbohvz.googlecode.com\">"
               "Homepage</a> [turbohvz.googlecode.com]")
    result = render("[link=http://turbohvz.googlecode.com]Homepage[/link]")
    assert result == desired, "Bad linking (got %r)" % result
    result = render('[link="http://turbohvz.googlecode.com"]Homepage[/link]')
    assert result == desired, "Bad linking (got %r)" % result
    result = render("[link http://turbohvz.googlecode.com]Homepage[/link]")
    assert result == desired, "Bad linking (got %r)" % result
    desired = ("<a href=\"http://turbohvz.googlecode.com\" "
               "title=\"http://turbohvz.googlecode.com\">"
               "http://turbohvz.googlecode.com</a> [turbohvz.googlecode.com]")
    result = render("[link]http://turbohvz.googlecode.com[/link]")
    assert result == desired, "Bad linking (got %r)" % result
    result = render("[link][link]http://turbohvz.googlecode.com[/link][/link]")
    assert result == desired, "Bad link flattening"

def test_search():
    """Markup should hyperlink search tags"""
    result = render(u"[google]Andr\u00e9 Man[/google]")
    desired = (u"<a href=\"http://www.google.com/search?"
               u"hl=en&amp;q=Andr%E9+Man&amp;btnG=Google+Search\" "
               u"title=\"google.com\">"
               u"Andr\u00e9 Man</a> [google.com]")
    assert result == desired, "Bad link unicoding"

def test_basic_formatting():
    """Markup should be able to do basic formatting"""
    result = render(u"[b]Hello Andr\u00e9[/b]")
    assert result == u"<strong>Hello Andr\u00e9</strong>", "Bad bolding"
    result = render(u"[i]Hello World[/i]")
    assert result == u"<em>Hello World</em>", "Bad italics"
    result = render(u"[u]Hello World[/u]")
    assert result == u"<u>Hello World</u>", "Bad underline"
    result = render(u"[s]Strike through[/s]")
    assert result == "<strike>Strike through</strike>", "Bad striking"
    result = render(u"Hello\nWorld\n\nAnother game.")
    assert result == "Hello<br/>World<br/><br/>Another game.", "Bad linebreaks"

def test_overlapping():
    """Markup should gracefully overlap formatting tags"""
    result = render(u"[b]bold [i]bold and italic[/b] italic[/i]")
    desired = "<strong>bold <em>bold and italic</em></strong><em> italic</em>"
    assert result == desired, "Overlapping does not work"

def test_list():
    """Markup should handle lists correctly"""
    desired = "<ul><li>First</li><li>Second item</li></ul>"
    result = render("[list][*]First[*]Second item[/list]")
    assert result == desired, "Bad simple list"
    result = render("""[list]
    [*]First
[*]Second item
[/list]""")
    assert result == desired, "Bad list blocking"
    desired = "<li>First</li><li>Second</li><li>The Third</li></ol>"
    inputCode = "[*]First[*]Second[*]The Third[/list]"
    result = render("[list=1]" + inputCode)
    assert result == "<ol>" + desired, "Bad ordered"
    result = render("[list=A]" + inputCode)
    assert result == "<ol style=\"list-style-type: upper-alpha;\">" + desired, \
        "Bad ordered lettered"
    result = render("[list=a]" + inputCode)
    assert result == "<ol style=\"list-style-type: lower-alpha;\">" + desired, \
        "Bad ordered lower lettered"

def test_xss():
    """Markup should be invulnerable to Cross-Site-Scripting"""
    result = render("<script>Basic & stuff</script>")
    assert result == "&lt;script&gt;Basic &amp; stuff&lt;/script&gt;"
    result = render("[url=<script>Attack</script>]Attack[/url]")
    assert result == ("<a href=\"http://%3Cscript%3EAttack%3C/script%3E\" "
                      "title=\"http://%3Cscript%3EAttack%3C/script%3E\">"
                      "Attack</a> [&lt;script&gt;attack&lt;]"), \
        "Vulnerable to URL attack"
    result = render("[img]<script>Attack</script>[/img]")
    assert result == ("<img src=\"&lt;script&gt;Attack&lt;/script&gt;\">"
                      "</img><div style=\"display:none\">"
                      "&lt;script&gt;Attack&lt;/script&gt;</div>"), \
        "Vulnerable to image attack"
