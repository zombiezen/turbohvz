#!/usr/bin/env python
#
#   widgets.py
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

from kid import Element
from pkg_resources import resource_filename
import turbogears
from turbogears import url, widgets
from turbogears.widgets import FormField, Widget

from hvz import util
from hvz.model.game import PlayerEntry

__author__ = "Ross Light"
__date__ = "March 31, 2008"
__all__ = ['Pager',
           'FieldList',
           'CustomDataGrid',
           'EntryList',
           'GameList',
           'UserList',]

## WIDGET RESOURCES ##

static_dir = resource_filename('hvz', 'widget_static')
turbogears.widgets.register_static_directory('hvz', static_dir)

## WIDGETS ##

class Pager(Widget):
    template = "hvz.templates.widgets.pager"

class FieldList(FormField):
    template = "hvz.templates.widgets.fieldlist"
    field_class = 'text_field_list'
    css = [widgets.CSSLink('hvz', 'fieldlist.css')]
    javascript = [widgets.mochikit, widgets.JSLink('hvz', 'fieldlist.js')]
    params = ['attrs']
    params_doc = {'attrs' : "Dictionary containing extra (X)HTML attributes "
                            "for the field list's parent tag"}
    attrs = {}

def _get_date_col(row, column):
    column = column.lstrip('_')
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
    default_columns = ['game_id', 'display_name', '_created', 'player_count']
    exclude_sorting = ['player_count']
    column_titles = {'game_id': _("ID"),
                     'display_name': _("Name"),
                     '_created': _("Created"),
                     '_started': _("Started"),
                     '_ended': _("Ended"),
                     'player_count': _("Players"),}
    accessors = {'game_id': '_get_link_col',
                 'display_name': '_get_link_col',
                 'player_count': (lambda r, c: len(r.entries)),
                 '_created': _get_date_col,
                 '_started': _get_date_col,
                 '_ended': _get_date_col,
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
    default_columns = ['name', 'affiliation', '_death_date',
                       '_feed_date', 'kills']
    exclude_sorting = ['affiliation',
                       '_death_date',
                       '_feed_date',
                       '_starve_date',
                       'kills',
                       'edit',]
    column_titles = {'player_gid': _("Game ID"),
                     'name': _("Player Name"),
                     '_death_date': _("Death Date"),
                     '_feed_date': _("Feed Date"),
                     '_starve_date': _("Starve Date"),
                     'kills': _("Kills"),
                     'affiliation': _("Affiliation"),
                     'edit': _("Edit"),}
    accessors = {'name': '_get_name_col',
                 'affiliation': '_get_affiliation_col',
                 '_death_date': '_get_oz_date_col',
                 '_feed_date': '_get_oz_date_col',
                 '_starve_date': '_get_oz_date_col',
                 'kills': '_get_kills_col',
                 'edit': '_get_edit_col',
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
        if not self.show_oz and row.is_original_zombie:
            return row.STATE_NAMES[PlayerEntry.STATE_HUMAN]
        else:
            return row.affiliation
    
    def _get_oz_date_col(self, row, column):
        if not self.show_oz and row.is_original_zombie:
            return u""
        else:
            return _get_date_col(row, column)
    
    def _get_kills_col(self, row, column):
        if not self.show_oz and row.is_original_zombie:
            return 0
        else:
            return self.default_accessor(row, column)
    
    def _get_edit_col(self, row, column):
        link = Element("{http://www.w3.org/1999/xhtml}a",
                       href=url('/game/editentry', entry_id=row.entry_id))
        link.text = _("Edit")
        return link

class UserList(CustomDataGrid):
    name = "user_list"
    grid_class = "custom_grid user_list"
    default_columns = ['display_name', '_created']
    column_titles = {'user_id': _("UID"),
                     'user_name': _("Login"),
                     'email_address': _("Email"),
                     'display_name': _("Name"),
                     '_created': _("Joined"),}
    accessors = {'display_name': '_get_display_name_col',
                 '_created': _get_date_col,
                 '*': 'default_accessor'}
    no_data_msg = _("No users yet")
    
    @staticmethod
    def _get_display_name_col(row, column):
        link = Element("{http://www.w3.org/1999/xhtml}a",
                       href=util.user_link(row))
        link.text = row.display_name
        return link
