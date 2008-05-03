#!/usr/bin/env python
#
#   test_model.py
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

"""Test model objects and database"""

# If your project uses a database, you can set up database tests
# similar to what you see below. Be sure to set the db_uri to
# an appropriate uri for your testing database. sqlite is a good
# choice for testing, because you can use an in-memory database
# which is very fast.

from datetime import date, datetime, timedelta
import unittest

from turbogears import testutil, database
from turbogears.database import metadata, session
from turbogears.util import get_model

from hvz import model
from hvz.model.dates import as_local, as_utc

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__all__ = []

database.set_db_uri("sqlite:///:memory:")

class SADBTest(unittest.TestCase):
    model = None
    
    def setUp(self):
        # Make sure engine is active
        database.bind_meta_data()
        # Import model
        if not self.model:
            self.model = get_model()
            if not self.model:
                raise RuntimeError("Unable to run database tests without a "
                                   "model")
        # Create all model tables
        metadata.create_all(checkfirst=True)
    
    def tearDown(self):
        # Flush commands for a clean deletion
        session.flush()
        # Drop all model tables
        database.metadata.drop_all(checkfirst=True)

class TestUser(SADBTest):
    def test_creation(self):
        """User creation should set all necessary attributes"""
        obj = model.identity.User(u"creosote", u"Mr Creosote",
                                  u"spam@python.not", u"Wafer-thin Mint")
        assert obj.user_name == "creosote", "Wrong internal name"
        assert obj.display_name == "Mr Creosote", "Wrong display name"
        assert obj.email_address == "spam@python.not", "Wrong email address"
    
    def test_created_timezone(self):
        """User creation date should be UTC"""
        obj = model.identity.User(u"arthur", u"King Arthur")
        assert obj.created.tzinfo is not None, "No timezone information"
        assert obj.created.utcoffset() == timedelta(), "Non-UTC timezone"
    
    def test_permission_set(self):
        """Permissions should be calculated from all groups"""
        permission1 = model.identity.Permission(u"p1", u"Permission 1")
        permission2 = model.identity.Permission(u"p2", u"Permission 2")
        group1 = model.identity.Group(u"group1")
        group2 = model.identity.Group(u"group2")
        group1.add_permission(permission1)
        group2.add_permission(permission2)
        user = model.identity.User(u"my_user")
        assert user.permissions == frozenset()
        group1.add_user(user)
        session.flush()
        assert user.permissions == frozenset([permission1])
        group2.add_user(user)
        session.flush()
        assert user.permissions == frozenset([permission1, permission2])
    
    def test_name_fetch(self):
        """Users should be able to be fetched by name"""
        user = model.identity.User(u"great_user")
        assert model.identity.User.by_user_name(u"great_user") is user
    
    def test_legendary(self):
        """Users should be legendary if they're in the first game"""
        game1 = model.game.Game(u"First Game")
        game1.created = as_utc(datetime(2008, 4, 21, 14, 30))
        game2 = model.game.Game(u"Second Game")
        game2.created = as_utc(datetime(2008, 4, 21, 14, 45))
        user = model.identity.User(u"legendary_user")
        assert user.is_legendary is False, "User is prematurely legendary"
        entry2 = model.game.PlayerEntry(game2, user)
        session.flush()
        assert user.is_legendary is False, "Later game is legendary"
        entry1 = model.game.PlayerEntry(game1, user)
        session.flush()
        assert user.is_legendary is True, "First game is not legendary"

class TestGroup(SADBTest):
    def test_creation(self):
        """Group creation should set all necessary attributes"""
        obj = model.identity.Group(u"my_group", u"My Great Group")
        assert obj.group_name == "my_group", "Wrong internal name"
        assert obj.display_name == "My Great Group", "Wrong display name"
    
    def test_created_timezone(self):
        """Group creation date should be UTC"""
        obj = model.identity.Group(u"knights", u"Knights of the Round Table")
        assert obj.created.tzinfo is not None, "No timezone information"
        assert obj.created.utcoffset() == timedelta(), "Non-UTC timezone"
    
    def test_name_fetch(self):
        """Groups should be able to be fetched by name"""
        obj = model.identity.Group(u"great_group")
        assert model.identity.Group.by_group_name(u"great_group") is obj

