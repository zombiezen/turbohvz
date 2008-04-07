#!/usr/bin/env python
#
#   controllers.py
#   HvZ
#

import logging
import random

import cherrypy
import turbogears
from turbogears import error_handler, expose, url, identity, validate
from turbogears.database import session
from turbogears.paginate import paginate

from hvz import model, util, widgets #, json

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__all__ = ['log',
           'GameController',
           'UserController',
           'Root',]

log = logging.getLogger("hvz.controllers")

class GameController(turbogears.controllers.Controller):
    @staticmethod
    def _get_current_entry(game):
        user = identity.current.user
        if user is not None:
            return model.PlayerEntry.by_player(game, user)
        else:
            return None
    
    @expose("hvz.templates.game.index")
    @paginate('games', default_order='-game_id')
    def index(self):
        all_games = session.query(model.Game)
        grid = widgets.GameList(sortable=True)
        pager = widgets.Pager()
        return dict(games=all_games,
                    grid=grid,
                    pager=pager,)
    
    @expose("hvz.templates.game.view")
    def view(self, game_id):
        game_id = int(game_id)
        requested_game = model.Game.get(game_id)
        perms = identity.current.permissions
        if requested_game is not None:
            entry = self._get_current_entry(requested_game)
            # Determine which columns to show
            columns = list(widgets.EntryList.default_columns)
            if 'view-player-gid' in perms:
                columns.insert(0, 'player_gid')
            # Determine whether to show original zombie
            oz = requested_game.revealed_original_zombie
            if entry is not None:
                is_oz = entry.state == model.PlayerEntry.STATE_ORIGINAL_ZOMBIE
            else:
                is_oz = False
            can_view_oz = bool('view-original-zombie' in perms)
            # Create widgets
            grid = widgets.EntryList(columns=columns,
                                     show_oz=(oz or is_oz or can_view_oz),)
            return dict(game=requested_game,
                        grid=grid,
                        current_entry=entry,)
        else:
            raise ValueError("404")
    
    @expose("hvz.templates.game.reportkill")
    @identity.require(identity.not_anonymous())
    def reportkill(self, game_id):
        game_id = int(game_id)
        requested_game = model.Game.get(game_id)
        if requested_game is not None:
            entry = self._get_current_entry(requested_game)
            return dict(game=requested_game,
                        form=widgets.kill_form,
                        current_entry=entry,)
        else:
            raise ValueError("404")
    
    @expose("hvz.templates.game.join")
    @identity.require(identity.has_permission('join-game'))
    def join(self, game_id):
        game_id = int(game_id)
        requested_game = model.Game.get(game_id)
        if requested_game is not None:
            return dict(game=requested_game,
                        form=widgets.join_form,)
        else:
            raise ValueError("404")
    
    @expose("hvz.templates.game.create")
    @identity.require(identity.has_permission('create-game'))
    def create(self):
        return dict()
    
    @expose("hvz.templates.game.choose_oz")
    @identity.require(identity.has_permission('stage-game'))
    def choose_oz(self, game_id):
        game_id = int(game_id)
        requested_game = model.Game.get(game_id)
        if requested_game is not None:
            # Build option list
            pool = requested_game.original_zombie_pool
            options = [(e.entry_id, e.player.display_name) for e in pool]
            options.insert(0, ("random", _("Random")))
            # Pass off to template
            return dict(game=requested_game,
                        options=options,
                        form=widgets.original_zombie_form,)
        else:
            raise ValueError("404")
    
    @expose()
    @identity.require(identity.not_anonymous())
    @error_handler(reportkill)
    @validate(widgets.kill_form)
    def action_kill(self, game_id, victim_id, kill_date):
        user = identity.current.user
        kill_date = model.as_local(kill_date)
        game_id = int(game_id)
        requested_game = model.Game.get(game_id)
        if requested_game is not None:
            if not requested_game.in_progress:
                raise ValueError("Game has not started")
            # Retrieve killer and victim
            killer = model.PlayerEntry.by_player(requested_game, user)
            if killer is None:
                raise ValueError("You are not a part of this game")
            victim = model.PlayerEntry.by_player_gid(requested_game,
                                                     victim_id)
            if victim is None:
                raise ValueError("Invalid victim")
            # Kill user in question
            killer.kill(victim, kill_date)
            # Log it and return to game
            log.info("OMG, %s killed %s!  Those idiots!", killer, victim)
            link = util.game_link(game_id, redirect=True) + '#sect_entry_list'
            raise turbogears.redirect(link)
        else:
            raise ValueError("404")
    
    @expose()
    @identity.require(identity.has_permission('stage-game'))
    @error_handler(view)
    @validate(validators=widgets.StageSchema)
    def action_stage(self, game_id, btnPrev=None, btnNext=None):
        user = identity.current.user
        game_id = int(game_id)
        requested_game = model.Game.get(game_id)
        if requested_game is not None:
            if btnNext:
                next_state = requested_game.state + 1
                if next_state == model.Game.STATE_CHOOSE_ZOMBIE:
                    link = util.game_link(game_id, 'choose_oz')
                    raise turbogears.redirect(link)
                requested_game.next_state()
            elif btnPrev:
                requested_game.previous_state()
            link = util.game_link(game_id, redirect=True) + '#sect_stage'
            raise turbogears.redirect(link)
        else:
            raise ValueError("404")
    
    @expose()
    @identity.require(identity.has_permission('join-game'))
    @error_handler(join)
    @validate(widgets.join_form)
    def action_join(self, game_id, original_pool=False):
        user = identity.current.user
        game_id = int(game_id)
        requested_game = model.Game.get(game_id)
        if requested_game is not None:
            if not requested_game.registration_open:
                raise ValueError("Registration is closed")
            entry = model.PlayerEntry(requested_game, user)
            entry.original_pool = original_pool
            link = util.game_link(game_id, redirect=True) + '#sect_entry_list'
            raise turbogears.redirect(link)
        else:
            raise ValueError("404")
    
    @expose()
    @identity.require(identity.not_anonymous())
    def action_unjoin(self, game_id):
        user = identity.current.user
        game_id = int(game_id)
        requested_game = model.Game.get(game_id)
        if requested_game is not None:
            if not requested_game.registration_open:
                raise ValueError("Registration is closed")
            entry = model.PlayerEntry.by_player(requested_game, user)
            session.delete(entry)
            link = util.game_link(game_id, redirect=True) + '#sect_entry_list'
            raise turbogears.redirect(link)
        else:
            raise ValueError("404")
    
    @expose()
    @identity.require(identity.has_permission('create-game'))
    def action_create(self):
        new_game = model.Game()
        session.flush()
        raise turbogears.redirect(util.game_link(new_game, redirect=True))
    
    @expose()
    @identity.require(identity.has_permission('stage-game'))
    @error_handler(choose_oz)
    @validate(widgets.original_zombie_form)
    def action_oz(self, game_id, original_zombie):
        game_id = int(game_id)
        requested_game = model.Game.get(game_id)
        if requested_game is not None:
            # Check if we're in the right state
            if (requested_game.state + 1) != model.Game.STATE_CHOOSE_ZOMBIE:
                raise ValueError("Game is not choosing original zombie")
            # Determine zombie
            pool = requested_game.original_zombie_pool
            if original_zombie == 'random':
                entry = random.choice(pool)
            else:
                entry = model.PlayerEntry.get(original_zombie)
                if entry not in pool:
                    raise ValueError("Original zombie is not a valid choice")
            # Make into zombie
            entry.state = model.PlayerEntry.STATE_ORIGINAL_ZOMBIE
            # Advance stage
            requested_game.next_state()
            # Go back to game page
            turbogears.flash(_("Original zombie is %s") % unicode(entry))
            link = util.game_link(requested_game, redirect=True)
            raise turbogears.redirect(link)
        else:
            raise ValueError("404")

