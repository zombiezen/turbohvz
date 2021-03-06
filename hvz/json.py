#!/usr/bin/env python
#
#   json.py
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

"""
A JSON-based API.

Most rules would look like::

    @jsonify.when("isinstance(obj, YourClass)")
    def jsonify_yourclass(obj):
        return [obj.val1, obj.val2]

@jsonify can convert your objects to following types: lists, dicts, numbers and
strings.
"""

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__docformat__ = 'reStructuredText'
__all__ = []

from turbojson.jsonify import jsonify
