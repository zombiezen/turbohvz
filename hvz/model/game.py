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

"""Gameplay-specific data objects"""

from datetime import timedelta
import random
import string

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
__date__ = 'April 18, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['PlayerEntry',
           'Game',]

## TABLES ##
entries_table = Table('entries', metadata,
    Column('entry_id', Integer, primary_key=True),
    Column('player_id', Integer, ForeignKey('tg_user.user_id',
           ondelete='RESTRICT', onupdate='CASCADE'), index=True),
    Column('game_id', Integer, ForeignKey('game.game_id',
           ondelete='CASCADE', onupdate='CASCADE'), index=True),
    Column('player_gid', String(128)),
    Column('state', Integer),
    Column('death_date', DateTime),
    Column('feed_date', DateTime),
    Column('starve_date', DateTime),
    Column('kills', Integer),
    Column('killer_id', Integer, ForeignKey('tg_user.user_id',
           ondelete='RESTRICT', onupdate='CASCADE')),
    Column('original_pool', Boolean),
    Column('notify_sms', Boolean),
    # Constraints
    UniqueConstraint('game_id', 'player_gid'),
    UniqueConstraint('game_id', 'player_id'),
)

games_table = Table('game', metadata,
    Column('game_id', Integer, primary_key=True),
    Column('display_name', Unicode(255)),
    Column('created', DateTime),
    Column('started', DateTime),
    Column('ended', DateTime),
    Column('state', Integer),
    Column('ignore_dates', String(2048)),
    Column('ignore_weekdays', String(16)),
    Column('zombie_starve_time', Integer),
    Column('zombie_report_time', Integer),
    Column('human_undead_time', Integer),
    Column('gid_length', Integer),
    Column('safe_zones', Unicode(2048)),
    Column('rules_notes', Unicode(4096)),
)

## CLASSES ##