class UserController(turbogears.controllers.Controller):
    @expose("hvz.templates.user.index")
    @paginate('users', default_order='display_name')
    def index(self):
        all_users = session.query(model.User)
        grid = widgets.UserList(sortable=True)
        pager = widgets.Pager()
        return dict(users=all_users,
                    grid=grid,
                    pager=pager,)
    
    @expose("hvz.templates.user.view")
    def view(self, user_id):
        if user_id.isdigit():
            requested_user = model.User.query.get(user_id)
        else:
            requested_user = model.User.by_user_name(user_id)
        if requested_user is not None:
            return dict(user=requested_user,)
        else:
            raise ValueError("404")
    
    @expose("hvz.templates.user.register")
    def register(self):
        return dict(form=widgets.register_form,)
    
    @expose()
    @error_handler(register)
    @validate(widgets.register_form)
    def action_register(self, user_name, display_name, email_address,
                        password1, password2, profile):
        # Determine group
        group_config = turbogears.config.get("hvz.default_group", "player")
        if group_config is None:
            groups = []
        elif isinstance(group_config, basestring):
            groups = [model.Group.by_group_name(group_config)]
        elif isinstance(group_config, (list, tuple)):
            groups = [model.Group.by_group_name(name) for name in group_config]
        else:
            raise Value
        # Create user
        new_user = model.User(user_name, display_name,
                              email_address, password1)
        if profile:
            new_user.profile = profile
        for group in groups:
            group.add_user(new_user)
        session.flush()
        # Handle interface
        msg = _("Your account has been created, %s.") % (unicode(new_user))
        turbogears.flash(msg)
        raise turbogears.redirect('/')

class Root(turbogears.controllers.RootController):
    def __init__(self):
        self.game = GameController()
        self.user = UserController()
    
    @expose("hvz.templates.welcome")
    # @identity.require(identity.in_group("admin"))
    def index(self):
        import time
        return dict(now=time.ctime())
    
    @expose("hvz.templates.rules")
    def rules(self):
        return dict()
    
    @expose("hvz.templates.login")
    def login(self, forward_url=None, previous_url=None, *args, **kw):
        if not identity.current.anonymous and \
           identity.was_login_attempted() and \
           not identity.get_identity_errors():
            raise turbogears.redirect(url(forward_url or previous_url or '/', kw))
        forward_url = None
        previous_url = cherrypy.request.path
        if identity.was_login_attempted():
            msg = _("Your login was not correct or did not grant access to "
                    "this resource.")
        elif identity.get_identity_errors():
            msg = _("You are not currently authorized to view this resource.")
        else:
            msg = _("Please log in.")
            forward_url = cherrypy.request.headers.get("Referer", "/")
        cherrypy.response.status = 403
        return dict(message=msg,
                    previous_url=previous_url,
                    logging_in=True,
                    original_parameters=cherrypy.request.params,
                    forward_url=forward_url,)
    
    @expose()
    def logout(self):
        identity.current.logout()
        raise turbogears.redirect("/")
