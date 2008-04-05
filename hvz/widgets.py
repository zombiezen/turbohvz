#!/usr/bin/env python
#
#   widgets.py
#   HvZ
#

from kid import Element
import turbogears
from turbogears import url, validators, widgets
from turbogears.widgets import Widget, WidgetsList

from hvz import util

__author__ = "Ross Light"
__date__ = "March 31, 2008"
__all__ = ['CustomDataGrid',
           'EntryList',
           'GameList',
           'KillSchema',
           'KillFields',
           'kill_form',
           'StageSchema',
           'JoinSchema',
           'JoinFields',
           'join_form',]

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
    params = ['sortable', 'columns', 'grid_class']
    params_doc = {'sortable': "Whether to use tg.paginate sorting",
                  'columns': "What columns to display",
                  'grid_class': "Element's class",}
    
    column_titles = {'id': _("ID"),}
    default_columns = ['id']
    accessors = {'*': 'default_accessor'}
    
    @staticmethod
    def default_accessor(row, column):
        return getattr(row, column, u"")
    
    def __init__(self, *args, **kw):
        sortable = kw.pop('sortable', False)
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

    @classmethod
    def get_column_title(cls, column):
        return cls.column_titles.get(column, column)

class GameList(CustomDataGrid):
    name = "game_list"
    grid_class = "game_list"
    default_columns = ['id', 'created', 'player_count']
    column_titles = {'id': _("ID"),
                     'created': _("Created"),
                     'started': _("Started"),
                     'ended': _("Ended"),
                     'player_count': _("Players"),}
    accessors = {'id': '_get_id_col',
                 'player_count': (lambda r, c: len(r.entries)),
                 'created': _get_date_col,
                 'started': _get_date_col,
                 'ended': _get_date_col,
                 '*': CustomDataGrid.default_accessor,}
    
    @staticmethod
    def _get_id_col(row, column):
        link = Element("{http://www.w3.org/1999/xhtml}a",
                       href=url("/game/view/" + str(row.game_id)))
        link.text = row.game_id
        return link

class EntryList(CustomDataGrid):
    name = "player_list"
    grid_class = "player_list"
    default_columns = ['player_gid', 'name', 'affiliation', 'death_date', 'kills']
    column_titles = {'player_gid': _("Game ID"),
                     'name': _("Player Name"),
                     'death_date': _("Death Date"),
                     'kills': _("Kills"),
                     'affiliation': _("Affiliation"),}
    accessors = {'name': '_get_name_col',
                 'affiliation': '_get_affiliation_col',
                 'death_date': _get_date_col,
                 '*': CustomDataGrid.default_accessor,}
    
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
                       href=url("/player/view/" + str(player.user_id)))
        link.text = player.display_name
        return link
    
    def _get_affiliation_col(self, row, column):
        from hvz.model import PlayerEntry
        if not self.show_oz and row.state == PlayerEntry.STATE_ORIGINAL_ZOMBIE:
            return row.STATE_NAMES[PlayerEntry.STATE_HUMAN]
        else:
            return row.affiliation

class KillSchema(validators.Schema):
    game_id = validators.Int()
    victim_id = validators.String(min=1, max=128)
    kill_date = validators.DateTimeConverter()

class KillFields(WidgetsList):
    game_id = widgets.HiddenField()
    victim_id = widgets.TextField(
        label=_("Victim"),
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