class PlayerEntry(object):
    """
    Per-game player statistics.
    
    :CVariables:
        STATE_ORIGINAL_ZOMBIE : int
            The constant for the original zombie state
        STATE_ZOMBIE : int
            The constant for a non-original zombie state
        STATE_DEAD : int
            The constant for a starved zombie state
        STATE_DEAD_OZ : int
            The constant for the original zombie starved state
        STATE_HUMAN : int
            The constant for a healthy human state
        STATE_INFECTED : int
            The constant for a human who has been tagged state
        STATE_NAMES : dict of {int: unicode}
            State-to-human-readable-name lookup table
        STATE_INTERNAL_NAMES : dict of {int: unicode}
            State-to-administrator-readable-name lookup table
    :IVariables:
        entry_id : int
            The entry's database identifier
        player : `identity.User`
            The player this is associated with
        game : `Game`
            The game associated
        player_gid : str
            In-game player identifier (Player Game Identifier)
        state : int
            The player's current state (see the ``STATE_*`` constants)
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
        notify_sms : bool
            Whether the user wants to be notified by text message when the game
            is updated
        affiliation : unicode
            A human-readable name for the player's state
        is_undead : bool
            Whether the player is a zombie
        is_human : bool
            Whether the player is human
        is_dead : bool
            Whether the player has starved
        is_original_zombie : bool
            Whether the player is the original zombie
        is_infected : bool
            Whether the player is currently infected
        survival_time : datetime.timedelta
            The amount of time the player has survived for this game
        undead_time : datetime.timedelta
            The amount of time the player has been a zombie for this game
    :See: identity.User
    """
    STATE_ORIGINAL_ZOMBIE = -2
    STATE_ZOMBIE = -1
    STATE_DEAD = 0
    STATE_DEAD_OZ = -3
    STATE_HUMAN = 1
    STATE_INFECTED = 2
    STATE_NAMES = {STATE_ORIGINAL_ZOMBIE: _("Original zombie"),
                   STATE_ZOMBIE: _("Zombie"),
                   STATE_DEAD: _("Dead"),
                   STATE_DEAD_OZ: _("Dead"),
                   STATE_HUMAN: _("Human"),
                   STATE_INFECTED: _("Infected"),}
    STATE_INTERNAL_NAMES = {STATE_ORIGINAL_ZOMBIE: _("Original zombie"),
                            STATE_ZOMBIE: _("Zombie"),
                            STATE_DEAD: _("Dead"),
                            STATE_DEAD_OZ: _("Dead (Original Zombie)"),
                            STATE_HUMAN: _("Human"),
                            STATE_INFECTED: _("Infected"),}
    
    ## INITIALIZATION/RETRIEVING ##
    
    @staticmethod
    def _generate_id(id_length):
        id_chars = string.ascii_uppercase + string.digits
        # Remove "O"s (zeros are better)
        id_chars = id_chars.replace('O', '')
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
        self.notify_sms = False
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
        else:
            date = make_aware(date)
        if self.is_human:
            # This is the first time that the player became an OZ, give 'em the
            # full attribute setup
            self.state = self.STATE_ORIGINAL_ZOMBIE
            self.death_date = date
        elif self.is_original_zombie:
            self.death_date = date
        else:
            raise WrongStateError(self, self.state, self.STATE_HUMAN,
                                  _("Player cannot become the original "
                                    "zombie because player is non-human."))
    
    def kill(self, other, date=None, report_time=None):
        """
        Make the player zombify someone else.
        
        This only works for zombies.
        
        :Parameters:
            other : `PlayerEntry`
                The victim
            date : datetime.datetime
                The date and time of the demise
            report_time : datetime.datetime
                The date and time that the kill was reported
        """
        # Default the date
        if date is None:
            date = now()
        else:
            date = make_aware(date)
        if report_time is None:
            report_time = now()
        else:
            report_time = make_aware(report_time)
        # Check for human trying to kill
        if not (self.is_undead or self.is_dead):
            raise WrongStateError(self, self.state, self.STATE_ZOMBIE,
                                  _("Killer must be zombie"))
        # Check for reports in the future
        if date > report_time:
            raise InvalidTimeError(self,
                                   _("You cannot kill someone in the future"))
        # Check if game is in-progress
        if not self.game.in_progress:
            raise WrongStateError(self.game, self.game.state, 
                                  self.game.STATE_STARTED,
                                  _("Game is not in progress"))
        # Check for non-chronological reports
        if (self.death_date is not None and date <= self.death_date) or \
           (self.feed_date is not None and date <= self.feed_date):
            raise InvalidTimeError(self,
                                   _("You must report kills chronologically"))
        # Check if the demise is within the report window
        if report_time - date > self.game.zombie_report_timedelta:
            raise InvalidTimeError(self, _("Kill not within report window"))
        # Ensure the player didn't starve first
        starve_delta = self.calculate_time_since_last_feeding(date)
        if starve_delta > self.game.zombie_starve_timedelta:
            raise InvalidTimeError(self, _("Killer has already starved"))
        # Ensure that the victim is human
        if not other.is_human:
            raise WrongStateError(other, other.state, other.STATE_HUMAN,
                                  _("Victim must be human"))
        # Now we're ready to kill
        self.kills += 1
        self.feed_date = date
        other.death_date = date + self.game.human_undead_timedelta
        other.state = other.STATE_INFECTED
        other.killed_by = self.player
        if self.is_dead:
            self.starve_date = None
            if self.is_original_zombie:
                self.state = self.STATE_ORIGINAL_ZOMBIE
            else:
                self.state = self.STATE_ZOMBIE
    
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
        else:
            date = make_aware(date)
        # Check if game is in-progress
        if not self.game.in_progress:
            raise WrongStateError(self.game, self.game.state, 
                                  self.game.STATE_STARTED,
                                  _("Game is not in progress"))
        # Starve, if we can
        if not self.is_undead:
            raise WrongStateError(self, self.state, self.STATE_ZOMBIE,
                                  _("Non-zombies can't starve"))
        self.starve_date = date
        if self.is_original_zombie:
            self.state = self.STATE_DEAD_OZ
        else:
            self.state = self.STATE_DEAD
    
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
        else:
            time = make_aware(time)
        # Check which date to compare
        if self.feed_date is None:
            feed_date = self.death_date
        else:
            feed_date = self.feed_date
        # If we haven't actually died yet, return zero
        if time <= feed_date:
            return timedelta()
        else:
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
        :ReturnType: datetime.timedelta
        """
        return (self.game.zombie_starve_timedelta -
                self.calculate_time_since_last_feeding(time))
    
    def calculate_starve_time(self, time=None):
        """
        Calculates when the zombie will starve.
        
        This calculation is a projection; if the zombie feeds before this time,
        the starve time will be extended.
        
        If the player has not fed yet (i.e. this is their first kill since
        becoming a zombie), then his or her death date is used for the
        calculation.
        
        :Parameters:
            time : datetime.datetime
                The date we're comparing to.  This may not actually be *now*.
                For example, this may be the time of a reported kill.
        :Returns: The time when the zombie will starve
        :ReturnType: datetime.datetime
        """
        # Default date
        if time is None:
            time = now()
        else:
            time = make_aware(time)
        # Check which date to compare
        if self.feed_date is None:
            feed_date = self.death_date
        else:
            feed_date = self.feed_date
        starve_delta = self.game.zombie_starve_timedelta
        return self.game.calculate_addtimedelta(feed_date, starve_delta)
    
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
        else:
            time = make_aware(time)
        if self.is_human:
            # Humans can't (read as: shouldn't) kill people
            return False
        elif self.is_infected:
            # Player is being infected, but can't kill yet
            return False
        else:
            # Regardless of whether the game caught it yet, let's see how much
            # game time would have elapsed.
            duration = self.calculate_time_since_last_feeding(time)
            max_duration = (self.game.zombie_starve_timedelta +
                            self.game.zombie_report_timedelta)
            return bool(duration <= max_duration)
    
    def delete(self):
        """
        Properly deletes the entry.
        
        Use this method instead of ``session.delete``, as this will properly
        remove all references from the database.
        """
        self.game.entries.remove(self)
        self.player.entries.remove(self)
        session.delete(self)
    
    def force_to_human(self, time=None):
        """
        Force the player to become human.
        
        :Parameters:
            time : datetime.datetime
                The time at which they are being forced.  Defaults to now.
        """
        if time is None:
            time = now()
        else:
            time = make_aware(time)
        self.reset()
    
    def force_to_infected(self, time=None):
        """
        Force the player to become infected.
        
        :Parameters:
            time : datetime.datetime
                The time at which they are being forced.  Defaults to now.
        """
        if time is None:
            time = now()
        else:
            time = make_aware(time)
        if self.is_infected:
            return
        # Infection is inherently a human condition, so we can lose any kill
        # information.
        self.reset()
        self.death_date = time + self.game.human_undead_timedelta
        self.state = self.STATE_INFECTED
    
    def force_to_zombie(self, time=None):
        """
        Force the player to become undead.
        
        :Parameters:
            time : datetime.datetime
                The time at which they are being forced.  Defaults to now.
        """
        if time is None:
            time = now()
        else:
            time = make_aware(time)
        if self.is_undead:
            pass
        elif self.is_human or self.is_infected:
            self.death_date = time
            self.state = self.STATE_ZOMBIE
        elif self.is_dead:
            if self.calculate_starve_time() <= time:
                # Renew the zombie's "life"
                self.feed_date = time
            self.starve_date = None
            if self.is_original_zombie:
                self.state = self.STATE_ORIGINAL_ZOMBIE
            else:
                self.state = self.STATE_ZOMBIE
        else:
            raise AssertionError("Unknown state when forced to zombie")
    
    def force_to_dead(self, time=None):
        """
        Force the player to become dead.
        
        :Parameters:
            time : datetime.datetime
                The time at which they are being forced.  Defaults to now.
        """
        if time is None:
            time = now()
        else:
            time = make_aware(time)
        if not self.is_dead:
            if self.death_date is None or self.death_date > time:
                self.death_date = time
            self.starve_date = time
            if self.is_original_zombie:
                self.state = self.STATE_DEAD_OZ
            else:
                self.state = self.STATE_DEAD
    
    ## PROPERTIES ##
    
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
        return self.state in (self.STATE_DEAD, self.STATE_DEAD_OZ)
    
    @property
    def is_original_zombie(self):
        return self.state in (self.STATE_ORIGINAL_ZOMBIE, self.STATE_DEAD_OZ)
    
    @property
    def is_infected(self):
        return self.state == self.STATE_INFECTED
    
    @property
    def survival_time(self):
        if self.is_human or self.is_original_zombie:
            return None
        else:
            return self.game.calculate_timedelta(self.game.started,
                                                 self.death_date)
    
    @property
    def undead_time(self):
        if self.is_human:
            return None
        elif self.is_undead or self.is_infected:
            if self.game.in_progress or (self.death_date > self.game.ended):
                return None
            else:
                return self.game.calculate_timedelta(self.death_date,
                                                     self.game.ended)
        elif self.is_dead:
            return self.game.calculate_timedelta(self.death_date,
                                                 self.starve_date)
        else:
            raise AssertionError("I don't know how to calculate undead time")
    
    death_date = date_prop('_death_date')
    feed_date = date_prop('_feed_date')
    starve_date = date_prop('_starve_date')

class Game(object):
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
        DEFAULT_HUMAN_UNDEAD_TIME : int
            The default number of minutes it takes to turn a human into a
            zombie
        DEFAULT_GID_LENGTH : int
            The default length of a player GID (see `PlayerEntry.player_gid`)
        DEFAULT_SAFE_ZONES : list of unicode
            The default safe zones
    :IVariables:
        game_id : int
            The database identifier for the game
        display_name : unicode
            The human-readable name for the game
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
        human_undead_time : int
            The number of minutes it takes to turn a human into a zombie.  If
            possible, rely on `human_undead_timedelta` (data abstraction and
            all).
        human_undead_timedelta : datetime.timedelta
            The duration it takes to turn a human into a zombie
        safe_zones : list of unicode
            Safe zones
        rules_notes : unicode
            Extra notes for the rules
    """
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
    DEFAULT_HUMAN_UNDEAD_TIME = 60
    DEFAULT_GID_LENGTH = 16
    DEFAULT_SAFE_ZONES = [_("Dorm rooms"),
                          _("Bathrooms"),
                          _("Academic buildings"),
                          _("Library"),
                          _("SRC"),
                          _("Health center"),
                          _("Dining halls"),]
    
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
        self.human_undead_time = self.DEFAULT_HUMAN_UNDEAD_TIME
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
    
    def update(self, update_time=None):
        """
        Update the game state.
        
        :Parameters:
            update_time : datetime.datetime
                The time at which the update commenced.  Defaults to now.
        """
        if update_time is None:
            update_time = now()
        else:
            update_time = make_aware(update_time)
        session.flush()
        # Hey, we're not playing.  Don't update!
        if not self.in_progress:
            return
        # Update
        self._update_check_zombie_win(update_time)
        if self.in_progress:
            self._update_infected(update_time)
            self._update_starved(update_time)
            self._update_check_human_win(update_time)
    
    def _update_starved(self, update_time):
        """
        Find zombies who have gone past their feeding time and starve them.
        
        Bring out yer dead!
        
        :Parameters:
            update_time : datetime.datetime
                The time at which the update commenced
        """
        zombies = (entry for entry in self.entries if entry.is_undead)
        for zombie in zombies:
            delta = zombie.calculate_time_since_last_feeding(update_time)
            if delta >= self.zombie_starve_timedelta:
                zombie.starve(zombie.calculate_starve_time())
        session.flush()
    
    def _update_infected(self, update_time):
        """
        Find infected who have become zombies and zombify them.
        
        :Parameters:
            update_time : datetime.datetime
                The time at which the update commenced
        """
        from sqlalchemy import and_
        infected = PlayerEntry.query.filter(
            and_(PlayerEntry.game == self,
                 PlayerEntry.state == PlayerEntry.STATE_INFECTED))
        for player in infected:
            if update_time >= player.death_date:
                player.state = PlayerEntry.STATE_ZOMBIE
        session.flush()
    
    def _update_check_zombie_win(self, update_time):
        """
        Checks if the humans have expired, and if necessary, forcibly end the
        game.
        
        :Parameters:
            update_time : datetime.datetime
                The time at which the update commenced
        """
        from sqlalchemy import or_
        players = PlayerEntry.query.filter_by(game=self)
        humans = players.filter_by(state=PlayerEntry.STATE_HUMAN)
        if humans.count() == 0:
            zombies = players.filter(
                or_(PlayerEntry.state == PlayerEntry.STATE_ZOMBIE,
                    PlayerEntry.state == PlayerEntry.STATE_ORIGINAL_ZOMBIE,
                    PlayerEntry.state == PlayerEntry.STATE_INFECTED))
            ultimate_end = max(zombie.death_date for zombie in zombies)
            self.end(ultimate_end)
    
    def _update_check_human_win(self, update_time):
        """
        Checks if the zombies have died, and if necessary, forcibly end the
        game.
        
        :Parameters:
            update_time : datetime.datetime
                The time at which the update commenced
        """
        from sqlalchemy import or_
        # Fetch the different groups
        players = PlayerEntry.query.filter(PlayerEntry.game == self)
        zombies = players.filter(
            or_(PlayerEntry.state == PlayerEntry.STATE_ZOMBIE,
                PlayerEntry.state == PlayerEntry.STATE_ORIGINAL_ZOMBIE,
                PlayerEntry.state == PlayerEntry.STATE_INFECTED,))
        dead = players.filter(
            or_(PlayerEntry.state == PlayerEntry.STATE_DEAD,
                PlayerEntry.state == PlayerEntry.STATE_DEAD_OZ))
        # Now determine whether we should end the game
        # The two closing scenarios:
        #   1. Humans have all died.
        #   2. Zombies have all starved and there are humans left.
        if zombies.count() == 0:
            # Zombies appear to have died off...
            # But there may still be dead ones who can report a kill.
            for corpse in dead:
                if corpse.can_report_kill(update_time):
                    # Someone could still report a kill!
                    break
            else:
                ultimate_end = max(corpse.starve_date for corpse in dead)
                self.end(ultimate_end)
    
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
    
    def calculate_addtimedelta(self, dt, delta):
        """
        Calculates the date after a delta.
        
        Along with adding the two dates, this adds time on specific dates and
        weekdays.
        
        :Parameters:
            dt
                The date and time
            delta
                The delta
        :Returns: The date with the delta added
        :ReturnType: datetime.datetime
        """
        return calc_addtimedelta(dt, delta,
                                 ignore_dates=self.ignore_dates,
                                 ignore_weekdays=self.ignore_weekdays,)
    
    def previous_state(self, time=None):
        """
        Change to the previous state
        
        :Parameters:
            time : datetime.datetime
                The date when we go to the previous state.  This may not
                actually be *now*.
        """
        if time is None:
            time = now()
        else:
            time = make_aware(time)
        # Check if we can do this
        if self.is_first_state:
            raise WrongStateError(self, self.state, self.STATE_CREATED + 1,
                                  _("Game is already at the first state"))
        # Go previous state
        self.state -= 1
        # Do state hooks
        prev_state = self.state + 1
        if prev_state == self.STATE_STARTED:
            self.started = None
        elif prev_state == self.STATE_ENDED:
            self.ended = None
        elif prev_state == self.STATE_CHOOSE_ZOMBIE:
            for entry in self.entries:
                entry.reset()
    
    def next_state(self, time=None):
        """
        Change to the next state
        
        :Parameters:
            time : datetime.datetime
                The date when we go to the next state.  This may not actually
                be *now*.
        """
        from sqlalchemy import or_
        if time is None:
            time = now()
        else:
            time = make_aware(time)
        # Check if we can do this
        if self.is_last_state:
            raise WrongStateError(self, self.state, self.STATE_ENDED - 1,
                                  _("The game is already over"))
        # Go next state
        self.state += 1
        # Do state hooks
        if self.state == self.STATE_STARTED:
            self.started = time
            self.original_zombie.make_original_zombie(time) # Refresh kill date
        elif self.state == self.STATE_ENDED:
            self.ended = time
            # Resurrect those who haven't actually starved
            players = PlayerEntry.query.filter(PlayerEntry.game == self)
            dead = players.filter(
                or_(PlayerEntry.state == PlayerEntry.STATE_DEAD,
                    PlayerEntry.state == PlayerEntry.STATE_DEAD_OZ))
            for corpse in dead:
                if corpse.starve_date > self.ended:
                    corpse.force_to_zombie(self.ended)
    
    def end(self, end_time=None):
        """
        Terminates the game, if it's in-progress.
        
        This method *shouldn't* normally be called outside the class.  It's
        mostly just used to encapsulate everything necessary to end the game
        when `update` thinks the game is over or when the administrator forces
        the game's end through `next_state`.
        
        :Parameters:
            end_time : datetime.datetime
                The date we're reporting it ended.  This may not actually
                be *now*.
        :Raises errors.WrongStateError: If the game is not in-progress.
        """
        if end_time is None:
            end_time = now()
        else:
            end_time = make_aware(end_time)
        # Ensure we can end now
        if not self.in_progress:
            raise WrongStateError(self, self.state, self.STATE_STARTED,
                                  _("The game cannot be ended right now %i"))
        # Advance state
        while self.state < self.STATE_ENDED:
            self.next_state(end_time)
    
    def delete(self):
        """
        Properly deletes the game.
        
        Use this method instead of ``session.delete``, as this will properly
        remove all entries from the database.
        """
        for entry in list(self.entries):
            entry.delete()
        session.delete(self)
    
    ## PROPERTIES ##
    
    @property
    def zombie_starve_timedelta(self):
        return timedelta(hours=self.zombie_starve_time)
    
    @property
    def zombie_report_timedelta(self):
        return timedelta(hours=self.zombie_report_time)
    
    @property
    def human_undead_timedelta(self):
        return timedelta(minutes=self.human_undead_time)
    
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
        results = [entry for entry in self.entries if entry.is_original_zombie]
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
        if value:
            components = value.split(';')
            result = []
            for component in components:
                parts = [int(part, 10) for part in component.split('-')]
                assert len(parts) == 3
                new_date = date(parts[0], parts[1], parts[2])
                result.append(new_date)
            return frozenset(result)
        else:
            return frozenset()
    
    def _set_ignore_dates(self, value):
        if value is None:
            self._ignore_dates = None
        else:
            date2str = (lambda d: u'%.4i-%.2i-%.2i' % (d.year, d.month, d.day))
            components = frozenset(date2str(date) for date in value)
            self._ignore_dates = ';'.join(components)
    
    def _get_ignore_weekdays(self):
        value = self._ignore_weekdays
        if value:
            components = value.split(';')
            result = [int(component, 10) for component in components]
            return frozenset(result)
        else:
            return frozenset()
    
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

### MAPPERS ###

mapper(PlayerEntry, entries_table, properties={
    'player':
       relation(identity.User,
                primaryjoin=(entries_table.c.player_id ==
                             identity.users_table.c.user_id),
                uselist=False,
                backref=backref('entries',
                                primaryjoin=(entries_table.c.player_id ==
                                             identity.users_table.c.user_id),
                                uselist=True)),
    'killed_by':
        relation(identity.User,
                 primaryjoin=(entries_table.c.killer_id ==
                              identity.users_table.c.user_id),
                 uselist=False),
    'death_date': synonym('_death_date', map_column=True),
    'feed_date': synonym('_feed_date', map_column=True),
    'starve_date': synonym('_starve_date', map_column=True),
})

mapper(Game, games_table, properties={
    'created': synonym('_created', map_column=True),
    'started': synonym('_started', map_column=True),
    'ended': synonym('_ended', map_column=True),
    'entries': relation(PlayerEntry, backref='game',
                        cascade='all, delete, delete-orphan'),
    'ignore_dates': synonym('_ignore_dates', map_column=True),
    'ignore_weekdays': synonym('_ignore_weekdays', map_column=True),
    'safe_zones': synonym('_safe_zones', map_column=True),
})
