#!/usr/bin/env python
#
#   hvz-create-perms.py
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
Creates HvZ permissions in the database.

This script is only needed during development for running from the project
directory. When the project is installed, easy_install will create a proper
script.
"""

import sys

from hvz.commands import create_permissions, ConfigurationError

__author__ = 'Ross Light'
__date__ = 'April 7, 2008'

if __name__ == "__main__":
    try:
        create_permissions()
    except ConfigurationError, exc:
        sys.stderr.write(str(exc))
        sys.exit(1)

