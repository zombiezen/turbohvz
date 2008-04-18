#!/usr/bin/env python
#
#   model/game.py
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

from datetime import timedelta
import random
import string

import pkg_resources
pkg_resources.require("SQLAlchemy>=0.3.10")
pkg_resources.require("Elixir>=0.4.0")

from elixir import (Entity, Field, OneToMany, ManyToOne, ManyToMany,
                    options_defaults, using_options,
                    using_table_options, setup_all,
                    String, Unicode, Integer, Boolean, DateTime)
from sqlalchemy import UniqueConstraint
from turbogears.database import session

from hvz.model.dates import now, date_prop, calc_timedelta
from hvz.model.errors import WrongStateError, InvalidTimeError

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['PlayerEntry',
           'Game',]

options_defaults['autosetup'] = False

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
        player : `identity.User`
            The player this is associated with
        game : `Game`
            The game associated
        player_gid : str
            In-game player identifier (Player Game Identifier)
        state : int
            -1 is zombie, -2 is original zombie, 0 is dead, 1 is human (-3 and
            2 are mysteries)
        death_date : datetime.datetime
            When the player died (tagged by zombie)
        feed_date : datetime.datetime
            Last time fed
        kills : int
            How many humans tagged
        killed_by : `identity.User`
            Who killed the user
        original_pool : bool
            Whether the user wants to be considered for being the original
            zombie
        starve_date : datetime.datetime
            When the player starved
    :See: identity.User
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
    player = ManyToOne('hvz.model.identity.User',
                       colname='player_id', inverse='entries')
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
            date = now()
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
            date = now()
        report_time = now()
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
        if report_time - date > self.game.zombie_report_timedelta:
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
            date = now()
        if self.is_undead:
            self.starve_date = date
            self.state = self.STATE_DEAD
        else:
            raise WrongStateError(self, self.state, self.STATE_ZOMBIE,
                                  _("Humans can't starve"))
    
    def calculate_time_since_last_feeding(self, time=None):
        """
        Determine how much game time has elapsed since the last feeding.
        
        If the player has not fed yet (i.e. this is their first kill since
        becoming a zombie), then his or her death date is used for the
        calculation.
        
        :Parameters:
            time : datetime.datetime
                The date we're comparing to.  This may not actually be *now*.
                For example, this may be the time of a reported kill.
        :Returns: The amount of game time elapsed
        :ReturnType: timedelta
        """
        # Default date
        if time is None:
            time = now()
        # Check which date to compare
        if self.feed_date is None:
            feed_date = self.death_date
        else:
            feed_date = self.feed_date
        # Return result
        return self.game.calculate_timedelta(feed_date, time)
    
    def calculate_time_before_starving(self, time=None):
        """
        Calculates how much time is left before the player starves.
        
        If the player has not fed yet (i.e. this is their first kill since
        becoming a zombie), then his or her death date is used for the
        calculation.
        
        :Parameters:
            time : datetime.datetime
                The date we're comparing to.  This may not actually be *now*.
                For example, this may be the time of a reported kill.
        :Returns: The amount of game time until starvation
        :ReturnType: timedelta
        """
        return (self.game.zombie_starve_timedelta -
                self.calculate_time_since_last_feeding(time))
    
    def can_report_kill(self, time=None):
        """
        Checks whether the player is able to report a kill.
        
        :Parameters:
            time : datetime.datetime
                The time at which the act of reporting the kill is happening.
        :Returns: Whether the report is valid
        :ReturnType: bool
        """
        if time is None:
            time = now()
        if self.is_human:
            # Humans can't (read as: shouldn't) kill people
            return False
        else:
            # Regardless of whether the game caught it yet, let's see how much
            # game time would have elapsed.
            duration = self.calculate_time_since_last_feeding(time)
            max_duration = (self.game.zombie_starve_timedelta +
                            self.game.zombie_report_timedelta)
            return bool(duration <= max_duration)
    
    ## PROPERTIES ##
    
    def _get_killed_by(self):
        from hvz.model.identity import User
        value = self._killed_by
        if value is None:
            return None
        else:
            return User.get(value)
    
    def _set_killed_by(self, new_killer):
        from hvz.model.identity import User
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
    
    death_date = date_prop('_death_date')
    feed_date = date_prop('_feed_date')
    starve_date = date_prop('_starve_date')
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
        STATE_NAMES : dict of {int: unicode}
            State-to-human-readable-name lookup table
        DEFAULT_ZOMBIE_STARVE_TIME : int
            The default number of hours before a zombie starves
        DEFAULT_ZOMBIE_REPORT_TIME : int
            The default number of hours that a zombie has to report a kill
        DEFAULT_GID_LENGTH : int
            The default length of a player GID (see `PlayerEntry.player_gid`)
        DEFAULT_SAFE_ZONES : list of unicode
            The default safe zones
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
        players : list of `identity.User`
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
        safe_zones : list of unicode
            Safe zones
        rules_notes : unicode
            Extra notes for the rules
    """
    using_options(tablename='game')
    
    STATE_CREATED = 0
    STATE_OPEN = 1
    STATE_CLOSED = 2
    STATE_CHOOSE_ZOMBIE = 3
    STATE_STARTED = 4
    STATE_REVEAL_ZOMBIE = 5
    STATE_ENDED = 6
    STATE_NAMES = {STATE_CREATED: _("Game created"),
                   STATE_OPEN: _("Open registration"),
                   STATE_CLOSED: _("Closed registration"),
                   STATE_CHOOSE_ZOMBIE: _("Choose original zombie"),
                   STATE_STARTED: _("Started game"),
                   STATE_REVEAL_ZOMBIE: _("Revealed original zombie"),
                   STATE_ENDED: _("Game ended"),}
    DEFAULT_ZOMBIE_STARVE_TIME = 48
    DEFAULT_ZOMBIE_REPORT_TIME = 3
    DEFAULT_GID_LENGTH = 16
    DEFAULT_SAFE_ZONES = [_("Bathrooms"),
                          _("Academic buildings"),
                          _("Library"),
                          _("Student center"),
                          _("Health center"),
                          _("Dining halls"),]
    
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
    _safe_zones = Field(Unicode(2048), 
                        colname='safe_zones', synonym='safe_zones')
    rules_notes = Field(Unicode(4096))
    
    ## INITIALIZATION/RETRIEVAL ##
    
    def __init__(self, name):
        self.display_name = name
        self.created = now()
        self.started = None
        self.ended = None
        self.state = self.STATE_CREATED
        self.ignore_dates = []
        self.ignore_weekdays = []
        self.zombie_starve_time = self.DEFAULT_ZOMBIE_STARVE_TIME
        self.zombie_report_time = self.DEFAULT_ZOMBIE_REPORT_TIME
        self.gid_length = self.DEFAULT_GID_LENGTH
        self.safe_zones = self.DEFAULT_SAFE_ZONES
        self.rules_notes = None
    
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
        update_time = now()
        # Bring out yer dead!
        zombies = (entry for entry in self.entries if entry.is_undead)
        for zombie in zombies:
            delta = zombie.calculate_time_since_last_feeding(update_time)
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
        return calc_timedelta(datetime1, datetime2,
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
            self.started = now()
            self.original_zombie.make_original_zombie() # Refresh kill date
        elif self.state == self.STATE_ENDED:
            self.ended = now()
    
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
    
    def _get_safe_zones(self):
        value = self._safe_zones
        if value is None:
            return []
        else:
            lines = value.splitlines()
            return [line.strip() for line in lines]
    
    def _set_safe_zones(self, value):
        if value is None:
            self._safe_zones = None
        else:
            self._safe_zones = '\n'.join(unicode(zone).strip()
                                         for zone in value)
    
    created = date_prop('_created')
    started = date_prop('_started')
    ended = date_prop('_ended')
    original_zombie = property(_get_oz, _set_oz)
    ignore_dates = property(_get_ignore_dates, _set_ignore_dates)
    ignore_weekdays = property(_get_ignore_weekdays, _set_ignore_weekdays)
    safe_zones = property(_get_safe_zones, _set_safe_zones)
