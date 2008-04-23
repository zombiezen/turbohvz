#!/usr/bin/env python
#
#   model/identity.py
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
from uuid import UUID, uuid4

import pkg_resources
pkg_resources.require("SQLAlchemy>=0.4.2")

from sqlalchemy import (Table, Column, ForeignKey, UniqueConstraint,
                        String, Unicode, Integer, Boolean, DateTime)
from sqlalchemy.orm import relation, synonym
from turbogears import identity
from turbogears.database import mapper, metadata, session

import hvz
from hvz.model.dates import now, date_prop

__author__ = 'Ross Light'
__date__ = 'April 18, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['Visit',
           'VisitIdentity',
           'Group',
           'User',
           'Permission',]

### TABLES ###

visits_table = Table('visit', metadata,
    Column('visit_key', String(40), primary_key=True),
    Column('created', DateTime, nullable=False, default=datetime.utcnow),
    Column('expiry', DateTime)
)

visit_identity_table = Table('visit_identity', metadata,
    Column('visit_key', String(40), primary_key=True),
    Column('user_id', Integer, ForeignKey('tg_user.user_id'), index=True),
)

groups_table = Table('tg_group', metadata,
    Column('group_id', Integer, primary_key=True),
    Column('group_name', Unicode(16), unique=True),
    Column('display_name', Unicode(255)),
    Column('created', DateTime),
)

users_table = Table('tg_user', metadata,
    Column('user_id', Integer, primary_key=True),
    Column('user_name', Unicode(16), unique=True),
    Column('display_name', Unicode(255)),
    Column('email_address', Unicode(255)),
    Column('tg_password', Unicode(40)),
    Column('created', DateTime),
    Column('profile', Unicode(4096)),
    Column('image_uuid', String(32)),
)

permissions_table = Table('permission', metadata,
    Column('permission_id', Integer, primary_key=True),
    Column('permission_name', Unicode(16), unique=True),
    Column('description', Unicode(255))
)

user_group_table = Table('user_group', metadata,
    Column('user_id', Integer, ForeignKey('tg_user.user_id',
        onupdate='CASCADE', ondelete='CASCADE')),
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE'))
)

group_permission_table = Table('group_permission', metadata,
    Column('group_id', Integer, ForeignKey('tg_group.group_id',
        onupdate='CASCADE', ondelete='CASCADE')),
    Column('permission_id', Integer, ForeignKey('permission.permission_id',
        onupdate='CASCADE', ondelete='CASCADE'))
)

### CLASSES ###

class Visit(object):
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
    @classmethod
    def lookup_visit(cls, visit_key):
        return cls.query.get(visit_key)

class VisitIdentity(object):
    """
    A visit that has identified itself.
    
    :IVariables:
        visit_key : str
            The visit's identifier
        user : `User`
            The user the visit has identified as
    """

class Group(object):
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

class User(object):
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
        return self.tg_password
    
    def _set_password(self, new_password):
        self.tg_password = unicode(identity.encrypt_password(new_password))
    
    def set_raw_password(self, new_password):
        """
        Modifies the password column directly.  **Use with extreme caution.**
        
        :Parameters:
            new_password : unicode
                The new value of the password column
        """
        self._password = unicode(new_password)
    
    def _get_image_uuid(self):
        if self._image_uuid is None:
            return None
        else:
            return UUID(hex=self._image_uuid)
    
    def _set_image_uuid(self, value):
        value = hvz.util.to_uuid(value)
        self._image_uuid = value.hex
    
    def _get_image(self):
        if self.image_uuid is not None:
            return hvz.model.images.Image.by_uuid(self.image_uuid)
        else:
            return None
    
    def _set_image(self, value):
        if self._image_uuid:
            # TODO: Clean up old image
            pass
        if value is None:
            self.image_uuid = None
        elif isinstance(value, hvz.model.images.Image):
            self.image_uuid = value.uuid
        else:
            self.image_uuid = value
    
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
    image_uuid = property(_get_image_uuid, _set_image_uuid)
    image = property(_get_image, _set_image)

class Permission(object):
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

## MAPPERS ##

mapper(Visit, visits_table)
mapper(VisitIdentity, visit_identity_table,
       properties=dict(user=relation(User, backref='visit_identity'),))
mapper(User, users_table,
        properties=dict(password=synonym('tg_password'),
                        created=synonym('_created', map_column=True),
                        image_uuid=synonym('_image_uuid', map_column=True),))
mapper(Group, groups_table,
        properties=dict(users=relation(User, backref='groups',
                                       secondary=user_group_table),
                        created=synonym('_created', map_column=True),))
mapper(Permission, permissions_table,
        properties=dict(groups=relation(Group, backref='permissions',
                                        secondary=group_permission_table),))
