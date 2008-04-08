#!/usr/bin/env python
#
#   forms.py
#   HvZ
#

"""Widgets for the various forms throughout HvZ"""

import re

from turbogears import url, validators, widgets
from turbogears.widgets import WidgetsList

from hvz import model

__author__ = "Ross Light"
__date__ = "April 8, 2008"
__all__ = ['UserNameValidator',
           'DateListValidator',
           'KillSchema',
           'StageSchema',
           'JoinSchema',
           'OriginalZombieSchema',
           'RegisterSchema',
           'GameSchema',
           'kill_form',
           'join_form',
           'original_zombie_form',
           'register_form',
           'game_form',]

## VALIDATORS ##

class UserNameValidator(validators.UnicodeString):
    messages = {'non_unique': "That user name is already taken",}
    
    def validate_python(self, value, state):
        if model.User.by_user_name(value) is not None:
            raise validators.Invalid(self.message('non_unique', state),
                                     value, state)
        else:
            super(UserNameValidator, self).validate_python(value, state)

class DateListValidator(validators.FancyValidator):
    date_regex = re.compile(r'^(\d{4})-(\d{2})-(\d{2})$')
    messages = {'invalid_date': "Date must be YYYY-MM-DD",}
    
    def _to_python(self, value, state):
        from datetime import date
        value = value.strip()
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
    profile = validators.UnicodeString(max=1024, strip=True)
    chained_validators = [validators.FieldsMatch('password1', 'password2')]

class GameSchema(validators.Schema):
    game_id = validators.Int(if_empty=None, not_empty=False)
    display_name = validators.UnicodeString(min=4, max=255, strip=True)
    zombie_starve_time = validators.Int(min=1)
    ignore_weekdays = validators.ForEach(validators.Int(min=1, max=7),
                                         convert_to_list=True,
                                         if_empty=[],
                                         if_missing=[],)
    ignore_dates = DateListValidator()

## FIELDS ##

class KillFields(WidgetsList):
    game_id = widgets.HiddenField()
    victim_id = widgets.TextField(
        label=_("Victim"),
        help_text=_("The Game ID of your victim (located on his or her 3x5 "
                    "card)"),
        attrs=dict(size=64),)
    kill_date = widgets.CalendarDateTimePicker(
        label=_("Time of Demise"),)

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
                    "Must be under 1024 characters in length."),
        cols=64,
        rows=20,)

class GameFields(WidgetsList):
    game_id = widgets.HiddenField()
    display_name = widgets.TextField(
        label=_("Game name"))
    zombie_starve_time = widgets.TextField(
        label=_("Zombie Starve Time"),
        help_text=_("The length of time (in hours) that a zombie has to feed "
                    "before starving."),
        default=model.Game.DEFAULT_ZOMBIE_STARVE_TIME,)
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
                    "YYYY-MM-DD format."))

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

game_form = widgets.TableForm(
    name="game_form",
    fields=GameFields(),
    validator=GameSchema(),)
    
