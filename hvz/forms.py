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

from hvz import model, widgets as hvz_widgets
from hvz.model.game import Game

__author__ = "Ross Light"
__date__ = "April 8, 2008"
__all__ = ['UserNameValidator',
           'ZoneListConverter',
           'DateListValidator',
           'PasswordValidator',
           'CellProviderValidator',
           'KillSchema',
           'StageSchema',
           'JoinSchema',
           'OriginalZombieSchema',
           'RegisterSchema',
           'EditUserSchema',
           'GameSchema',
           'PasswordChangeSchema',
           'SendMailSchema',
           'kill_form',
           'join_form',
           'original_zombie_form',
           'register_form',
           'edit_user_form',
           'game_form',
           'password_change_form',
           'send_mail_form',]

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
        if model.identity.User.by_user_name(value) is not None:
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

class PasswordValidator(validators.FormValidator):
    password = None
    __unpackargs__ = ('password',)
    
    def validate_python(self, value, state=None):
        from turbogears.identity import encrypt_password
        from hvz.model.identity import User
        errors = {}
        requested_user = User.query.get(int(value['user_id']))
        if requested_user is None:
            errors['user_id'] = "Bad User ID"
            raise validators.Invalid("This form has errors", value, state,
                                     error_dict=errors)
        if encrypt_password(value[self.password]) != requested_user.password:
            errors[self.password] = "Wrong password"
            raise validators.Invalid("This form has errors", value, state,
                                     error_dict=errors)

class CellProviderValidator(validators.UnicodeString):
    messages = {'bad_provider': "Provider is unrecognized.",}
    
    def validate_python(self, value, state):
        from hvz.email import cell_providers
        if value not in cell_providers:
            raise validators.Invalid(self.message('bad_provider', state),
                                     value, state)
        else:
            super(CellProviderValidator, self).validate_python(value, state)

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
    notify_sms = validators.Bool()

class OriginalZombieSchema(validators.Schema):
    game_id = validators.Int()
    original_zombie = validators.Any(
        validators.Int(),
        validators.OneOf(["random"]),)

class RegisterSchema(validators.Schema):
    user_name = UserNameValidator(min=4, max=16, strip=True)
    display_name = validators.UnicodeString(min=1, max=255, strip=True)
    email_address = validators.Email()
    cell_number = validators.PhoneNumber(if_empty=None, not_empty=False)
    cell_provider = CellProviderValidator()
    password1 = validators.UnicodeString(min=8)
    password2 = validators.UnicodeString()
    profile = validators.UnicodeString(max=4096, strip=True)
    chained_validators = [validators.FieldsMatch('password1', 'password2')]

class EditUserSchema(validators.Schema):
    user_id = validators.Int()
    display_name = RegisterSchema.fields['display_name']
    cell_number = RegisterSchema.fields['cell_number']
    cell_provider = RegisterSchema.fields['cell_provider']
    email_address = RegisterSchema.fields['email_address']
    profile = RegisterSchema.fields['profile']
    new_image = validators.FieldStorageUploadConverter()
    clear_user_image = validators.Bool()

class GameSchema(validators.Schema):
    game_id = validators.Int(if_empty=None, not_empty=False)
    display_name = validators.UnicodeString(min=4, max=255, strip=True)
    gid_length = validators.Int(min=1, max=128)
    zombie_starve_time = validators.Int(min=1)
    zombie_report_time = validators.Int(min=1)
    human_undead_time = validators.Int(min=0)
    ignore_weekdays = validators.ForEach(validators.Int(min=1, max=7),
                                         convert_to_list=True,
                                         if_empty=[],
                                         if_missing=[],)
    ignore_dates = DateListValidator()
    safe_zones = validators.All(ZoneListConverter(),
                                validators.UnicodeString(max=2048))
    rules_notes = validators.UnicodeString(max=4096)

class PasswordChangeSchema(validators.Schema):
    user_id = validators.Int()
    original_password = validators.UnicodeString()
    password1 = RegisterSchema.fields['password1']
    password2 = RegisterSchema.fields['password2']
    chained_validators = [validators.FieldsMatch('password1', 'password2'),
                          PasswordValidator('original_password'),]

class SendMailSchema(validators.Schema):
    recipients = validators.ForEach(validators.All(validators.Email(),
                                                   validators.NotEmpty()),
                                    convert_to_list=True,
                                    not_empty=True,)
    subject = validators.UnicodeString(min=1)
    message = validators.UnicodeString(max=8192)

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
    notify_sms = widgets.CheckBox(
        label=_("Send SMS Updates"),
        help_text=_("Check this box if you want to receive game updates "
                    "through text messages."),)

class OriginalZombieFields(WidgetsList):
    game_id = widgets.HiddenField()
    original_zombie = widgets.SingleSelectField(
        label=_("Original Zombie"),
        options=[("random", _("Random"))],)

