#!/usr/bin/env python
#
#   commands.py
#   HvZ
#

"""This module contains functions called from console script entry points."""

import os
import sys

import pkg_resources
pkg_resources.require("TurboGears>=1.0.4.4")
pkg_resources.require("SQLAlchemy>=0.3.10")

import cherrypy
import turbogears

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__all__ = ['ConfigurationError',
           'start',]

cherrypy.lowercase_api = True

class ConfigurationError(Exception):
    pass

def start():
    """Start the CherryPy application server."""
    setupdir = os.path.dirname(os.path.dirname(__file__))
    curdir = os.getcwd()
    # First look on the command line for a desired config file,
    # if it's not on the command line, then look for 'setup.py'
    # in the current directory. If there, load configuration
    # from a file called 'dev.cfg'. If it's not there, the project
    # is probably installed and we'll look first for a file called
    # 'prod.cfg' in the current directory and then for a default
    # config file called 'default.cfg' packaged in the egg.
    if len(sys.argv) > 1:
        configfile = sys.argv[1]
    elif os.path.exists(os.path.join(setupdir, "setup.py")):
        configfile = os.path.join(setupdir, "dev.cfg")
    elif os.path.exists(os.path.join(curdir, "prod.cfg")):
        configfile = os.path.join(curdir, "prod.cfg")
    else:
        try:
            configfile = pkg_resources.resource_filename(
                pkg_resources.Requirement.parse("HvZ"),
                "config/default.cfg")
        except pkg_resources.DistributionNotFound:
            raise ConfigurationError("Could not find default configuration.")
    turbogears.update_config(configfile=configfile,
                             modulename="hvz.config")
    from hvz.controllers import Root
    turbogears.start_server(Root())
