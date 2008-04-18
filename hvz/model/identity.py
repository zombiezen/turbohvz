#!/usr/bin/env python
#
#   model.py
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

from datetime import datetime, timedelta

import pkg_resources
pkg_resources.require("SQLAlchemy>=0.3.10")
pkg_resources.require("Elixir>=0.4.0")

from elixir import (Entity, Field, OneToMany, ManyToOne, ManyToMany,
                    options_defaults, using_options,
                    using_table_options, setup_all,
                    String, Unicode, Integer, Boolean, DateTime)
from sqlalchemy import UniqueConstraint
from turbogears import identity
from turbogears.database import session

from hvz.model.dates import now, date_prop

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['Visit',
           'VisitIdentity',
           'Group',
           'User',
           'Permission',]

options_defaults['autosetup'] = False

class Visit(Entity):
    """
    A visit to HvZ
    
    :IVariables:
        visit_key : str
            The visit name
        created : datetime
            When the visit started
        expiry : datetime
            When the visit will expire
    """
    using_options(tablename='visit')

    visit_key = Field(String(40), primary_key=True)
    created = Field(DateTime, nullable=False, default=datetime.utcnow,)
    expiry = Field(DateTime)
    
    @classmethod
    def lookup_visit(cls, visit_key):
        return Visit.get(visit_key)

class VisitIdentity(Entity):
    """
    A visit that has identified itself.
    
    :IVariables:
        visit_key : str
            The visit's identifier
        user : `User`
            The user the visit has identified as
    """
    using_options(tablename='visit_identity')

    visit_key = Field(String(40), primary_key=True)
    user = ManyToOne('User', colname='user_id', use_alter=True)

class Group(Entity):
    """
    A group of users with the same permissions.
    
    Users can be a member of multiple groups.
    
    :IVariables:
        group_id : int
            The group's basic identification number
        group_name : unicode
            The group's unique internal name
        display_name : unicode
            The group's human-readable name
        created : datetime.datetime
            The time at which the group was created
        users : list of `User`
            The members of the group
        permissions : list of `Permissions`
            The actions the group can perform
    """
    using_options(tablename='tg_group')

    group_id = Field(Integer, primary_key=True)
    group_name = Field(Unicode(16), unique=True)
    display_name = Field(Unicode(255), nullable=False)
    _created = Field(DateTime, colname='created', synonym='created')
    users = ManyToMany('User', tablename='user_group')
    permissions = ManyToMany('Permission', tablename='group_permission')
    
    @classmethod
    def by_group_name(cls, name):
        """
        Find a group by its internal name.
        
        :Parameters:
            name : unicode
                The internal name to query
        :Returns: The requested group, or ``None`` if not found
        :ReturnType: `Group`
        """
        return cls.query.filter_by(group_name=name).first()
    
    def __init__(self, name, display_name=None):
        if display_name is None:
            display_name = name
        self.group_name = unicode(name)
        self.display_name = unicode(display_name)
        self.created = now()
    
    def __repr__(self):
        return "<Group %s (%s)>" % (self.group_name, self.display_name)
    
    def __str__(self):
        return unicode(self).encode()
    
    def __unicode__(self):
        return self.display_name
    
    def add_permission(self, permission):
        """
        Adds a permission to the group.
        
        :Parameters:
            permission : `Permission` or unicode
                The permission to add.  If a unicode object is given, then the
                permission with the given internal name is fetched and added.
        :Raises TypeError: If the parameter is not a permission
        :Raises ValueError: If the permission is not found (a string is given)
        """
        if isinstance(permission, Permission):
            pass
        elif isinstance(permission, basestring):
            permission = Permission.by_permission_name(permission)
            if permission is None:
                raise ValueError("Cannot find permission %r" % permission)
        else:
            raise TypeError("Not a valid permission")
        self.permissions.append(permission)
    
    def remove_permission(self, permission):
        """
        Removes a permission from the group.
        
        :Parameters:
            permission : `Permission` or unicode
                The permission to remove.  If a unicode object is given, then
                the permission with the given internal name is fetched and
                removed.
        :Raises TypeError: If the parameter is not a permission
        :Raises ValueError: If the permission is not found (a string is given)
        """
        if isinstance(permission, Permission):
            pass
        elif isinstance(permission, basestring):
            permission = Permission.by_permission_name(permission)
            if permission is None:
                raise ValueError("Cannot find permission %r" % permission)
        else:
            raise TypeError("Not a valid permission")
        self.permissions.remove(permission)
    
    def add_user(self, user):
        """
        Adds a user to the group.
        
        :Parameters:
            user : `User` or unicode
                The user to add.  If a unicode object is given, then the user
                with the given internal name is fetched and added.
        :Raises TypeError: If the parameter is not a user
        :Raises ValueError: If the user is not found (a string is given)
        """
        if isinstance(user, User):
            pass
        elif isinstance(user, basestring):
            user = User.by_user_name(user)
            if user is None:
                raise ValueError("Cannot find user %r" % user)
        else:
            raise TypeError("Not a valid user")
        self.users.append(user)
    
    def remove_user(self, user):
        """
        Removes a user from the group.
        
        :Parameters:
            permission : `User` or unicode
                The user to remove.  If a unicode object is given, then the
                user with the given internal name is fetched and removed.
        :Raises TypeError: If the parameter is not a user
        :Raises ValueError: If the user is not found (a string is given)
        """
        if isinstance(user, User):
            pass
        elif isinstance(user, basestring):
            user = User.by_user_name(user)
            if user is None:
                raise ValueError("Cannot find user %r" % user)
        else:
            raise TypeError("Not a valid user")
        self.users.remove(user)
    
    created = date_prop('_created')

