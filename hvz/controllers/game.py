#!/usr/bin/env python
#
#   controllers/game.py
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

import random

import cherrypy
import turbogears
from turbogears import error_handler, expose, url, identity, validate
from turbogears.database import session
from turbogears.paginate import paginate

from hvz import forms, model, util, widgets #, json
from hvz.controllers import base
from hvz.model.game import PlayerEntry, Game

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__all__ = ['GameController']

class GameController(base.BaseController):
    @staticmethod
    def _get_current_entry(game):
        user = identity.current.user
        if user is not None:
            return PlayerEntry.by_player(game, user)
        else:
            return None
    
    @expose("hvz.templates.game.index")
    @paginate('games', default_order='-game_id')
    def index(self):
        all_games = session.query(Game)
        grid = widgets.GameList(sortable=True)
        pager = widgets.Pager()
        return dict(games=all_games,
                    grid=grid,
                    pager=pager,)
    
    @expose("hvz.templates.game.view")
    def view(self, game_id):
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        perms = identity.current.permissions
        if requested_game is None:
            raise base.NotFound()
        # Update game
        requested_game.update()
        # Find user's entry, if he/she has one
        entry = self._get_current_entry(requested_game)
        # Determine which columns to show
        columns = list(widgets.EntryList.default_columns)
        if 'view-player-gid' in perms:
            columns.insert(0, 'player_gid')
        # Determine whether to show original zombie
        oz = requested_game.revealed_original_zombie
        if entry is not None:
            is_oz = entry.state == PlayerEntry.STATE_ORIGINAL_ZOMBIE
        else:
            is_oz = False
        can_view_oz = bool('view-oz' in perms)
        # Create widgets
        grid = widgets.EntryList(columns=columns,
                                 show_oz=(oz or is_oz or can_view_oz),)
        entries = sorted(requested_game.entries,
                         key=(lambda e: e.player.display_name))
        # Calculate server time and timezone
        current_time = model.dates.now()
        offset = model.dates.to_local(current_time).utcoffset()
        days, seconds = offset.days, offset.seconds
        if days < 0:
            tz_sign = "-"
        else:
            tz_sign = "+"
        total_offset = abs(days * (60 * 60 * 24) + seconds)
        tz_hours, extra_offset = divmod(total_offset, 60 * 60)
        tz_minutes = extra_offset // 60
        # Return template variables
        return dict(game=requested_game,
                    grid=grid,
                    current_entry=entry,
                    entries=entries,
                    current_time=current_time,
                    tz_sign=tz_sign,
                    tz_hours=tz_hours,
                    tz_minutes=tz_minutes,)
    
    @expose("hvz.templates.game.edit")
    @identity.require(identity.has_permission('edit-game'))
    def edit(self, game_id):
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        values = {}
        for field in forms.game_form.fields:
            name = field.name
            values[name] = getattr(requested_game, name)
        return dict(game=requested_game,
                    form=forms.game_form,
                    values=values,)
    
    @expose("hvz.templates.game.reportkill")
    @identity.require(identity.not_anonymous())
    def reportkill(self, game_id):
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        entry = self._get_current_entry(requested_game)
        default_time = model.dates.to_local(model.dates.now())
        return dict(game=requested_game,
                    form=forms.kill_form,
                    current_entry=entry,
                    default_time=default_time,)
    
    @expose("hvz.templates.game.join")
    @identity.require(identity.has_permission('join-game'))
    def join(self, game_id):
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        return dict(game=requested_game,
                    form=forms.join_form,)
    
    @expose("hvz.templates.game.create")
    @identity.require(identity.has_permission('create-game'))
    def create(self):
        return dict(form=forms.game_form,)
    
    @expose("hvz.templates.game.choose_oz")
    @identity.require(identity.has_permission('stage-game'))
    def choose_oz(self, game_id):
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        # Build option list
        pool = requested_game.original_zombie_pool
        options = [(e.entry_id, e.player.display_name) for e in pool]
        options.insert(0, ("random", _("Random")))
        # Pass off to template
        return dict(game=requested_game,
                    options=options,
                    form=forms.original_zombie_form,)
    
    @expose("hvz.templates.game.rules")
    def rules(self, game_id):
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        return dict(game=requested_game)
    
    @expose()
    @identity.require(identity.not_anonymous())
    @error_handler(reportkill)
    @validate(forms.kill_form)
    def action_kill(self, game_id, victim_id, kill_date):
        user = identity.current.user
        kill_date = model.dates.as_local(kill_date)
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        # Retrieve killer and victim
        killer = PlayerEntry.by_player(requested_game, user)
        if killer is None:
            msg = _("You are not a part of this game")
            raise model.errors.PlayerNotFoundError(requested_game, msg)
        victim = PlayerEntry.by_player_gid(requested_game, victim_id)
        if victim is None:
            raise model.errors.PlayerNotFoundError(requested_game,
                                            _("Invalid victim"))
        # Kill user in question
        killer.kill(victim, kill_date)
        # Log it and return to game
        base.log.info("OMG, %s killed %s!  Those idiots!", killer, victim)
        link = util.game_link(game_id, redirect=True) + '#sect_entry_list'
        raise turbogears.redirect(link)
    
    @expose()
    @identity.require(identity.has_permission('stage-game'))
    @error_handler(view)
    @validate(validators=forms.StageSchema)
    def action_stage(self, game_id, btnPrev=None, btnNext=None):
        user = identity.current.user
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        if btnNext:
            next_state = requested_game.state + 1
            if next_state == Game.STATE_CHOOSE_ZOMBIE:
                link = util.game_link(game_id, 'choose_oz', redirect=True)
                raise turbogears.redirect(link)
            requested_game.next_state()
        elif btnPrev:
            requested_game.previous_state()
        link = util.game_link(game_id, redirect=True) + '#sect_stage'
        raise turbogears.redirect(link)
    
    @expose()
    @identity.require(identity.has_permission('join-game'))
    @error_handler(join)
    @validate(forms.join_form)
    def action_join(self, game_id, original_pool=False):
        user = identity.current.user
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        if not requested_game.registration_open:
            raise model.errors.WrongStateError(requested_game,
                                               requested_game.state,
                                               Game.STATE_OPEN,
                                               _("Registration is closed"))
        entry = PlayerEntry(requested_game, user)
        entry.original_pool = original_pool
        link = util.game_link(game_id, redirect=True) + '#sect_entry_list'
        raise turbogears.redirect(link)
    
    @expose()
    @identity.require(identity.not_anonymous())
    def action_unjoin(self, game_id):
        user = identity.current.user
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        if not requested_game.registration_open:
            raise model.errors.WrongStateError(requested_game,
                                               requested_game.state,
                                               Game.STATE_OPEN,
                                               _("Registration is closed"))
        entry = PlayerEntry.by_player(requested_game, user)
        session.delete(entry)
        link = util.game_link(game_id, redirect=True) + '#sect_entry_list'
        raise turbogears.redirect(link)
    
    @expose()
    @identity.require(identity.has_permission('create-game'))
    @error_handler(create)
    @validate(forms.game_form)
    def action_create(self, game_id, display_name,
                      gid_length,
                      zombie_starve_time,
                      zombie_report_time,
                      ignore_weekdays,
                      ignore_dates,
                      safe_zones,
                      rules_notes,):
        assert not game_id
        new_game = Game(display_name)
        new_game.gid_length = gid_length
        new_game.zombie_starve_time = zombie_starve_time
        new_game.zombie_report_time = zombie_report_time
        new_game.ignore_weekdays = ignore_weekdays
        new_game.ignore_dates = ignore_dates
        new_game.safe_zones = safe_zones
        new_game.rules_notes = rules_notes
        session.flush()
        turbogears.flash(_("Game created"))
        raise turbogears.redirect(util.game_link(new_game, redirect=True))
    
    @expose()
    @identity.require(identity.has_permission('edit-game'))
    @error_handler(edit)
    @validate(forms.game_form)
    def action_edit(self, game_id, display_name,
                    gid_length,
                    zombie_starve_time,
                    zombie_report_time,
                    ignore_weekdays,
                    ignore_dates,
                    safe_zones,
                    rules_notes,):
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        requested_game.display_name = display_name
        requested_game.gid_length = gid_length
        requested_game.zombie_starve_time = zombie_starve_time
        requested_game.zombie_report_time = zombie_report_time
        requested_game.ignore_weekdays = ignore_weekdays
        requested_game.ignore_dates = ignore_dates
        requested_game.safe_zones = safe_zones
        requested_game.rules_notes = rules_notes
        session.flush()
        turbogears.flash(_("Game updated"))
        raise turbogears.redirect(util.game_link(requested_game,
                                                 redirect=True))
    
    @expose()
    @identity.require(identity.has_permission('delete-game'))
    def action_delete(self, game_id):
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        requested_game.delete()
        session.flush()
        turbogears.flash(_("Game deleted"))
        raise turbogears.redirect('/game/index')
    
    @expose()
    @identity.require(identity.has_permission('stage-game'))
    @error_handler(choose_oz)
    @validate(forms.original_zombie_form)
    def action_oz(self, game_id, original_zombie):
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        # Check if we're in the right state
        if (requested_game.state + 1) != Game.STATE_CHOOSE_ZOMBIE:
            msg = _("Game is not choosing original zombie")
            raise model.errors.WrongStateError(requested_game,
                                               requested_game.state,
                                               Game.STATE_CHOOSE_ZOMBIE - 1,
                                               msg)
        # Determine zombie
        pool = requested_game.original_zombie_pool
        if original_zombie == 'random':
            entry = random.choice(pool)
        else:
            entry = PlayerEntry.query.get(original_zombie)
            if entry not in pool:
                msg = _("Original zombie is not a valid choice")
                raise PlayerNotFoundError(requested_game, msg)
        # Make into zombie
        requested_game.original_zombie = entry
        # Advance stage
        requested_game.next_state()
        # Go back to game page
        turbogears.flash(_("Original zombie chosen"))
        link = util.game_link(requested_game, redirect=True)
        raise turbogears.redirect(link)
