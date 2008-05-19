#!/usr/bin/env python
#
#   controllers/__init__.py
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

"""Classes to handle client-data interactions"""

__author__ = 'Ross Light'
__date__ = 'April 18, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['base',
           'feeds',
           'game',
           'user',]

from hvz.controllers import (base,
                             feeds,
                             game,
                             user,)
