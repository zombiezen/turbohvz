#!/usr/bin/env python
#
#   model.py
#   HvZ
#

from datetime import datetime, timedelta
import random
import string

import pkg_resources
pkg_resources.require("SQLAlchemy>=0.3.10")
pkg_resources.require("Elixir>=0.4.0")
pkg_resources.require("pytz")

from elixir import (Entity, Field, OneToMany, ManyToOne, ManyToMany,
                    options_defaults, using_options,
                    using_table_options, setup_all,
                    String, Unicode, Integer, Boolean, DateTime)
import pytz
from sqlalchemy import UniqueConstraint
from turbogears import identity, config

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['as_local',
           'as_utc',
           'to_local',
           'to_utc',
           'PlayerEntry',
           'Game',
           'Visit',
           'VisitIdentity',
           'Group',
           'User',
           'Permission',]

options_defaults['autosetup'] = False

# Date functions

def _get_local_timezone():
    return pytz.timezone(config.get('hvz.timezone', 'UTC'))

def as_local(date, tz=None):
    """
    Interprets (but does not convert) the date as being in the local timezone.
    
    :Parameters:
        date : datetime.datetime
            The date to interpret
        tz : datetime.tzinfo
            The timezone to interpret as.  If not given, then the timezone is
            read from the ``hvz.timezone`` configuration value.
    :Returns: The timezone-aware date
    :ReturnType: datetime.datetime
    """
    if tz is None:
        tz = _get_local_timezone()
    return tz.localize(date)

def as_utc(date):
    """
    Interprets (but does not convert) the date as UTC.
    
    :Parameters:
        date : datetime.datetime
            The date to interpret
    :Returns: The timezone-aware date
    :ReturnType: datetime.datetime
    """
    return date.replace(tzinfo=pytz.utc)

def to_local(date, tz=None):
    """
    Converts the date to the local timezone.
    
    :Parameters:
        date : datetime.datetime
            The date to convert.  If this date is naive, then it will be
            interpreted as UTC.
        tz : datetime.tzinfo
            The timezone to convert to.  If not given, then the timezone is
            read from the ``hvz.timezone`` configuration value.
    :Returns: The timezone-aware date
    :ReturnType: datetime.datetime
    """
    if tz is None:
        tz = _get_local_timezone()
    if date.tzinfo is None:
        date = as_utc(date)
    return date.astimezone(tz)

def to_utc(date):
    """
    Converts the date to UTC.
    
    :Parameters:
        date : datetime.datetime
            The date to convert.  If this date is naive, then it will be
            interpreted as UTC.
    :Returns: The timezone-aware date
    :ReturnType: datetime.datetime
    """
    if date.tzinfo is None:
        date = as_utc(date)
    return date.astimezone(pytz.utc)

def _get_date_prop(name):
    """
    Retrieves a date from the database, interpreting it as UTC.
    
    :Parameters:
        name : str
            Attribute name for the column
    :Returns: A function that can be used as a property getter
    :ReturnType: function
    """
    def get_prop(self):
        value = getattr(self, name)
        if value is None:
            return None
        else:
            return as_utc(value)
    return get_prop

def _set_date_prop(name, default_tz=pytz.utc):
    """
    Updates a date in the database, converting it to UTC.
    
    :Parameters:
        name : str
            Attribute name for the column
    :Keywords:
        default_tz : datetime.tzinfo
            Default timezone to intepret naive 
    :Returns: A function that can be used as a property setter
    :ReturnType: function
    """
    def set_prop(self, value):
        if value is not None:
            if value.tzinfo is None:
                value = as_local(value, default_tz)
            value = to_utc(value)
        setattr(self, name, value)
    return set_prop

def _date_prop(name, default_tz=pytz.utc):
    return property(_get_date_prop(name),
                    _set_date_prop(name, default_tz=default_tz))

def _calc_timedelta(datetime1, datetime2, tz=None,
                    ignore_dates=None, ignore_weekdays=None):
    """
    Calculates the delta between two datetimes.
    
    Along with subtracting the two dates, this removes time on specific dates
    and weekdays.
    
    :Parameters:
        datetime1
            The first date and time
        datetime2
            The second date and time
    :Keywords:
        tz : datetime.tzinfo
            The timezone to calculate dates in.  If you get the wrong timezone,
            your results will possibly be **very incorrect**.  This is because
            the algorithm should be looking at dates in the players'
            timezone, which is rarely UTC.
        ignore_dates : list of datetime.date
            Days that are removed from the difference
        ignore_weekdays : list of int
            Weekdays that are removed from the difference (given as ISO weekday
            numbers)
    :Returns: The difference between the two dates
    :ReturnType: datetime.timedelta
    """
    assert datetime1 <= datetime2
    # Get arguments
    if tz is None:
        tz = _get_local_timezone()
    if ignore_dates is None:
        ignore_dates = []
    if ignore_weekdays is None:
        ignore_weekdays = []
    datetime1, datetime2 = as_local(datetime1, tz), as_local(datetime2, tz)
    # Calculate basic difference
    difference = datetime2 - datetime1
    # Find date range
    date1, date2 = (datetime1.date(), datetime2.date())
    # Loop through all dates in-between date1 and date2
    accum_date = date1
    while accum_date <= date2:
        if accum_date in ignore_dates or \
           accum_date.isoweekday() in ignore_weekdays:
            # This date is an ignore day, so let's decide what to do:
            if accum_date == date1:
                # This is the first date, so get the amount of time remaining
                # in the day on datetime1 and subtract it from the difference
                this_day = datetime1.replace(hour=0, minute=0, second=0,
                                             microsecond=0)
                next_day = this_day + timedelta(1)
                difference -= next_day - datetime1
            elif accum_date == date2:
                # This is the last date, so get the amount of time elapsed
                # in the day on datetime2 and subtract it from the difference
                this_day = datetime2.replace(hour=0, minute=0, second=0,
                                             microsecond=0)
                difference -= datetime2 - this_day
            else:
                # Woo-hoo!  This is a full ignore day, so let's do simple math.
                difference -= timedelta(1)
        # Okay, let's take up the next day
        accum_date += timedelta(1)
    # Ensure that difference >= 0
    # This prevents the weird case where 
    difference = max(timedelta(), difference)
    # Return result
    return difference

