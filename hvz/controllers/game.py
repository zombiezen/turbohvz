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

from __future__ import division
from datetime import datetime
import random

import cherrypy
import turbogears
from turbogears import error_handler, expose, url, identity, validate
from turbogears.database import session
from turbogears.paginate import paginate

from hvz import charts, email, forms, model, util, widgets #, json
from hvz.controllers import base
from hvz.model.errors import PlayerNotFoundError
from hvz.model.game import PlayerEntry, Game

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__all__ = ['GameController']

def _get_seconds(delta):
    return delta.days * 24 * 60 * 60 + delta.seconds

class GameController(base.BaseController):
    @staticmethod
    def _get_current_entry(game):
        user = identity.current.user
        if user is not None:
            return PlayerEntry.by_player(game, user)
        else:
            return None
    
    @expose("hvz.templates.game.index")
    @paginate('games', limit=20, default_order='-game_id')
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
        if 'edit-entry' in perms:
            columns.append('edit')
        # Determine whether to show original zombie
        oz = requested_game.revealed_original_zombie
        if entry is not None:
            is_oz = entry.state == PlayerEntry.STATE_ORIGINAL_ZOMBIE
        else:
            is_oz = False
        can_view_oz = bool('view-oz' in perms)
        # Find factions
        humans = [e.player for e in requested_game.entries if e.is_human]
        zombies = [e.player for e in requested_game.entries if e.is_undead]
        infected = [e.player for e in requested_game.entries if e.is_infected]
        starved = [e.player for e in requested_game.entries if e.is_dead]
        # Create widgets
        grid = widgets.EntryList(columns=columns,
                                 show_oz=(oz or is_oz or can_view_oz),)
        entries = sorted(requested_game.entries,
                         key=(lambda e: e.player.display_name))
        # Create charts
        if (turbogears.config.get('hvz.show_charts', True) and
            requested_game.in_progress):
            # Create data
            chart_data = [len(humans),
                          len(zombies),
                          len(infected),
                          len(starved)]
            chart_labels = [_("Humans (%i)") % len(humans),
                            _("Zombies (%i)") % len(zombies),
                            _("Infected (%i)") % len(infected),
                            _("Starved (%i)") % len(starved),]
            chart_colors = ['ff0000',
                            'cccccc',
                            '00CC00',
                            '333333',]
            # Remove empty statistics
            i = 0
            while True:
                try:
                    i = chart_data.index(0, i)
                except ValueError:
                    break
                else:
                    del chart_data[i], chart_labels[i], chart_colors[i]
            # Generate chart
            player_chart = charts.PieChart(chart_data,
                                           title=_("Player Statistics"),
                                           labels=chart_labels,
                                           colors=chart_colors,
                                           pie3D=True,)
            # Determine whether we need starve meter
            if entry is not None and entry.is_undead:
                time = entry.calculate_time_before_starving()
                elapsed_sec = _get_seconds(time)
                max_sec = _get_seconds(requested_game.zombie_starve_timedelta)
                starve_meter = charts.GoogleOMeter(
                    [elapsed_sec / max_sec * 100],
                    colors=['ff0000', 'ffff00', '00ff00'])
            else:
                starve_meter = None
        else:
            player_chart = None
            starve_meter = None
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
        # Find email addresses
        all_emails = [e.player.email_address
                      for e in requested_game.entries]
        human_emails = [player.email_address for player in humans]
        zombie_emails = [player.email_address for player in zombies]
        starved_emails = [player.email_address for player in starved]
        # Return template variables
        return dict(game=requested_game,
                    grid=grid,
                    current_entry=entry,
                    entries=entries,
                    current_time=current_time,
                    tz_sign=tz_sign,
                    tz_hours=tz_hours,
                    tz_minutes=tz_minutes,
                    all_emails=all_emails,
                    human_emails=human_emails,
                    zombie_emails=zombie_emails,
                    starved_emails=starved_emails,
                    player_chart=player_chart,
                    starve_meter=starve_meter,)
    
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
    
    @expose("hvz.templates.game.editentry")
    @identity.require(identity.has_permission('edit-entry'))
    def editentry(self, entry_id):
        entry_id = int(entry_id)
        requested_entry = PlayerEntry.query.get(entry_id)
        if requested_entry is None:
            raise base.NotFound()
        values = {}
        for field in forms.edit_entry_form.fields:
            name = field.name
            new_value = getattr(requested_entry, name)
            if new_value is None:
                values[name] = u''
            elif isinstance(new_value, datetime):
                values[name] = model.dates.to_local(new_value)
            else:
                values[name] = new_value
        return dict(entry=requested_entry,
                    form=forms.edit_entry_form,
                    values=values,)
    
    @expose("hvz.templates.game.reportkill")
    @identity.require(identity.not_anonymous())
    def reportkill(self, game_id):
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        requested_game.update()
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
    
    @expose("hvz.templates.game.rules.goucher")
    def rules(self, game_id):
        game_id = int(game_id)
        requested_game = Game.query.get(game_id)
        if requested_game is None:
            raise base.NotFound()
        if turbogears.config.get('hvz.goucher_rules', True):
            template = "hvz.templates.game.rules.goucher"
        else:
            template = "hvz.templates.game.rules.high_school"
        return dict(tg_template=template,
                    game=requested_game)
    
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
        # Update the game state
        requested_game.update()
        # Retrieve killer and victim
        killer = PlayerEntry.by_player(requested_game, user)
        if killer is None:
            msg = _("You are not a part of this game")
            raise PlayerNotFoundError(requested_game, msg)
        victim = PlayerEntry.by_player_gid(requested_game, victim_id)
        if victim is None:
            raise PlayerNotFoundError(requested_game, _("Invalid victim"))
        # Kill user in question
        killer.kill(victim, kill_date)
        # Log it
        base.log.info("<Game %i> %r killed %r!",
                      game_id, killer, victim)
        # Send out email
        recipients = [entry.player.email_address
                      for entry in requested_game.entries]
        subject = _("HvZ: \"%s\": %s is a zombie") % \
                       (requested_game.display_name,
                        victim.player.display_name)
        notif_vars = dict(game=requested_game,
                          killer=killer,
                          victim=victim,
                          kill_date=kill_date,)
        email.sendmail(recipients, subject,
                       "hvz.templates.mail.zombienotif",
                       notif_vars)
        # Send out SMS
        numbers = [(entry.player.cell_number, entry.player.cell_provider)
                   for entry in requested_game.entries
                   if entry.notify_sms and entry.player.cell_number]
        email.send_sms(numbers, subject,
                       "hvz.templates.mail.zombienotif",
                       notif_vars)
        # Return to game
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
            if requested_game.state == Game.STATE_STARTED:
                # Send out email
                recipients = [entry.player.email_address
                              for entry in requested_game.entries]
                email.sendmail(recipients,
                               _("HvZ: \"%s\" Started" %
                                   (requested_game.display_name)),
                               "hvz.templates.mail.gamestarted",
                               dict(game=requested_game,))
            base.log.info("<Game %i> Next Stage %i -> %i",
                          game_id, next_state - 1, next_state)
        elif btnPrev:
            requested_game.previous_state()
            base.log.info("<Game %i> Previous Stage %i -> %i",
                          game_id, requested_game.state + 1,
                          requested_game.state)
        link = util.game_link(game_id, redirect=True) + '#sect_stage'
        raise turbogears.redirect(link)
    
    @expose()
    @identity.require(identity.has_permission('join-game'))
    @error_handler(join)
    @validate(forms.join_form)
    def action_join(self, game_id, original_pool=False, notify_sms=False):
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
        entry.notify_sms = notify_sms
        session.flush()
        base.log.info("<Game %i> %r joined", game_id, entry)
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
        entry.delete()
        base.log.info("<Game %i> %r unjoined", game_id, user)
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
                      human_undead_time,
                      ignore_weekdays,
                      ignore_dates,
                      safe_zones,
                      rules_notes,):
        assert not game_id
        new_game = Game(display_name)
        new_game.gid_length = gid_length
        new_game.zombie_starve_time = zombie_starve_time
        new_game.zombie_report_time = zombie_report_time
        new_game.human_undead_time = human_undead_time
        new_game.ignore_weekdays = ignore_weekdays
        new_game.ignore_dates = ignore_dates
        new_game.safe_zones = safe_zones
        new_game.rules_notes = rules_notes
        session.flush()
        base.log.info("<Game %i> Created", game_id)
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
                    human_undead_time,
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
        requested_game.human_undead_time = human_undead_time
        requested_game.ignore_weekdays = ignore_weekdays
        requested_game.ignore_dates = ignore_dates
        requested_game.safe_zones = safe_zones
        requested_game.rules_notes = rules_notes
        session.flush()
        base.log.info("<Game %i> Updated", game_id)
        turbogears.flash(_("Game updated"))
        raise turbogears.redirect(util.game_link(requested_game,
                                                 redirect=True))
    
    @expose()
    @identity.require(identity.has_permission('edit-entry'))
    @error_handler(editentry)
    @validate(forms.edit_entry_form)
    def action_editentry(self, entry_id,
                         state, kills, death_date, feed_date, starve_date,
                         original_pool=False,
                         notify_sms=False,):
        entry_id = int(entry_id)
        requested_entry = PlayerEntry.query.get(entry_id)
        if requested_entry is None:
            raise base.NotFound()
        # Update parameters
        if death_date:
            death_date = model.dates.as_local(death_date)
        if feed_date:
            feed_date = model.dates.as_local(feed_date)
        if starve_date:
            starve_date = model.dates.as_local(starve_date)
        # Update entry
        requested_entry.state = state
        requested_entry.kills = kills
        requested_entry.death_date = death_date
        requested_entry.feed_date = feed_date
        requested_entry.starve_date = starve_date
        requested_entry.original_pool = original_pool
        requested_entry.notify_sms = notify_sms
        session.flush()
        # Go back to game page
        base.log.info("<Entry %i;%i:%s> Updated",
                      entry_id, requested_entry.game.game_id,
                      requested_entry.player_gid)
        turbogears.flash(_("Player updated"))
        raise turbogears.redirect(util.game_link(requested_entry.game,
                                                 redirect=True))
    
    @expose()
    @identity.require(identity.has_permission('edit-entry'))
    def action_entryquick(self, entry_id, action):
        entry_id = int(entry_id)
        requested_entry = PlayerEntry.query.get(entry_id)
        if requested_entry is None:
            raise base.NotFound()
        # Perform requested action
        actions = {'human': requested_entry.force_to_human,
                   'infected': requested_entry.force_to_infected,
                   'zombie': requested_entry.force_to_zombie,
                   'dead': requested_entry.force_to_dead,}
        func = actions.get(action)
        if func is not None:
            func()
        else:
            raise ValueError("Invalid action given")
        # Go back to game page
        base.log.info("<Entry %i;%i:%s> Changed to: %s",
                      entry_id, requested_entry.game.game_id,
                      requested_entry.player_gid, action)
        turbogears.flash(_("Player updated"))
        raise turbogears.redirect(util.game_link(requested_entry.game,
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
        base.log.info("<Game %i> Deleted", game_id)
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
        # Log change
        base.log.info("<Game %i> OZ Chosen %r", game_id, entry)
        # Send out email
        email.sendmail(entry.player.email_address,
                       _("HvZ: You are the original zombie"),
                       "hvz.templates.mail.oznotif",
                       dict(game=requested_game,
                            entry=entry))
        # Go back to game page
        turbogears.flash(_("Original zombie chosen"))
        link = util.game_link(requested_game, redirect=True)
        raise turbogears.redirect(link)