class TestGame(SADBTest):
    def test_creation(self):
        """Game creation should set everything to default"""
        obj = model.game.Game(u"My Great Game")
        assert obj.display_name == u"My Great Game", "Display name is wrong"
        assert obj.started is None, "Premature starting date"
        assert obj.ended is None, "Premature end date"
        assert obj.state == model.game.Game.STATE_CREATED, \
            "Wrong initial state"
        assert obj.ignore_dates == frozenset(), \
            "There shouldn't be initial ignores"
        assert obj.ignore_weekdays == frozenset(), \
            "There shouldn't be initial ignores"
        assert (obj.zombie_starve_time == 
                model.game.Game.DEFAULT_ZOMBIE_STARVE_TIME), \
            "Wrong initial starve time"
        assert (obj.zombie_report_time == 
                model.game.Game.DEFAULT_ZOMBIE_REPORT_TIME), \
            "Wrong initial report time"
        assert obj.gid_length == model.game.Game.DEFAULT_GID_LENGTH, \
            "Wrong initial GID length"
        assert (obj.safe_zones ==
                [unicode(z) for z in model.game.Game.DEFAULT_SAFE_ZONES]), \
            "Wrong initial safe zones"
        assert obj.rules_notes is None, "Rules notes was set to a value"
    
    def test_timedeltas(self):
        """Game timedeltas should be the hours given by the columns"""
        obj = model.game.Game(u"My Delta Game")
        obj.zombie_starve_time = 27
        assert obj.zombie_starve_timedelta == timedelta(hours=27), \
            "Starve timedelta does not correspond to column"
        obj.zombie_report_time = 8
        assert obj.zombie_report_timedelta == timedelta(hours=8), \
            "Report timedelta does not correspond to column"
    
    def test_calculate_timedelta(self):
        """Calculating timedeltas should consider ignore dates"""
        game = model.game.Game(u"Calculation Game")
        game.ignore_dates = [date(2008, 4, 22), date(2008, 4, 23)]
        game.ignore_weekdays = [6, 7]
        # Check weekends
        dt1, dt2 = datetime(2008, 4, 25, 18, 27), datetime(2008, 4, 28, 2, 0)
        result = game.calculate_timedelta(as_local(dt1), as_local(dt2))
        assert result == timedelta(hours=7, minutes=33), \
            "Weekends aren't ignored"
        # Check holidays
        dt1, dt2 = datetime(2008, 4, 21, 18, 33), datetime(2008, 4, 24, 2, 0)
        result = game.calculate_timedelta(as_local(dt1), as_local(dt2))
        assert result == timedelta(hours=7, minutes=27), \
            "Holidays aren't ignored"
    
    def test_registration(self):
        """Games should only be open on STATE_OPEN"""
        game = model.game.Game(u"Registration game")
        assert game.registration_open is False, "Premature registration"
        while game.state < model.game.Game.STATE_OPEN:
            game.next_state()
        assert game.registration_open is True, "Unresponsive registration"
    
    def test_entry_insertion(self):
        """Entries should add themselves to the game and the user"""
        game = model.game.Game(u"Test Game")
        user = model.identity.User(u"Test User")
        entry = model.game.PlayerEntry(game, user)
        session.flush()
        assert entry in game.entries, "Entry not in game"
        assert entry in user.entries, "Entry not in user"
    
    def test_entry_deletion(self):
        """Entry destruction should remove itself from user and game"""
        game = model.game.Game(u"Test Game")
        user = model.identity.User(u"Test User")
        entry = model.game.PlayerEntry(game, user)
        session.flush()
        entry.delete()
        session.flush()
        assert not user.entries, "User still has entries"
        assert not game.entries, "Game still has entries"
    
    def test_deletion(self):
        """Game destruction should cascade to entries"""
        game = model.game.Game(u"Game to delete")
        user = model.identity.User(u"Test User")
        entry = model.game.PlayerEntry(game, user)
        session.flush()
        game.delete()
        session.flush()
        assert not user.entries, "User still has entries"