# your data model

class PlayerEntry(Entity):
    """
    Per-game player statistics.
    
    :CVariables:
        STATE_ORIGINAL_ZOMBIE : int
            The constant for the original zombie state
        STATE_ZOMBIE : int
            The constant for a non-original zombie state
        STATE_DEAD : int
            The constant for a starved zombie state
        STATE_HUMAN : int
            The constant for a healthy human state
        STATE_NAMES : dict of {int: unicode}
            State-to-human-readable-name lookup table
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
    :See: User
    """
    using_options(tablename='entries')
    
    STATE_ORIGINAL_ZOMBIE = -2
    STATE_ZOMBIE = -1
    STATE_DEAD = 0
    STATE_HUMAN = 1
    STATE_NAMES = {STATE_ORIGINAL_ZOMBIE: _("Original zombie"),
                   STATE_ZOMBIE: _("Zombie"),
                   STATE_DEAD: _("Dead"),
                   STATE_HUMAN: _("Human"),}
    
    entry_id = Field(Integer, primary_key=True)
    player = ManyToOne('User', colname='player_id', inverse='entries')
    game = ManyToOne('Game', colname='game_id', inverse='entries')
    player_gid = Field(String(128))
    state = Field(Integer)
    _death_date = Field(DateTime, colname='death_date', synonym='death_date')
    _feed_date = Field(DateTime, colname='feed_date', synonym='feed_date')
    kills = Field(Integer)
    # _killed_by: Yes, it's a foreign key, but SQLAlchemy doesn't seem to like
    # it, so just making it an integer temporarily.
    _killed_by = Field(Integer, colname='killed_by', synonym='killed_by')
    original_pool = Field(Boolean)
    _starve_date = Field(DateTime, colname='starve_date', synonym='starve_date')
    
    @staticmethod
    def _generate_id(id_length):
        id_chars = string.ascii_uppercase + string.digits
        result = ''.join(random.choice(id_chars) for i in xrange(id_length))
        return result
    
    @classmethod
    def by_player(cls, game, user):
        """Fetches an entry by game and player."""
        return cls.query.filter_by(game=game, player=user).first()
    
    @classmethod
    def by_player_gid(cls, game, gid):
        """Fetches an entry by game and player_gid."""
        return cls.query.filter_by(game=game, player_gid=gid).first()
    
    def __init__(self, game, player):
        assert game is not None
        assert player is not None
        id_length = int(config.get('hvz.id_length', '16'), 10)
        self.game = game
        self.player = player
        self.player_gid = self._generate_id(id_length)
        self.state = 1
        self.death_date = None
        self.feed_date = None
        self.kills = 0
        self.killed_by = None
        self.original_pool = False
        self.starve_date = None
    
    def kill(self, other, date=None):
        if date is None:
            date = as_utc(datetime.utcnow())
        if self.is_undead:
            if other.is_human:
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
    
    def _get_killed_by(self):
        value = self._killed_by
        if value is None:
            return None
        else:
            return User.get(value)
    
    def _set_killed_by(self, new_killer):
        if new_killer is None:
            self._killed_by = None
        elif isinstance(new_killer, (int, long)):
            assert User.get(new_killer) is not None
            self._killed_by = new_killer
        else:
            self._killed_by = new_killer.user_id
    
    @property
    def affiliation(self):
        return self.STATE_NAMES[self.state]
    
    @property
    def is_undead(self):
        return self.state in (self.STATE_ORIGINAL_ZOMBIE, self.STATE_ZOMBIE)
    
    @property
    def is_human(self):
        return self.state == self.STATE_HUMAN
    
    @property
    def is_dead(self):
        return self.state == self.STATE_DEAD
    
    death_date = _date_prop('_death_date')
    feed_date = _date_prop('_feed_date')
    starve_date = _date_prop('_starve_date')
    killed_by = property(_get_killed_by, _set_killed_by)
    
    using_table_options(UniqueConstraint('game_id', 'player_gid'),
                        UniqueConstraint('game_id', 'player_id'),)

