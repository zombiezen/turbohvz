#!/usr/bin/env python
#
#   model/social.py
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

"""Social features"""

import pkg_resources
pkg_resources.require("SQLAlchemy>=0.4.2")

from sqlalchemy import (Table, Column, ForeignKey, UniqueConstraint,
                        String, Unicode, Integer, Boolean, DateTime)
from sqlalchemy.orm import backref, relation, synonym
from turbogears.database import mapper, metadata, session

from hvz.model import identity
from hvz.model.dates import (now, date_prop, make_aware,
                             calc_timedelta, calc_addtimedelta)
from hvz.model.errors import WrongStateError, InvalidTimeError

__author__ = 'Ross Light'
__date__ = 'May 18, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['Alliance']

### TABLES ###

alliances_table = Table('alliances', metadata,
    Column('alliance_id', Integer, primary_key=True),
    Column('display_name', Unicode(255)),
    Column('description', Unicode(4096)),
    Column('created', DateTime),
    Column('owner_id', Integer, ForeignKey('tg_user.user_id',
           ondelete='RESTRICT', onupdate='CASCADE')),
)

user_alliance_table = Table('user_alliance', metadata,
    Column('user_id', Integer, ForeignKey('tg_user.user_id',
           ondelete='CASCADE', onupdate='CASCADE')),
    Column('alliance_id', Integer, ForeignKey('alliances.alliance_id',
           ondelete='CASCADE', onupdate='CASCADE')),
)

### CLASSES ###

class Alliance(object):
    """
    A user-formed alliance.
    
    :IVariables:
        alliance_id : int
            The alliance's database ID
        display_name : unicode
            The alliance's name
        description : unicode
            The alliance's profile
        created : datetime
            The time at which the alliance was created
        owner : hvz.identity.User
            The creator of the alliance
    """
    def __init__(self, name, description=None, owner=None):
        self.display_name = name
        self.description = description
        self.created = now()
        self.owner = owner
    
    def __repr__(self):
        return "<Alliance %i (%s)>" % (self.alliance_id, self.display_name)
    
    def __str__(self):
        return unicode(self).encode()
    
    def __unicode__(self):
        return self.display_name
    
    created = date_prop('_created')

### MAPPERS ###

mapper(Alliance, alliances_table, properties={
    'users':
        relation(identity.User, backref='alliances',
                 secondary=user_alliance_table),
    'owner':
        relation(identity.User,
                 primaryjoin=(alliances_table.c.owner_id ==
                              identity.users_table.c.user_id),
                 uselist=False),
    'created': synonym('_created', map_column=True),
})
