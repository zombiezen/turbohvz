#!/usr/bin/env python
#
#   forms.py
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

"""Widgets for the various forms throughout HvZ"""

import re
import string

from turbogears import url, validators, widgets
from turbogears.widgets import WidgetsList

from hvz import model

__author__ = "Ross Light"
__date__ = "April 8, 2008"
__all__ = ['UserNameValidator',
           'ZoneListConverter',
           'DateListValidator',
           'KillSchema',
           'StageSchema',
           'JoinSchema',
           'OriginalZombieSchema',
           'RegisterSchema',
           'EditUserSchema',
           'GameSchema',
           'kill_form',
           'join_form',
           'original_zombie_form',
           'register_form',
           'edit_user_form',
           'game_form',]

## VALIDATORS ##

class UserNameValidator(validators.UnicodeString):
    messages = {'non_unique': "That user name is already taken",
                'invalid_chars': "User names can only contain letters, "
                                 "numbers, periods, underscores, and hyphens."}
    
    @staticmethod
    def _has_valid_chars(s):
        ascii_chars = frozenset(chr(i) for i in xrange(255))
        nonprintable_chars = ascii_chars - frozenset(string.printable)
        bad_punctuation = frozenset(string.punctuation) - frozenset('._-')
        whitespace = frozenset(string.whitespace)
        invalid_chars = nonprintable_chars | bad_punctuation | whitespace
        return not frozenset(s) & invalid_chars
    
    def validate_python(self, value, state): 
        if model.User.by_user_name(value) is not None:
            raise validators.Invalid(self.message('non_unique', state),
                                     value, state)
        elif not self._has_valid_chars(value):
            raise validators.Invalid(self.message('invalid_chars', state),
                                     value, state)
        else:
            super(UserNameValidator, self).validate_python(value, state)

class ZoneListConverter(validators.FancyValidator):
    def _to_python(self, value, state):
        result = []
        for line in value.splitlines():
            line = line.strip()
            if not line:
                continue
            result.append(line)
        return result
    
    def _from_python(self, value, state):
        # We convert all to unicode in case we get lazytext defaults
        return '\n'.join(unicode(zone) for zone in value)

class DateListValidator(validators.FancyValidator):
    date_regex = re.compile(r'^(\d{4})-(\d{2})-(\d{2})$')
    messages = {'invalid_date': "Date must be YYYY-MM-DD",}
    
    def _to_python(self, value, state):
        from datetime import date
        result = []
        for line in value.splitlines():
            line = line.strip()
            if not line:
                continue
            match = self.date_regex.match(line)
            if match:
                year, month, day = match.groups()
                year, month, day = int(year, 10), int(month, 10), int(day, 10)
                new_date = date(year, month, day)
                result.append(new_date)
            else:
                raise validators.Invalid(self.message('invalid_date', state),
                                         value, state)
        return result
    
    def _from_python(self, value, state):
        date_strings = ['%.4i-%.2i-%.2i' % (d.year, d.month, d.day)
                        for d in value]
        return '\n'.join(date_strings)

## SCHEMAS ##

class KillSchema(validators.Schema):
    game_id = validators.Int()
    victim_id = validators.String(min=1, max=128)
    kill_date = validators.DateTimeConverter()

class StageSchema(validators.Schema):
    game_id = validators.Int()
    btnPrev = validators.UnicodeString(if_empty=None)
    btnNext = validators.UnicodeString(if_empty=None)

class JoinSchema(validators.Schema):
    game_id = validators.Int()
    original_pool = validators.Bool()

class OriginalZombieSchema(validators.Schema):
    game_id = validators.Int()
    original_zombie = validators.Any(
        validators.Int(),
        validators.OneOf(["random"]),)

class RegisterSchema(validators.Schema):
    user_name = UserNameValidator(min=4, max=16, strip=True)
    display_name = validators.UnicodeString(min=1, max=255, strip=True)
    email_address = validators.Email()
    password1 = validators.UnicodeString(min=8)
    password2 = validators.UnicodeString(min=8)
    profile = validators.UnicodeString(max=4096, strip=True)
    chained_validators = [validators.FieldsMatch('password1', 'password2')]

class EditUserSchema(validators.Schema):
    user_id = validators.Int()
    display_name = validators.UnicodeString(min=1, max=255, strip=True)
    email_address = validators.Email()
    profile = validators.UnicodeString(max=4096, strip=True)

class GameSchema(validators.Schema):
    game_id = validators.Int(if_empty=None, not_empty=False)
    display_name = validators.UnicodeString(min=4, max=255, strip=True)
    gid_length = validators.Int(min=1, max=128)
    zombie_starve_time = validators.Int(min=1)
    zombie_report_time = validators.Int(min=1)
    ignore_weekdays = validators.ForEach(validators.Int(min=1, max=7),
                                         convert_to_list=True,
                                         if_empty=[],
                                         if_missing=[],)
    ignore_dates = DateListValidator()
    safe_zones = validators.All(ZoneListConverter(),
                                validators.UnicodeString(max=2048))
    rules_notes = validators.UnicodeString(max=4096)

## FIELDS ##

class KillFields(WidgetsList):
    game_id = widgets.HiddenField()
    victim_id = widgets.TextField(
        label=_("Victim"),
        help_text=_("The Game ID of your victim (located on his or her 3x5 "
                    "card)"),
        attrs=dict(size=64),)
    kill_date = widgets.CalendarDateTimePicker(
        label=_("Time of Demise"),
        help_text=_("The time at which the victim was tagged"),)