def _provider_options():
    from hvz.email import cell_providers
    return [(key, name) for key, (name, domain) in cell_providers.iteritems()]

_cell_number_help_text = _(
    "[Optional] Your cell phone number.  This number will "
    "only be used to send you short game notifications.  Only "
    "the system administrator will be able to use it.")

_cell_provider_help_text = _(
    "[Optional] Your cell phone's provider.  You must give "
    "this if you want text message updates to work properly. "
    "If your provider is not on this list, then we can't send "
    "text messages to you.")

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
    cell_number = widgets.TextField(
        label=_("Cell Phone Number"),
        help_text=_cell_number_help_text,
        validator=RegisterSchema.fields['cell_number'],)
    cell_provider = widgets.SingleSelectField(
        label=_("Cell Phone Provider"),
        help_text=_cell_provider_help_text,
        options=_provider_options,)
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

def _new_image_help_text():
    from hvz.util import display_file_size
    max_file_size = model.images.Image.get_max_file_size()
    max_image_width, max_image_height = model.images.Image.get_max_image_size()
    return _("[Optional] A picture of yourself.  This image must be under %s "
             "and smaller than %ix%i pixels and will replace the image you "
             "have now.  If you leave this field blank, your current image "
             "will be kept, unless you check the box below.") % \
        (display_file_size(max_file_size),
         max_image_width,
         max_image_height)

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
    cell_number = widgets.TextField(
        label=_("Cell Phone Number"),
        help_text=_cell_number_help_text,
        validator=RegisterSchema.fields['cell_number'],)
    cell_provider = widgets.SingleSelectField(
        label=_("Cell Phone Provider"),
        help_text=_cell_provider_help_text,
        options=_provider_options,)
    profile = widgets.TextArea(
        label=_("Profile"),
        help_text=_("[Optional] Create a short profile describing yourself.  "
                    "Must be under 4096 characters in length."),
        cols=64,
        rows=20,)
    new_image = widgets.FileField(
        label=_("Image"),
        help_text=_new_image_help_text(),)
    clear_user_image = widgets.CheckBox(
        label=_("Delete Image"),
        help_text=_("If you check this box, your current image will be "
                    "permanently deleted."),)

class GameFields(WidgetsList):
    game_id = widgets.HiddenField()
    display_name = widgets.TextField(
        label=_("Game name"))
    gid_length = widgets.TextField(
        label=_("Player GID Length"),
        help_text=_("The length of each player's game identification number. "
                    "The default length of 16 should be sufficient for most "
                    "games."),
        default=Game.DEFAULT_GID_LENGTH,)
    zombie_starve_time = widgets.TextField(
        label=_("Zombie Starve Time"),
        help_text=_("The length of time (in hours) that a zombie has to feed "
                    "before starving."),
        default=Game.DEFAULT_ZOMBIE_STARVE_TIME,)
    zombie_report_time = widgets.TextField(
        label=_("Zombie Report Time"),
        help_text=_("The length of time (in hours) that a zombie has to "
                    "report a kill."),
        default=Game.DEFAULT_ZOMBIE_REPORT_TIME,)
    human_undead_time = widgets.TextField(
        label=_("Human Infection Time"),
        help_text=_("The length of time (in minutes) that it takes to turn a "
                    "human into a zombie"),
        default=Game.DEFAULT_HUMAN_UNDEAD_TIME,)
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
        default=Game.DEFAULT_SAFE_ZONES,
        validator=ZoneListConverter())
    rules_notes = widgets.TextArea(
        label=_("Rules Notes"),
        help_text=_("Any additional notes to add to the end of the rules."))

class PasswordChangeFields(WidgetsList):
    user_id = widgets.HiddenField()
    original_password = widgets.PasswordField(
        label=_("Current Password"),
        help_text=_("Please type your current password for security "
                    "purposes."),)
    password1 = widgets.PasswordField(
        label=_("New Password"),
        help_text=_("Must be at least 8 characters in length."),)
    password2 = widgets.PasswordField(
        label=_("Confirm Password"),
        help_text=_("For security purposes, retype your password."),)

class SendMailFields(WidgetsList):
    recipients = hvz_widgets.FieldList(label=_("To"),)
    subject = widgets.TextField(
        label=_("Subject"),
        attrs={'size': 64},)
    message = widgets.TextArea(
        label=_("Message"),
        rows=20,
        cols=64,)

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
    submit_text=_("Save"),)

game_form = widgets.TableForm(
    name="game_form",
    fields=GameFields(),
    validator=GameSchema(),)

password_change_form = widgets.TableForm(
    name="change_password_form",
    fields=PasswordChangeFields(),
    validator=PasswordChangeSchema(),
    action=url('/user/action.changepassword'),
    submit_text=_("Change"),)

send_mail_form = widgets.TableForm(
    name="send_mail_form",
    fields=SendMailFields(),
    validator=SendMailSchema(),
    action=url('/action.sendmail'),
    submit_text=_("Send"),
    method='GET',)
