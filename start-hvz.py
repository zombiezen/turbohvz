#!/usr/bin/env python
#
#   start-hvz.py
#   HvZ
#

"""
Start script for the HvZ TurboGears project.

This script is only needed during development for running from the project
directory. When the project is installed, easy_install will create a proper
start script.
"""

import sys

from hvz.commands import start, ConfigurationError

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'

if __name__ == "__main__":
    try:
        start()
    except ConfigurationError, exc:
        sys.stderr.write(str(exc))
        sys.exit(1)

