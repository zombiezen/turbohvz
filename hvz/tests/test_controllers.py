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

import cherrypy
import turbogears
from turbogears import testutil

from hvz.controllers.base import Root

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__all__ = ['TestPages']

cherrypy.root = Root()

class TestPages(unittest.TestCase):
    def setUp(self):
        turbogears.startup.startTurboGears()

    def tearDown(self):
        """Tests for apps using identity need to stop CP/TG after each test to
        stop the VisitManager thread.
        See http://trac.turbogears.org/turbogears/ticket/1217 for details.
        """
        turbogears.startup.stopTurboGears()
    
    def test_indextitle(self):
        "The indexpage should have the right title"
        testutil.create_request("/")
        response = cherrypy.response.body[0].lower()
        assert "<title>humans vs. zombies</title>" in response

    def test_logintitle(self):
        "login page should have the right title"
        testutil.create_request("/login")
        response = cherrypy.response.body[0].lower()
        assert "<title>login</title>" in response
