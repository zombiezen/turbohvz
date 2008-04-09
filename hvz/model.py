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
from turbogears.database import session

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['as_local',
           'as_utc',
           'to_local',
           'to_utc',
           'ModelError',
           'WrongStateError',
           'InvalidTimeError',
           'PlayerNotFoundError',
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
            # WEIRD BUG: SQLAlchemy gets cranky because it tries to compare the
            #            accessor value to the non-accessor value in an attempt
            #            to preserve history (thus comparing naive to aware).
            #            In order to get around this, we set the dates to None,
            #            flush it, then set it correctly.  Don't ask me why I
            #            need this.
            setattr(self, name, None)
            session.flush()
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
            The timezone to calculate dates in, defaulting to the config value
            of ``hvz.timezone``.  If you get the wrong timezone, your results
            will possibly be **very incorrect**.  This is because the algorithm
            should be looking at dates in the players' timezone, which is
            rarely UTC.
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
    datetime1, datetime2 = to_local(datetime1, tz), to_local(datetime2, tz)
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

### GAME LOGIC ERRORS ###

class ModelError(Exception):
    """
    Base class for model errors.
    
    Model errors usually occur when the players try to cheat, so try to catch
    these and display a friendly error message.
    
    :IVariables:
        game_object
            The game object raising the exception
        message : unicode
            The exception's message
    """
    def __init__(self, game_object, message=None):
        self.game_object = game_object
        if message is None:
            self.message = message
        else:
            self.message = unicode(message)
    
    def __repr__(self):
        cls_name = type(self).__name__
        cls_module = type(self).__module__
        type_name = cls_module + '.' + cls_name
        if self.message is None:
            return "%s(%r)" % (type_name, self.game_object)
        else:
            return "%s(%r, %r)" % (type_name, self.game_object, self.message)
    
    def __str__(self):
        return unicode(self).encode()
    
    def __unicode__(self):
        return self.message

class WrongStateError(ModelError):
    """
    Raised when an action takes place in the wrong state.
    
    :IVariables:
        current_state : int
            The state the object is in
        needed_state : int
            The state the object must be in to make the action valid
    """
    def __init__(self, game_object, current_state, needed_state, *args, **kw):
        super(WrongStateError, self).__init__(game_object, *args, **kw)
        self.current_state = current_state
        self.needed_state = needed_state
    
    def __repr__(self):
        return "hvz.model.WrongStateError(%r, %r, %r)" % (self.game_object,
                                                          self.current_state,
                                                          self.needed_state)
    
    def __unicode__(self):
        # Get message or default
        if self.message is None:
            msg = _("That action cannot be performed; it must be "
                    "%(needed_name)s (it is currently %(current_name)s).")
        else:
            msg = self.message
        # Get state names
        names = getattr(self.game_object, 'STATE_NAMES', {})
        current_name = names.get(self.current_state,
                                 unicode(self.current_state))
        needed_name = names.get(self.needed_state,
                                unicode(self.needed_state))
        # Format and return
        return msg % dict(game_object=self.game_object,
                          current=self.current_state,
                          needed=self.needed_state,
                          current_name=current_name,
                          needed_name=needed_name,)

class InvalidTimeError(ModelError):
    """
    Raised when an action happens at an invalid time (i.e. non-chronological
    kills).
    """

class PlayerNotFoundError(ModelError):
    """Raised when a player can't be found (i.e. an invalid GID is given)."""

### GAME LOGIC MODEL ###

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
    _starve_date = Field(DateTime,
                         colname='starve_date', synonym='starve_date')
    
    ## INITIALIZATION/RETRIEVING ##
    
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
        self.game = game
        self.player = player
        self.player_gid = self._generate_id(self.game.gid_length)
        self.original_pool = False
        self.reset()
    
    ## STRING REPRESENTATION ##
    
    def __repr__(self):
        return "<PlayerEntry %i:%s (%s)>" % (self.game.game_id,
                                             self.player_gid,
                                             self.player.user_name,)
    
    def __str__(self):
        return unicode(self).encode()
    
    def __unicode__(self):
        return unicode(self.player)
    
    ## ACTIONS ##
    
    def reset(self):
        """Reset volatile in-game statistics"""
        self.state = self.STATE_HUMAN
        self.death_date = None
        self.feed_date = None
        self.kills = 0
        self.killed_by = None
        self.starve_date = None
    
    def make_original_zombie(self, date=None):
        """
        Turn player into original zombie.
        
        If an already-original-zombie player has this called, then the death
        and feed date is refreshed.
        
        :Parameters:
            date : datetime.datetime
                The date and time of the infection
        """
        if date is None:
            date = as_utc(datetime.utcnow())
        if self.is_human:
            # This is the first time that the player became an OZ, give 'em the
            # full attribute setup
            self.state = self.STATE_ORIGINAL_ZOMBIE
            self.death_date = date
        elif self.state == self.STATE_ORIGINAL_ZOMBIE:
            self.death_date = date
        else:
            raise WrongStateError(self, self.state, self.STATE_HUMAN,
                                  _("Player cannot become the original "
                                    "zombie because player is non-human."))
    
    def kill(self, other, date=None):
        """
        Make the player zombify someone else.
        
        This only works for zombies.
        
        :Parameters:
            other : `PlayerEntry`
                The victim
            date : datetime.datetime
                The date and time of the demise
        """
        # Default the date
        if date is None:
            date = as_utc(datetime.utcnow())
        now = as_utc(datetime.utcnow())
        # Check if game is in-progress
        if not self.game.in_progress:
            raise WrongStateError(game, game.state, game.STATE_STARTED,
                                  _("Game is not in progress"))
        # Check for non-chronological reports
        if (self.death_date is not None and date <= self.death_date) or \
           (self.feed_date is not None and date <= self.feed_date):
            raise InvalidTimeError(self,
                                   _("You must report kills chronologically"))
        # Check if the demise is within the report window
        if now - date > self.game.zombie_report_timedelta:
            raise InvalidTimeError(self, _("Kill not within report window"))
        if not self.is_human:
            # Ensure the player didn't starve first
            starve_delta = self.calculate_time_since_last_feeding(date)
            if starve_delta > self.game.zombie_starve_timedelta:
                raise InvalidTimeError(self, _("Killer has already starved"))
            # Ensure that the victim is human
            if other.is_human:
                self.kills += 1
                self.feed_date = other.death_date = date
                other.state = other.STATE_ZOMBIE
                other.killed_by = self.player
            else:
                raise WrongStateError(self, self.state, self.STATE_HUMAN,
                                      _("Victim is nonhuman"))
        else:
            raise WrongStateError(self, self.state, self.STATE_ZOMBIE,
                                  _("Killer can't be human"))
    
    def starve(self, date=None):
        """
        Make the player die from starvation.
        
        This only works for zombies.
        
        :Parameters:
            date : datetime.datetime
                The date and time of the starvation
        """
        if date is None:
            date = as_utc(datetime.utcnow())
        if self.is_undead:
            self.starve_date = date
            self.state = self.STATE_DEAD
        else:
            raise WrongStateError(self, self.state, self.STATE_ZOMBIE,
                                  _("Humans can't starve"))
    
    def calculate_time_since_last_feeding(self, now=None):
        """
        Determine how much game time has elapsed since the last feeding.
        
        If the player has not fed yet (i.e. this is their first kill since
        becoming a zombie), then his or her death date is used for the
        calculation.
        
        :Parameters:
            now : datetime.datetime
                The date we're comparing to.  This may not actually be *now*.
                For example, this may be the time of a reported kill.
        :Returns: The amount of game time elapsed
        :ReturnType: timedelta
        """
        # Default date
        if now is None:
            now = as_utc(datetime.utcnow())
        # Check which date to compare
        if self.feed_date is None:
            feed_date = self.death_date
        else:
            feed_date = self.feed_date
        # Return result
        return self.game.calculate_timedelta(feed_date, now)
    
    def calculate_time_before_starving(self, now=None):
        """
        Calculates how much time is left before the player starves.
        
        If the player has not fed yet (i.e. this is their first kill since
        becoming a zombie), then his or her death date is used for the
        calculation.
        
        :Parameters:
            now : datetime.datetime
                The date we're comparing to.  This may not actually be *now*.
                For example, this may be the time of a reported kill.
        :Returns: The amount of game time until starvation
        :ReturnType: timedelta
        """
        return (self.game.zombie_starve_timedelta -
                self.calculate_time_since_last_feeding(now))
    
    def can_report_kill(self, now=None):
        """
        Checks whether the player is able to report a kill.
        
        :Parameters:
            now : datetime.datetime
                The time at which the act of reporting the kill is happening.
        :Returns: Whether the report is valid
        :ReturnType: bool
        """
        if self.is_human:
            # Humans can't (read as: shouldn't) kill people
            return False
        else:
            # Regardless of whether the game caught it yet, let's see how much
            # game time would have elapsed.
            duration = self.calculate_time_since_last_feeding(now)
            max_duration = (self.game.zombie_starve_timedelta +
                            self.game.zombie_report_timedelta)
            return bool(duration <= max_duration)
    
    ## PROPERTIES ##
    
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
        DEFAULT_ZOMBIE_STARVE_TIME : int
            The default number of hours before a zombie starves
        DEFAULT_ZOMBIE_REPORT_TIME : int
            The default number of hours that a zombie has to report a kill
        DEFAULT_GID_LENGTH : int
            The default length of a player GID (see `PlayerEntry.player_gid`)
    :IVariables:
        created : datetime.datetime
            The time at which the game was created
        started : datetime.datetime
            The time at which the game was started
        ended : datetime.datetime
            The time at which the game ended
        revealed_original_zombie : bool
            Whether the original zombie has been revealed
        in_progress : bool
            Whether the game is in-progress (i.e. after `STATE_STARTED` but
            before `STATE_ENDED`)
        registration_open : bool
            Whether registration is open
        state : int
            The current state of the game.  See the ``STATE_*`` class
            constants.
        is_first_state : bool
            Whether the current state is the first state
        is_last_state : bool
            Whether the current state is the last state
        entries : list of `PlayerEntry`
            A list of all the player entries in the game
        players : list of `User`
            A list of all the users participating in the game
        original_zombie_pool : list of `PlayerEntry`
            The players that want to be considered for the original zombie
        original_zombie : `PlayerEntry`
            The player that is acting as the original zombie for this game
        gid_length : int
            The length of each player's GID
        ignore_dates : frozenset of datetime.date
            Which dates to ignore for this game
        ignore_weekdays : frozenset of int
            Which weekdays (ISO weekday number) to ignore for this game
        zombie_starve_time : int
            The number of hours before a zombie starves.  If possible, rely on
            `zombie_starve_timedelta` (data abstraction and all).
        zombie_starve_timedelta : datetime.timedelta
            The duration before a zombie starves
        zombie_report_time : int
            The number of hours a zombie has to report a kill.  If possible,
            rely on `zombie_report_timedelta` (data abstraction and all).
        zombie_report_timedelta : datetime.timedelta
            The duration a zombie has to report a kill
    """
    using_options(tablename='game')
    
    STATE_CREATED = 0
    STATE_OPEN = 1
    STATE_CLOSED = 2
    STATE_CHOOSE_ZOMBIE = 3
    STATE_STARTED = 4
    STATE_REVEAL_ZOMBIE = 5
    STATE_ENDED = 6
    DEFAULT_ZOMBIE_STARVE_TIME = 48
    DEFAULT_ZOMBIE_REPORT_TIME = 3
    DEFAULT_GID_LENGTH = 16
    
    game_id = Field(Integer, primary_key=True)
    display_name = Field(Unicode(255))
    _created = Field(DateTime, colname='created', synonym='created')
    _started = Field(DateTime, colname='started', synonym='started')
    _ended = Field(DateTime, colname='ended', synonym='ended')
    state = Field(Integer)
    entries = OneToMany('PlayerEntry', inverse='game')
    _ignore_dates = Field(String(), colname='ignore_dates',
                          synonym='ignore_dates')
    _ignore_weekdays = Field(String(16), colname='ignore_weekdays',
                             synonym='ignore_weekdays')
    zombie_starve_time = Field(Integer)
    zombie_report_time = Field(Integer)
    gid_length = Field(Integer)
    
    ## INITIALIZATION/RETRIEVAL ##
    
    def __init__(self, name):
        self.display_name = name
        self.created = datetime.utcnow()
        self.started = None
        self.ended = None
        self.state = self.STATE_CREATED
        self.ignore_dates = []
        self.ignore_weekdays = []
        self.zombie_starve_time = self.DEFAULT_ZOMBIE_STARVE_TIME
        self.zombie_report_time = self.DEFAULT_ZOMBIE_REPORT_TIME
        self.gid_length = self.DEFAULT_GID_LENGTH
    
    ## STRING REPRESENTATION ##
    
    def __repr__(self):
        return "<Game %i (%s)>" % (self.game_id, self.display_name.encode())
    
    def __str__(self):
        return unicode(self).encode()
    
    def __unicode__(self):
        return self.display_name
    
    ## ACTIONS ##
    
    def update(self):
        # Hey, we're not playing.  Don't update!
        if not self.in_progress:
            return
        # Initialize variables
        now = as_utc(datetime.utcnow())
        # Bring out yer dead!
        zombies = (entry for entry in self.entries if entry.is_undead)
        for zombie in zombies:
            delta = zombie.calculate_time_since_last_feeding(now)
            if delta >= self.zombie_starve_timedelta:
                zombie.starve()
    
    def calculate_timedelta(self, datetime1, datetime2):
        """
        Calculates the delta between two datetimes.
        
        Along with subtracting the two dates, this removes time on ignored
        dates and weekdays.
        
        :Parameters:
            datetime1
                The first date and time
            datetime2
                The second date and time
        :Returns: The difference between the two dates
        :ReturnType: datetime.timedelta
        """
        return _calc_timedelta(datetime1, datetime2,
                               ignore_dates=self.ignore_dates,
                               ignore_weekdays=self.ignore_weekdays,)
    
    def previous_state(self):
        """Change to the previous state"""
        # Check if we can do this
        if self.is_first_state:
            raise WrongStateError(self, self.state, self.STATE_CREATED + 1,
                                  _("Game is already at the first state"))
        # Go previous state
        self.state -= 1
        # Do state hooks
        if self.state == self.STATE_STARTED - 1:
            self.started = None
        elif self.state == self.STATE_ENDED - 1:
            self.ended = None
        elif self.state == self.STATE_CHOOSE_ZOMBIE - 1:
            for entry in self.entries:
                entry.reset()
    
    def next_state(self):
        """Change to the next state"""
        # Check if we can do this
        if self.is_last_state:
            raise WrongStateError(self, self.state, self.STATE_ENDED - 1,
                                  _("The game is already over"))
        # Go next state
        self.state += 1
        # Do state hooks
        if self.state == self.STATE_STARTED:
            self.started = as_utc(datetime.utcnow())
            self.original_zombie.make_original_zombie() # Refresh kill date
        elif self.state == self.STATE_ENDED:
            self.ended = as_utc(datetime.utcnow())
    
    ## PROPERTIES ##
    
    @property
    def zombie_starve_timedelta(self):
        return timedelta(hours=self.zombie_starve_time)
    
    @property
    def zombie_report_timedelta(self):
        return timedelta(hours=self.zombie_report_time)
    
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
    
    def _get_oz(self):
        results = [entry for entry in self.entries
                   if entry.state == PlayerEntry.STATE_ORIGINAL_ZOMBIE]
        if len(results) == 0:
            return None
        elif len(results) == 1:
            return results[0]
        else:
            raise AssertionError("We have multiple OZs")
    
    def _set_oz(self, new_oz):
        prev_oz = self._get_oz()
        if prev_oz is not None:
            prev_oz.reset()
        new_oz.make_original_zombie()
    
    def _get_ignore_dates(self):
        from datetime import date
        value = self._ignore_dates
        if value is None:
            return frozenset()
        else:
            components = value.split(';')
            result = []
            for component in components:
                parts = [int(part, 10) for part in component.split('-')]
                assert len(parts) == 3
                new_date = date(parts[0], parts[1], parts[2])
                result.append(new_date)
            return frozenset(result)
    
    def _set_ignore_dates(self, value):
        if value is None:
            self._ignore_dates = None
        else:
            date2str = (lambda d: u'%.4i-%.2i-%.2i' % (d.year, d.month, d.day))
            components = frozenset(date2str(date) for date in value)
            self._ignore_dates = ';'.join(components)
    
    def _get_ignore_weekdays(self):
        value = self._ignore_weekdays
        if value is None:
            return frozenset()
        else:
            components = value.split(';')
            result = [int(component, 10) for component in components]
            return frozenset(result)
    
    def _set_ignore_weekdays(self, value):
        if value is None:
            self._ignore_weekdays = None
        else:
            value = frozenset(value)
            if not frozenset(xrange(1, 8)).issuperset(value):
                raise ValueError("ignore_weekdays only accepts [1,7] ints")
            self._ignore_weekdays = ';'.join(str(i) for i in value)
    
    created = _date_prop('_created')
    started = _date_prop('_started')
    ended = _date_prop('_ended')
    original_zombie = property(_get_oz, _set_oz)
    ignore_dates = property(_get_ignore_dates, _set_ignore_dates)
    ignore_weekdays = property(_get_ignore_weekdays, _set_ignore_weekdays)

### IDENTITY ###

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