class Game(Entity):
    """
    A game played.
    
    :CVariables:
        STATE_CREATED : int
            The initial game state
        STATE_OPEN : int
            Open registration
        STATE_CLOSED : int
            Closed registration
        STATE_CHOOSE_ZOMBIE : int
            Choose original zombie
        STATE_STARTED : int
            Game has started
        STATE_REVEAL_ZOMBIE : int
            Revealed original zombie
        STATE_ENDED : int
            Game is over
    :IVariables:
        created : datetime
        started : datetime
        ended : datetime
        revealed_zombie : bool
        registration_open : bool
        state : int
            The current state of the game.  See the ``STATE_*`` class
            constants.
        entries : list of `PlayerEntry` objects
        players : list of `User` objects
    """
    using_options(tablename='game')
    
    STATE_CREATED = 0
    STATE_OPEN = 1
    STATE_CLOSED = 2
    STATE_CHOOSE_ZOMBIE = 3
    STATE_STARTED = 4
    STATE_REVEAL_ZOMBIE = 5
    STATE_ENDED = 6
    
    game_id = Field(Integer, primary_key=True)
    _created = Field(DateTime, colname='created', synonym='created')
    _started = Field(DateTime, colname='started', synonym='started')
    _ended = Field(DateTime, colname='ended', synonym='ended')
    state = Field(Integer)
    entries = OneToMany('PlayerEntry', inverse='game')
    
    def __init__(self):
        self.created = datetime.utcnow()
        self.started = None
        self.ended = None
        self.state = self.STATE_CREATED
    
    @property
    def revealed_original_zombie(self):
        return self.state >= self.STATE_REVEAL_ZOMBIE
    
    @property
    def in_progress(self):
        return self.STATE_STARTED <= self.state < self.STATE_ENDED
    
    @property
    def registration_open(self):
        return self.state == self.STATE_OPEN
    
    @property
    def players(self):
        return [entry.player for entry in self.entries]
    
    @property
    def is_first_state(self):
        return bool(self.state <= self.STATE_CREATED)
    
    @property
    def is_last_state(self):
        return bool(self.state >= self.STATE_ENDED)
    
    @property
    def original_zombie_pool(self):
        return [entry for entry in self.entries if entry.original_pool]
    
    def previous_state(self):
        # Check if we can do this
        if self.is_first_state:
            raise ValueError("The game has not yet begun")
        # Go previous state
        self.state -= 1
        # Do state hooks
        if self.state == self.STATE_STARTED - 1:
            self.started = None
        elif self.state == self.STATE_ENDED - 1:
            self.ended = None
        elif self.state == self.STATE_CHOOSE_ZOMBIE - 1:
            for entry in self.entries:
                entry.state = PlayerEntry.STATE_HUMAN
    
    def next_state(self):
        # Check if we can do this
        if self.is_last_state:
            raise ValueError("The game is already over")
        # Go next state
        self.state += 1
        # Do state hooks
        if self.state == self.STATE_STARTED:
            self.started = datetime.utcnow()
        elif self.state == self.STATE_ENDED:
            self.ended = datetime.utcnow()
    
    created = _date_prop('_created')
    started = _date_prop('_started')
    ended = _date_prop('_ended')

# the identity model

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
    _created = Field(DateTime, colname='created', synonym='created',
                     nullable=False, default=datetime.utcnow,)
    _expiry = Field(DateTime, colname='expiry', synonym='expiry')
    
    @classmethod
    def lookup_visit(cls, visit_key):
        return Visit.get(visit_key)
    
    created = _date_prop('_created', default_tz=None)
    expiry = _date_prop('_expiry', default_tz=None)

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
        self.created = datetime.utcnow()
    
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
    
    created = _date_prop('_created')

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
            Using ``user.password = 'random_string'`` will automagically
            encrypt the password.
        created : datetime.datetime
            The time at which the user joined/was created
        profile : unicode
            A user-provided text profile
        entries : list of `PlayerEntry`
            All the game entries that the user has joined
        groups : list of `Group`
            All groups that the user is a member of
        permissions : set of `Permission`
            An automatically calculated set of permissions, based on group
            permissions.
    :See: PlayerEntry
    """
    using_options(tablename='tg_user')

    user_id = Field(Integer, primary_key=True)
    user_name = Field(Unicode(16), unique=True)
    display_name = Field(Unicode(255), nullable=False)
    email_address = Field(Unicode(255))
    _password = Field(Unicode(40), colname='tg_password', synonym='password')
    _created = Field(DateTime, colname='created', synonym='created')
    groups = ManyToMany('Group', tablename='user_group')
    profile = Field(Unicode(1024))
    
    entries = OneToMany('PlayerEntry', inverse='player')
    
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
        self.created = datetime.utcnow()
        self.profile = None
    
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
        """
        Modifies the password column directly.  **Use with extreme caution.**
        
        :Parameters:
            new_password : unicode
                The new value of the password column
        """
        self._password = unicode(new_password)
    
    created = _date_prop('_created')
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

# Set up all Elixir entities declared above

setup_all()
random.seed() # make sure we have real randomness
