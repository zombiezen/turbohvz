#!/usr/bin/env python
#
#   hvz-create-perms.py
#   HvZ
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