class TestGameplay(SADBTest):
    def setUp(self):
        super(TestGameplay, self).setUp()
        self.game = model.game.Game(u"Ender's game")
        self.user1 = model.identity.User(u"Ender")
        self.user2 = model.identity.User(u"Bean")
        self.user3 = model.identity.User(u"Chuck Norris")
        self.entry1 = model.game.PlayerEntry(self.game, self.user1)
        self.entry2 = model.game.PlayerEntry(self.game, self.user2)
        self.entry3 = model.game.PlayerEntry(self.game, self.user3)
        session.flush()
    
    def _choose_oz(self):
        while self.game.state < model.game.Game.STATE_CHOOSE_ZOMBIE:
            self.game.next_state()
        self.entry1.make_original_zombie()
        assert self.game.original_zombie is self.entry1, \
            "Original zombie does not stick"
    
    def _start_game(self):
        while self.game.state < model.game.Game.STATE_STARTED:
            self.game.next_state(as_local(datetime(2008, 4, 21, 14, 15)))
        assert self.game.in_progress is True, "Game does not start"
    
    def test_game_progress(self):
        """Games should progress properly"""
        self._choose_oz()
        self._start_game()
        # End game
        self.game.end(as_local(datetime(2008, 4, 21, 14, 30)))
        assert self.game.in_progress is False, "Game does not end"
    
    def test_starving(self):
        """Zombies should starve after starve time"""
        self._choose_oz()
        self._start_game()
        self.game.update(as_local(datetime(2008, 4, 22, 14, 15)))
        assert not self.game.original_zombie.is_dead, \
            "Original zombie is prematurely dead"
        self.game.update(as_local(datetime(2008, 4, 23, 14, 15)))
        assert self.game.original_zombie.is_dead, "Original zombie is not dead"
        assert (self.game.original_zombie.state == 
                model.game.PlayerEntry.STATE_DEAD_OZ), \
            "Wrong death state"
    
    def test_killing(self):
        """Zombie kills turn other players into zombies"""
        self._choose_oz()
        self._start_game()
        kill_time = as_local(datetime(2008, 4, 22, 14, 15))
        zombie_time = kill_time + self.game.human_undead_timedelta
        self.entry1.kill(self.entry2, kill_time, kill_time)
        # Check for infection
        assert self.entry1.feed_date == kill_time, "Wrong feed time"
        assert self.entry1.kills == 1, "Wrong kill count"
        assert self.entry2.is_infected, "Not infected yet"
        assert self.entry2.state == model.game.PlayerEntry.STATE_INFECTED, \
            "Victim is not infected"
        assert self.entry2.death_date == zombie_time, "Wrong death time"
        assert self.entry2.killed_by is self.user1, "Wrong killer"
        # Check for zombie
        self.game.update(zombie_time)
        assert self.entry2.is_undead, "Not zombie yet"
        assert self.entry2.state == model.game.PlayerEntry.STATE_ZOMBIE, \
            "Victim is not a zombie"
    
    def test_check_human_end(self):
        """Game should automatically detect human survival"""
        self._choose_oz()
        self._start_game()
        self.game.update(as_local(datetime(2008, 4, 23, 18, 15)))
        assert not self.game.in_progress, "Game is still advancing"
    
    def test_check_zombie_end(self):
        """Game should automatically detect zombie victory"""
        self._choose_oz()
        self._start_game()
        kill_time = as_local(datetime(2008, 4, 22, 14, 15))
        self.entry1.kill(self.entry2, kill_time, kill_time)
        kill_time = as_local(datetime(2008, 4, 22, 14, 30))
        self.entry1.kill(self.entry3, kill_time, kill_time)
        self.game.update(as_local(datetime(2008, 4, 27)))
        assert not self.game.in_progress, "Game is still advancing"
    
    def test_force_to_human(self):
        """Forcing to human should revert any zombie attributes"""
        self._choose_oz()
        self._start_game()
        kill_time = as_local(datetime(2008, 4, 22, 14, 15))
        self.entry1.kill(self.entry2, kill_time, kill_time)
        # Test original zombie to human
        self.entry1.force_to_human()
        assert self.entry1.is_human, "Not human yet"
        assert self.entry1.state == model.game.PlayerEntry.STATE_HUMAN, \
            "Not turned back to human"
        assert self.entry1.kills == 0, "Lingering kill count"
        assert self.entry1.death_date is None, "Lingering death date"
        assert self.entry1.feed_date is None, "Lingering death date"
        assert self.entry1.starve_date is None, "Lingering starve date"
        # Test zombie to human
        self.entry2.force_to_human()
        assert self.entry2.is_human, "Not human yet"
        assert self.entry2.state == model.game.PlayerEntry.STATE_HUMAN, \
            "Not turned back to human"
        assert self.entry2.kills == 0, "Lingering kill count"
        assert self.entry2.killed_by is None, "Still knows killer"
        assert self.entry2.death_date is None, "Lingering death date"
        assert self.entry2.feed_date is None, "Lingering death date"
        assert self.entry2.starve_date is None, "Lingering starve date"
    
    def test_force_to_infected(self):
        """Forcing to infected should infect the player"""
        self._choose_oz()
        time = as_local(datetime(2008, 4, 22, 14, 15))
        zombie_time = time + self.game.human_undead_timedelta
        # Test zombie to infected
        self.entry1.force_to_infected(time)
        assert self.entry1.is_infected, "Not infected yet"
        assert self.entry1.state == model.game.PlayerEntry.STATE_INFECTED, \
            "Has not been infected"
        assert self.entry1.death_date == zombie_time, "Wrong death date"
        # Test human to infected
        self.entry2.force_to_infected(time)
        assert self.entry2.is_infected, "Not infected yet"
        assert self.entry2.state == model.game.PlayerEntry.STATE_INFECTED, \
            "Has not been infected"
        assert self.entry2.death_date == zombie_time, "Wrong death date"
    
    def test_force_to_zombie(self):
        """Forcing to zombie should completely zombie the player"""
        time = as_local(datetime(2008, 4, 22, 14, 15))
        starve_time = time + self.game.zombie_starve_timedelta
        resurrect_time = starve_time + timedelta(minutes=5)
        # Test human to zombie
        self.entry1.force_to_zombie(time)
        assert self.entry1.is_undead, "Not undead yet"
        assert self.entry1.state == model.game.PlayerEntry.STATE_ZOMBIE, \
            "Has not been zombied"
        assert self.entry1.death_date == time, "Wrong death date"
        # Test starved to zombie
        self.entry2.force_to_zombie(time)
        self.entry2.force_to_dead(starve_time)
        self.entry2.force_to_zombie(resurrect_time)
        assert self.entry2.is_undead, "Not undead yet"
        assert self.entry2.state == model.game.PlayerEntry.STATE_ZOMBIE, \
            "Has not been zombied"
        assert self.entry2.death_date == time, "Obliterated death date"
        assert self.entry2.feed_date == resurrect_time, \
            "Did not fully resurrect"
        assert self.entry2.starve_date is None, "Lingering starve date"
    
    def test_force_to_dead(self):
        """Forcing to die should completely kill the player"""
        self._choose_oz()
        self._start_game()
        time = as_local(datetime(2008, 4, 22, 14, 15))
        starve_time = time + self.game.zombie_starve_timedelta
        resurrect_time = starve_time + timedelta(minutes=5)
        # Test infected to dead
        self.entry1.kill(self.entry3, time, time)
        self.entry3.force_to_dead(time)
        assert self.entry3.is_dead, "Not dead yet"
        assert self.entry3.state == model.game.PlayerEntry.STATE_DEAD, \
            "Has not been killed"
        assert self.entry3.death_date == time, "Wrong death date"
        assert self.entry3.starve_date == time, "Wrong starve date"
        # Test original zombie to dead
        self.entry1.force_to_dead(time)
        assert self.entry1.is_dead, "Not dead yet"
        assert self.entry1.state == model.game.PlayerEntry.STATE_DEAD_OZ, \
            "Has not been killed"
        assert self.entry1.death_date == self.game.started, \
            "Tampered with death date"
        assert self.entry1.starve_date == time, "Wrong starve date"
        # Test human to dead
        self.entry2.force_to_dead(time)
        assert self.entry2.is_dead, "Not dead yet"
        assert self.entry2.state == model.game.PlayerEntry.STATE_DEAD, \
            "Has not been killed"
        assert self.entry2.death_date == time, "Wrong death date"
        assert self.entry2.starve_date == time, "Wrong starve date"