class JoinFields(WidgetsList):
    game_id = widgets.HiddenField()
    original_pool = widgets.CheckBox(
        label=_("Consider for Original Zombie"),)

class OriginalZombieFields(WidgetsList):
    game_id = widgets.HiddenField()
    original_zombie = widgets.SingleSelectField(
        label=_("Original Zombie"),
        options=[("random", _("Random"))],)

class RegisterFields(WidgetsList):
    user_name = widgets.TextField(
        label=_("Internal Name"),
        help_text=_("This will be the name you type at the login screen.  "
                    "Must be between 4-16 characters in length."),)
    display_name = widgets.TextField(
        label=_("Real Name"),
        help_text=_("This will be the name everyone else sees."),)
    email_address = widgets.TextField(
        label=_("Email Address"),
        help_text=_("Your email address.  Only the system administrator will "
                    "see your address and will use it only to send "
                    "notifications and other game information to you."),)
    password1 = widgets.PasswordField(
        label=_("Password"),
        help_text=_("Must be at least 8 characters in length"),)
    password2 = widgets.PasswordField(
        label=_("Confirm Password"),
        help_text=_("For security purposes, retype your password"),)
    profile = widgets.TextArea(
        label=_("Profile"),
        help_text=_("[Optional] Create a short profile describing yourself.  "
                    "Must be under 4096 characters in length."),
        cols=64,
        rows=20,)

class EditUserFields(WidgetsList):
    user_id = widgets.HiddenField()
    display_name = widgets.TextField(
        label=_("Real Name"),
        help_text=_("This will be the name everyone else sees."),)
    email_address = widgets.TextField(
        label=_("Email Address"),
        help_text=_("Your email address.  Only the system administrator will "
                    "see your address and will use it only to send "
                    "notifications and other game information to you."),)
    profile = widgets.TextArea(
        label=_("Profile"),
        help_text=_("[Optional] Create a short profile describing yourself.  "
                    "Must be under 4096 characters in length."),
        cols=64,
        rows=20,)

class GameFields(WidgetsList):
    game_id = widgets.HiddenField()
    display_name = widgets.TextField(
        label=_("Game name"))
    gid_length = widgets.TextField(
        label=_("Player GID Length"),
        help_text=_("The length of each player's game identification number. "
                    "The default length of 16 should be sufficient for most "
                    "games."),
        default=model.Game.DEFAULT_GID_LENGTH,)
    zombie_starve_time = widgets.TextField(
        label=_("Zombie Starve Time"),
        help_text=_("The length of time (in hours) that a zombie has to feed "
                    "before starving."),
        default=model.Game.DEFAULT_ZOMBIE_STARVE_TIME,)
    zombie_report_time = widgets.TextField(
        label=_("Zombie Report Time"),
        help_text=_("The length of time (in hours) that a zombie has to "
                    "report a kill."),
        default=model.Game.DEFAULT_ZOMBIE_REPORT_TIME,)
    ignore_weekdays = widgets.MultipleSelectField(
        label=_("Ignore Days"),
        help_text=_("The days of the week to regularly ignore when "
                    "considering starve time.  You can choose multiple days."),
        options=[(1, _("Monday")),
                 (2, _("Tuesday")),
                 (3, _("Wednesday")),
                 (4, _("Thursday")),
                 (5, _("Friday")),
                 (6, _("Saturday")),
                 (7, _("Sunday"))],
        default=[6, 7],
        size=7,)
    ignore_dates = widgets.TextArea(
        label=_("Ignore Dates"),
        help_text=_("Individual dates to ignore when considering starve "
                    "time.  Each date must be put on a separate line in ISO "
                    "YYYY-MM-DD format."),
        validator=DateListValidator()) # This ensures from_python gets called
    safe_zones = widgets.TextArea(
        label=_("Safe Zones"),
        help_text=_("The safe zones to include in the rules.  Each zone must "
                    "be put on a separate line."),
        default=model.Game.DEFAULT_SAFE_ZONES,
        validator=ZoneListConverter())
    rules_notes = widgets.TextArea(
        label=_("Rules Notes"),
        help_text=_("Any additional notes to add to the end of the rules."))

## FORMS ##

kill_form = widgets.TableForm(name='kill_form',
                              fields=KillFields(),
                              validator=KillSchema(),
                              action=url('/game/action.kill'),
                              submit_text=_("Report"),)

join_form = widgets.TableForm(name='join_form',
                              fields=JoinFields(),
                              validator=JoinSchema(),
                              action=url('/game/action.join'),
                              submit_text=_("Join"),)

original_zombie_form = widgets.TableForm(
    name='oz_form',
    fields=OriginalZombieFields(),
    validator=OriginalZombieSchema(),
    action=url('/game/action.oz'),
    submit_text=_("Choose"),)

register_form = widgets.TableForm(
    name='register_form',
    fields=RegisterFields(),
    validator=RegisterSchema(),
    action=url('/user/action.register'),
    submit_text=_("Register"),)

edit_user_form = widgets.TableForm(
    name='edit_user_form',
    fields=EditUserFields(),
    validator=EditUserSchema(),
    action=url('/user/action.edit'),
    submit_text=_("Edit"),)

game_form = widgets.TableForm(
    name="game_form",
    fields=GameFields(),
    validator=GameSchema(),)
    
