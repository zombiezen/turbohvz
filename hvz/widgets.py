#!/usr/bin/env python
#
#   widgets.py
#   HvZ
#

from kid import Element
from turbogears import url
from turbogears.widgets import Widget

from hvz import util

__author__ = "Ross Light"
__date__ = "March 31, 2008"
__all__ = ['Pager',
           'CustomDataGrid',
           'EntryList',
           'GameList',
           'UserList',]

class Pager(Widget):
    template = "hvz.templates.widgets.pager"

def _get_date_col(row, column):
    date = getattr(row, column, None)
    if date is None:
        return u""
    else:
        return util.display_date(date)

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
    default_columns = ['game_id', 'display_name', 'created', 'player_count']
    exclude_sorting = ['player_count']
    column_titles = {'game_id': _("ID"),
                     'display_name': _("Name"),
                     'created': _("Created"),
                     'started': _("Started"),
                     'ended': _("Ended"),
                     'player_count': _("Players"),}
    accessors = {'game_id': '_get_link_col',
                 'display_name': '_get_link_col',
                 'player_count': (lambda r, c: len(r.entries)),
                 'created': _get_date_col,
                 'started': _get_date_col,
                 'ended': _get_date_col,
                 '*': CustomDataGrid.default_accessor,}
    no_data_msg = _("No games found")
    
    @staticmethod
    def _get_link_col(row, column):
        link = Element("{http://www.w3.org/1999/xhtml}a",
                       href=util.game_link(row))
        link.text = getattr(row, column)
        return link

class EntryList(CustomDataGrid):
    name = "player_list"
    grid_class = "custom_grid player_list"
    default_columns = ['name', 'affiliation', 'death_date', 'kills']
    exclude_sorting = ['affiliation',
                       'death_date',
                       'feed_date',
                       'starve_date',
                       'kills',]
    column_titles = {'player_gid': _("Game ID"),
                     'name': _("Player Name"),
                     'death_date': _("Death Date"),
                     'feed_date': _("Feed Date"),
                     'starve_date': _("Starve Date"),
                     'kills': _("Kills"),
                     'affiliation': _("Affiliation"),}
    accessors = {'name': '_get_name_col',
                 'affiliation': '_get_affiliation_col',
                 'death_date': '_get_oz_date_col',
                 'feed_date': '_get_oz_date_col',
                 'starve_date': '_get_oz_date_col',
                 'kills': '_get_kills_col',
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
    
    def _get_oz_date_col(self, row, column):
        from hvz.model import PlayerEntry
        if not self.show_oz and row.state == PlayerEntry.STATE_ORIGINAL_ZOMBIE:
            return u""
        else:
            return _get_date_col(row, column)
    
    def _get_kills_col(self, row, column):
        from hvz.model import PlayerEntry
        if not self.show_oz and row.state == PlayerEntry.STATE_ORIGINAL_ZOMBIE:
            return 0
        else:
            return self.default_accessor(row, column)

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