class User(Entity):
    """
    An individual user of the HvZ application.
    
    A user is not necessarily a player, but every player has a user associated
    with it.
    
    :IVariables:
        user_id : int
            The user's basic identification number
        user_name : unicode
            The user's unique internal name
        display_name : unicode
            The user's human-readable name
        email_address : unicode
            The user's email address
        password : unicode
            The (encrypted) text of the user's password.  Note that this
            depends on the configuration setting of password encryption.
            Using ``user.password = 'myPassword'`` will automagically
            encrypt the password.
        created : datetime.datetime
            The time at which the user joined/was created
        profile : unicode
            A user-provided text profile
        entries : list of `game.PlayerEntry`
            All the game entries that the user has joined
        groups : list of `Group`
            All groups that the user is a member of
        permissions : set of `Permission`
            An automatically calculated set of permissions, based on group
            permissions.
        is_legendary : bool
            Whether the player was part of the first game on the server
    :See: game.PlayerEntry
    """
    using_options(tablename='tg_user')

    user_id = Field(Integer, primary_key=True)
    user_name = Field(Unicode(16), unique=True)
    display_name = Field(Unicode(255), nullable=False)
    email_address = Field(Unicode(255))
    _password = Field(Unicode(40), colname='tg_password', synonym='password')
    _created = Field(DateTime, colname='created', synonym='created')
    groups = ManyToMany('Group', tablename='user_group')
    profile = Field(Unicode(4096))
    
    entries = OneToMany('hvz.model.game.PlayerEntry', inverse='player')
    
    @classmethod
    def by_user_name(cls, name):
        """
        Find a user by his or her name.
        
        :Parameters:
            name : unicode
                The internal name to query
        :Returns: The requested user, or ``None`` if not found
        :ReturnType: `User`
        """
        return cls.query.filter_by(user_name=name).first()
    
    def __init__(self, name, display_name=None, email=None, password=''):
        if display_name is None:
            display_name = name
        self.user_name = unicode(name)
        self.email_address = unicode(email) if email is not None else None
        self.display_name = unicode(display_name)
        self.password = password
        self.created = now()
        self.profile = None
    
    def __repr__(self):
        return "<User %i %s (%s)>" % (self.user_id,
                                      self.user_name,
                                      self.display_name)
    
    def __str__(self):
        return unicode(self).encode()
    
    def __unicode__(self):
        return self.display_name
    
    @property
    def permissions(self):
        p = set()
        for g in self.groups:
            p |= set(g.permissions)
        return p
    
    def _get_password(self):
        return self._password
    
    def _set_password(self, new_password):
        self._password = unicode(identity.encrypt_password(new_password))
    
    def set_raw_password(self, new_password):
        """
        Modifies the password column directly.  **Use with extreme caution.**
        
        :Parameters:
            new_password : unicode
                The new value of the password column
        """
        self._password = unicode(new_password)
    
    @property
    def is_legendary(self):
        from hvz.model.game import Game, PlayerEntry
        game = Game.query.order_by('created').first()
        if game is None:
            return False
        else:
            return bool(PlayerEntry.by_player(game, self) is not None)
    
    created = date_prop('_created')
    password = property(_get_password, _set_password)

class Permission(Entity):
    """
    A name that determines what each `Group` can do.
    
    :IVariables:
        permission_id : int
            The permission's basic identification number
        permission_name : unicode
            The permission's internal name
        description : unicode
            A short, human-readable description of what the permission allows
        groups : list of `Group`
            The groups that have this permission
    """
    using_options(tablename='permission')

    permission_id = Field(Integer, primary_key=True)
    permission_name = Field(Unicode(16), unique=True)
    description = Field(Unicode(255))
    groups = ManyToMany('Group', tablename='group_permission')
    
    @classmethod
    def by_permission_name(cls, name):
        """
        Find a permission by its name.
        
        :Parameters:
            name : unicode
                The internal name to query
        :Returns: The requested permission, or ``None`` if not found
        :ReturnType: `Permission`
        """
        return cls.query.filter_by(permission_name=name).first()
    
    def __init__(self, name, description):
        self.permission_name = unicode(name)
        self.description = unicode(description)
    
    def __repr__(self):
        return "<Permission %s>" % (self.permission_name)
    
    def __str__(self):
        return unicode(self).encode()
    
    def __unicode__(self):
        return self.description
