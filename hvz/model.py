#!/usr/bin/env python
#
#   model.py
#   HvZ
#

from datetime import datetime

import pkg_resources
pkg_resources.require("SQLAlchemy>=0.3.10")
pkg_resources.require("Elixir>=0.4.0")

from elixir import (Entity, Field, OneToMany, ManyToOne, ManyToMany,
                    options_defaults, using_options, setup_all,
                    String, Unicode, Integer, Boolean, DateTime)
from turbogears import identity

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__all__ = ['PlayerEntry',
           'Game',
           'Visit',
           'VisitIdentity',
           'Group',
           'User',
           'Permission',]

options_defaults['autosetup'] = False

# your data model

class PlayerEntry(Entity):
    """
    Per-game player statistics.
    
    :IVariables:
        player : `User`
            The player this is associated with
        game : `Game`
            The game associated
        player_gid : str
            In-game player identifier (Player Game Identifier)
        state : int
            -1 is zombie, -2 is original zombie, 0 is dead, 1 is human (-3 and
            2 are mysteries)
        death_date : datetime
            When the player died (tagged by zombie)
        feed_date : datetime
            Last time fed
        kills : int
            How many humans tagged
        killed_by : `User`
            Who killed the user
        original_pool : bool
            Whether the user wants to be considered for being the original
            zombie
        starve_date : datetime
            When the player starved
    """
    using_options(tablename='entries')
    
    entry_id = Field(Integer, primary_key=True)
    player = ManyToOne('User', inverse='entries')
    game = ManyToOne('Game', inverse='entries')
    player_gid = Field(String(128))
    state = Field(Integer)
    death_date = Field(DateTime)
    feed_date = Field(DateTime)
    kills = Field(Integer)
    killed_by = ManyToOne('User')
    original_pool = Field(Boolean)
    starve_date = Field(DateTime)
    
    @classmethod
    def by_player_gid(cls, game, gid):
        """Fetches an entry by game and player_gid."""
        return cls.query.filter_by(game=game, player_gid=gid).first()
    
    def __init__(self, game, player):
        assert game is not None
        assert player is not None
        self.game = game
        self.player = player
        # TODO: self.player_game_id
        self.state = 1
        self.death_date = None
        self.feed_date = None
        self.kills = 0
        self.original_pool = False
        self.starve_date = None
    
    def kill(self, other, date=None):
        if date is None:
            date = datetime.utcnow()
        if self.state < 0:
            if other.state == 1:
                self.kills += 1
                self.feed_date = other.death_date = date
                other.state = -1
                other.killed_by = self.player
            else:
                raise ValueError("Victim is nonhuman")
        else:
            raise ValueError("Killer is nonzombie")
    
    def __repr__(self):
        return "<PlayerEntry %i:%s (%s)>" % (self.game.game_id,
                                             self.player_gid,
                                             self.player.user_name,)
    
    def __str__(self):
        return unicode(self).encode()
    
    def __unicode__(self):
        return unicode(self.player)

class Game(Entity):
    """
    A game played.
    
    :IVariables:
        created : datetime
        started : datetime
        ended : datetime
        revealed_zombie : bool
        registration_open : bool
        state : int
            The current state of the game.  Stages:
            =====   =========================
             No.           Description
            =====   =========================
            0       Game created, not open
            1       Open registration
            2       Registration closed
            3       Choose original zombie
            4       Start game
            5       Original zombie revealed?
            6       End game
            =====   =========================
        entries : list of `PlayerEntry` objects
        players : list of `User` objects
    """
    using_options(tablename='game')
    
    game_id = Field(Integer, primary_key=True)
    created = Field(DateTime)
    started = Field(DateTime)
    ended = Field(DateTime)
    state = Field(Integer)
    entries = OneToMany('PlayerEntry', inverse='game')
    
    def __init__(self):
        self.created = datetime.utcnow()
        self.started = None
        self.ended = None
        self.state = 0
    
    @property
    def revealed_original_zombie(self):
        return self.state >= 5
    
    @property
    def registration_open(self):
        return self.state == 1
    
    @property
    def players(self):
        return [entry.player for entry in self.entries]

# the identity model

class Visit(Entity):
    """
    A visit to your site
    """
    using_options(tablename='visit')

    visit_key = Field(String(40), primary_key=True)
    created = Field(DateTime, nullable=False, default=datetime.utcnow)
    expiry = Field(DateTime)
    
    @classmethod
    def lookup_visit(cls, visit_key):
        return Visit.get(visit_key)


class VisitIdentity(Entity):
    """
    A Visit that is link to a User object
    """
    using_options(tablename='visit_identity')

    visit_key = Field(String(40), primary_key=True)
    user = ManyToOne('User', colname='user_id', use_alter=True)


class Group(Entity):
    """
    An ultra-simple group definition.
    """
    using_options(tablename='tg_group')

    group_id = Field(Integer, primary_key=True)
    group_name = Field(Unicode(16), unique=True)
    display_name = Field(Unicode(255), nullable=False)
    created = Field(DateTime, default=datetime.utcnow)
    users = ManyToMany('User', tablename='user_group')
    permissions = ManyToMany('Permission', tablename='group_permission')
    
    def __init__(self, name, display_name=None):
        if display_name is None:
            display_name = name
        self.group_name = unicode(name)
        self.display_name = unicode(display_name)
        self.created = datetime.utcnow()

class User(Entity):
    """
    Reasonably basic User definition.
    Probably would want additional attributes.
    """
    using_options(tablename='tg_user')

    user_id = Field(Integer, primary_key=True)
    user_name = Field(Unicode(16), unique=True)
    email_address = Field(Unicode(255))
    display_name = Field(Unicode(255), nullable=False)
    _password = Field(Unicode(40), colname='tg_password')
    created = Field(DateTime)
    groups = ManyToMany('Group', tablename='user_group')
    
    entries = OneToMany('PlayerEntry', inverse='player')
    
    @classmethod
    def by_user_name(cls, name):
        """Find a user by his or her name."""
        return cls.query.filter_by(user_name=name).first()
    
    def __init__(self, name, display_name=None, email=None, password=''):
        if display_name is None:
            display_name = name
        self.user_name = unicode(name)
        self.email_address = unicode(email) if email is not None else None
        self.display_name = unicode(display_name)
        self.password = password
        self.created = datetime.utcnow()
    
    def __repr__(self):
        return "<User %s (%s)>" % (self.user_name, self.display_name)
    
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
        self._password = unicode(new_password)
    
    password = property(_get_password, _set_password)

class Permission(Entity):
    """
    A relationship that determines what each Group can do
    """
    using_options(tablename='permission')

    permission_id = Field(Integer, primary_key=True)
    permission_name = Field(Unicode(16), unique=True)
    description = Field(Unicode(255))
    groups = ManyToMany('Group', tablename='group_permission')
    
    def __init__(self, name, description):
        self.permission_name = unicode(name)
        self.description = unicode(description)

# Set up all Elixir entities declared above

setup_all()

