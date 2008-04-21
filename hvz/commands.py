#!/usr/bin/env python
#
#   commands.py
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

"""This module contains functions called from console script entry points."""

import os
import sys

import pkg_resources
pkg_resources.require("TurboGears>=1.0.4.4")
pkg_resources.require("SQLAlchemy>=0.4.2")

import cherrypy
import turbogears

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__all__ = ['ConfigurationError',
           'start',
           'start_wsgi',
           'create_permissions',
           'create_admin',]

cherrypy.lowercase_api = True

class ConfigurationError(Exception):
    pass

def _load_config(configfile=None):
    """
    Tries to load the project configuration.
    
    It first looks at the configfile parameter (usually straight from the
    command line) for a desired config file.  If it doesn't get a configfile,
    then look for ``setup.py`` in the current directory.  If there, load
    configuration from a file called ``dev.cfg``.  If it's not there, the
    project is probably installed and we'll look first for a file called
    ``prod.cfg`` in the current directory and then for a default config file
    called ``default.cfg`` packaged in the egg.
    
    :Parameters:
        configfile : str
            Path to a configuration file
    """
    setupdir = os.path.dirname(os.path.dirname(__file__))
    curdir = os.getcwd()
    if configfile is not None:
        pass
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
    turbogears.update_config(configfile=configfile, modulename="hvz.config")

def start(args=None):
    """Start the CherryPy application server."""
    # Read arguments
    if args is None:
        args = sys.argv[1:]
    if len(args) > 0:
        _load_config(args[0])
    else:
        _load_config()
    # Start the server
    from hvz.controllers.base import Root
    turbogears.start_server(Root())

def start_wsgi(args=None):
    """Start the CherryPy application server as an WSGI application."""
    # Read arguments
    if args is None:
        args = sys.argv[1:]
    if len(args) > 0:
        _load_config(args[0])
    else:
        _load_config()
    # Start the server
    from hvz.controllers.base import Root
    cherrypy.root = Root()
    # These two parameters ensure that this does not block, so WSGI hooks can
    # work properly and not hang.
    cherrypy.server.start(init_only=True, server_class=None)

def create_permissions(args=None):
    """Creates default groups and permissions"""
    # Read arguments
    if args is None:
        args = sys.argv[1:]
    if len(args) > 0:
        _load_config(args[0])
    else:
        _load_config()
    # Import necessary modules
    from turbogears.database import session
    from hvz.model.identity import Permission, Group
    # Create groups
    player = Group(u"player", u"Player")
    admin = Group(u"admin", u"Administrator")
    # Create permissions
    perms = {'view-player-gid': Permission(u"view-player-gid",
                                           u"View Player Game IDs"),
             'view-oz': Permission(u"view-oz",
                                   u"View Original Zombie"),
             'edit-user': Permission(u"edit-user",
                                     u"Edit Any User"),
             'view-user-email': Permission(u"view-user-email",
                                           u"View users' email addresses"),
             'sudo-login': Permission(u"sudo-login",
                                      u"Log in as anyone"),
             'view-int-name': Permission(u"view-int-name",
                                         u"View internal user names"),
             'create-game': Permission(u"create-game", u"Create Games"),
             'delete-game': Permission(u"delete-game", u"Delete Games"),
             'edit-game': Permission(u"edit-game", u"Edit Games"),
             'join-game': Permission(u"join-game", u"Join Games"),
             'stage-game': Permission(u"stage-game", u"Stage Games"),}
    # Set up group permissions
    player.add_permission(perms['join-game'])
    for perm in perms.itervalues():
        admin.add_permission(perm)
    # Save objects
    session.flush()

def create_admin(args=None):
    """Creates the administrator account"""
    # Read arguments
    if args is None:
        args = sys.argv[1:]
    if len(args) > 0:
        _load_config(args[0])
    else:
        _load_config()
    # Import necessary modules
    from getpass import getpass
    from turbogears.database import session
    from hvz.model.identity import Group, User
    # Check for admin group
    admin = Group.by_group_name(u'admin')
    if admin is None:
        raise ConfigurationError("No administrator group found")
    # Get user information
    if len(args) > 1:
        user_name = args[1].decode()
    else:
        user_name = raw_input("User name: ").decode()
    if len(args) > 2:
        display_name = args[2].decode()
    else:
        display_name = raw_input("Display name: ").decode()
    email_address = raw_input("Email Address: ").decode()
    while True:
        password1 = getpass("Password:")
        password2 = getpass("Retype Password:")
        if password1 == password2:
            break
        else:
            print >> sys.stderr, "Error: Passwords don't match"
    # Create user
    new_admin = User(user_name, display_name, email_address, password1)
    admin.add_user(new_admin)
    # Flush to database
    session.flush()
    print "Administrator '%s' created" % new_admin.user_name.encode('utf-8')
