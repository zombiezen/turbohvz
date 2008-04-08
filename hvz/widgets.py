#!/usr/bin/env python
#
#   widgets.py
#   HvZ
#

import re

from kid import Element
import turbogears
from turbogears import url, validators, widgets
from turbogears.widgets import Widget, WidgetsList

from hvz import model, util

__author__ = "Ross Light"
__date__ = "March 31, 2008"
__all__ = ['Pager',
           'CustomDataGrid',
           'EntryList',
           'GameList',
           'UserList',
           'UserNameValidator',
           'DateListValidator',
           'KillSchema',
           'KillFields',
           'kill_form',
           'StageSchema',
           'JoinSchema',
           'JoinFields',
           'join_form',
           'OriginalZombieSchema',
           'OriginalZombieFields',
           'original_zombie_form',
           'RegisterSchema',
           'RegisterFields',
           'register_form',
           'CreateGameSchema',
           'CreateGameFields',
           'create_game_form',]

class Pager(Widget):
    template = "hvz.templates.widgets.pager"

def _get_date_col(row, column):
    from hvz.util import display_date
    date = getattr(row, column, None)
    if date is None:
        return u""
    else:
        return display_date(date)

class CustomDataGrid(Widget):
    name = "custom_grid"
    grid_class = "custom_grid"
    template = "hvz.templates.widgets.customgrid"
    params = ['sortable', 'columns', 'grid_class', 'no_data_msg']
    params_doc = {'sortable': "Whether to enable tg.paginate sorting",
                  'columns': "What columns to display",
                  'grid_class': "Element's class",
                  'no_data_msg': "Message to display if there is no data",}
    
    column_titles = {'id': _("ID"),}
    default_columns = ['id']
    exclude_sorting = []
    accessors = {'*': 'default_accessor'}
    no_data_msg = _("No data")
    
    @staticmethod
    def default_accessor(row, column):
        return getattr(row, column, u"")
    
    def __init__(self, *args, **kw):
        sortable = kw.pop('sortable', None)
        columns = kw.pop('columns', self.default_columns)
        grid_class = kw.pop('grid_class', self.grid_class)
        super(CustomDataGrid, self).__init__(*args, **kw)
        self.sortable = bool(sortable)
        self.columns = list(columns)
        self.grid_class = grid_class
    
    def update_params(self, d):
        super(CustomDataGrid, self).update_params(d)
        d['get_cell'] = self.get_cell
        d['get_column_title'] = self.get_column_title
        d['exclude_sorting'] = frozenset(self.exclude_sorting)
    
    def get_cell(self, row, column):
        """
        Retrieves the value for a cell.

        :Parameters:
            row
                The row to get a value for
            column : str
                The name of the column
        :Returns: The column's value
        :ReturnType: str
        """
        default_accessor = self.accessors.get('*')
        accessor = self.accessors.get(column, default_accessor)
        if accessor is None:
            raise ValueError("Invalid column: %r", column)
        elif isinstance(accessor, basestring):
            accessor = getattr(self, accessor)
        return accessor(row, column)
    
    def get_column_title(self, column):
        return self.column_titles.get(column, column)

class GameList(CustomDataGrid):
    name = "game_list"
    grid_class = "custom_grid game_list"
    default_columns = ['game_id', 'created', 'player_count']
    exclude_sorting = ['player_count']
    column_titles = {'game_id': _("ID"),
                     'created': _("Created"),
                     'started': _("Started"),
                     'ended': _("Ended"),
                     'player_count': _("Players"),}
    accessors = {'game_id': '_get_id_col',
                 'player_count': (lambda r, c: len(r.entries)),
                 'created': _get_date_col,
                 'started': _get_date_col,
                 'ended': _get_date_col,
                 '*': CustomDataGrid.default_accessor,}
    no_data_msg = _("No games found")
    
    @staticmethod
    def _get_id_col(row, column):
        link = Element("{http://www.w3.org/1999/xhtml}a",
                       href=util.game_link(row))
        link.text = row.game_id
        return link

class EntryList(CustomDataGrid):
    name = "player_list"
    grid_class = "custom_grid player_list"
    default_columns = ['name', 'affiliation', 'death_date', 'kills']
    exclude_sorting = ['affiliation']
    column_titles = {'player_gid': _("Game ID"),
                     'name': _("Player Name"),
                     'death_date': _("Death Date"),
                     'kills': _("Kills"),
                     'affiliation': _("Affiliation"),}
    accessors = {'name': '_get_name_col',
                 'affiliation': '_get_affiliation_col',
                 'death_date': _get_date_col,
                 '*': CustomDataGrid.default_accessor,}
    no_data_msg = _("No players have joined yet")
    
    params = ['show_oz']
    params_doc = {'show_oz': "Whether to reveal the original zombie",}
    
    def __init__(self, *args, **kw):
        show_oz = kw.pop('show_oz', True)
        super(EntryList, self).__init__(*args, **kw)
        self.show_oz = show_oz
    
    @staticmethod
    def _get_name_col(row, column):
        player = row.player
        link = Element("{http://www.w3.org/1999/xhtml}a",
                       href=util.user_link(player))
        link.text = player.display_name
        return link
    
    def _get_affiliation_col(self, row, column):
        from hvz.model import PlayerEntry
        if not self.show_oz and row.state == PlayerEntry.STATE_ORIGINAL_ZOMBIE:
            return row.STATE_NAMES[PlayerEntry.STATE_HUMAN]
        else:
            return row.affiliation

class UserList(CustomDataGrid):
    name = "user_list"
    grid_class = "custom_grid user_list"
    default_columns = ['display_name', 'created']
    column_titles = {'user_id': _("UID"),
                     'user_name': _("Login"),
                     'email_address': _("Email"),
                     'display_name': _("Name"),
                     'created': _("Joined"),}
    accessors = {'display_name': '_get_display_name_col',
                 'created': _get_date_col,
                 '*': 'default_accessor'}
    no_data_msg = _("No users yet")
    
    @staticmethod
    def _get_display_name_col(row, column):
        link = Element("{http://www.w3.org/1999/xhtml}a",
                       href=util.user_link(row))
        link.text = row.display_name
        return link

## VALIDATORS ##

class UserNameValidator(validators.UnicodeString):
    messages = {'non_unique': "That user name is already taken",}
    
    def validate_python(self, value, state):
        from hvz.model import User
        if User.by_user_name(value) is not None:
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

## FORMS ##

class KillSchema(validators.Schema):
    game_id = validators.Int()
    victim_id = validators.String(min=1, max=128)
    kill_date = validators.DateTimeConverter()

class KillFields(WidgetsList):
    game_id = widgets.HiddenField()
    victim_id = widgets.TextField(
        label=_("Victim"),
        help_text=_("The Game ID of your victim (located on his or her 3x5 "
                    "card)"),
        attrs=dict(size=64),)
    kill_date = widgets.CalendarDateTimePicker(
        label=_("Time of Demise"),)

kill_form = widgets.TableForm(name='kill_form',
                              fields=KillFields(),
                              validator=KillSchema(),
                              action=turbogears.url('/game/action.kill'),
                              submit_text=_("Report"),)

class StageSchema(validators.Schema):
    game_id = validators.Int()
    btnPrev = validators.UnicodeString(if_empty=None)
    btnNext = validators.UnicodeString(if_empty=None)

class JoinSchema(validators.Schema):
    game_id = validators.Int()
    original_pool = validators.Bool()

class JoinFields(WidgetsList):
    game_id = widgets.HiddenField()
    original_pool = widgets.CheckBox(
        label=_("Consider for Original Zombie"),)

join_form = widgets.TableForm(name='join_form',
                              fields=JoinFields(),
                              validator=JoinSchema(),
                              action=turbogears.url('/game/action.join'),
                              submit_text=_("Join"),)

class OriginalZombieSchema(validators.Schema):
    game_id = validators.Int()
    original_zombie = validators.Any(
        validators.Int(),
        validators.OneOf(["random"]),)

class OriginalZombieFields(WidgetsList):
    game_id = widgets.HiddenField()
    original_zombie = widgets.SingleSelectField(
        label=_("Original Zombie"),
        options=[("random", _("Random"))],)

original_zombie_form = widgets.TableForm(
    name='oz_form',
    fields=OriginalZombieFields(),
    validator=OriginalZombieSchema(),
    action=turbogears.url('/game/action.oz'),
    submit_text=_("Choose"),)

class RegisterSchema(validators.Schema):
    user_name = UserNameValidator(min=4, max=16)
    display_name = validators.UnicodeString(min=1, max=255)
    email_address = validators.Email()
    password1 = validators.UnicodeString(min=8)
    password2 = validators.UnicodeString(min=8)
    profile = validators.UnicodeString(max=1024)
    chained_validators = [validators.FieldsMatch('password1', 'password2')]

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

register_form = widgets.TableForm(
    name='register_form',
    fields=RegisterFields(),
    validator=RegisterSchema(),
    action=turbogears.url('/user/action.register'),
    submit_text=_("Register"),)

class CreateGameSchema(validators.Schema):
    zombie_starve_time = validators.Int(min=1)
    ignore_weekdays = validators.ForEach(validators.Int(min=1, max=7),
                                         convert_to_list=True,
                                         if_empty=[],
                                         if_missing=[],)
    ignore_dates = DateListValidator()

class CreateGameFields(WidgetsList):
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

create_game_form = widgets.TableForm(
    name="create_game_form",
    fields=CreateGameFields(),
    validator=CreateGameSchema(),
    action=turbogears.url('/game/action.create'),
    submit_text=_("Create"),)
    
