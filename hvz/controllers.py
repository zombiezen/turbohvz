#!/usr/bin/env python
#
#   controllers.py
#   HvZ
#

import logging

import cherrypy
import turbogears
from turbogears import error_handler, expose, url, identity, validate
from turbogears.database import session
from turbogears.paginate import paginate

from hvz import model, util, widgets #, json

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__all__ = ['log',
           'Root',]

log = logging.getLogger("hvz.controllers")

class GameController(turbogears.controllers.Controller):
    @expose("hvz.templates.game.index")
    @paginate('games', default_order='-game_id')
    def index(self):
        all_games = session.query(model.Game)
        grid = widgets.GameList()
        return dict(games=all_games,
                    grid=grid,)
    
    @expose("hvz.templates.game.view")
    def view(self, game_id):
        game_id = int(game_id)
        requested_game = model.Game.get(game_id)
        if requested_game is not None:
            oz = requested_game.revealed_original_zombie
            grid = widgets.EntryList(show_oz=oz)
            return dict(game=requested_game,
                        grid=grid,)
        else:
            raise ValueError("404")
    
    @expose("hvz.templates.game.reportkill")
    @identity.require(identity.not_anonymous())
    def reportkill(self, game_id):
        game_id = int(game_id)
        requested_game = model.Game.get(game_id)
        if requested_game is not None:
            return dict(game=requested_game,
                        form=widgets.kill_form,)
        else:
            raise ValueError("404")
    
    @expose("hvz.templates.game.join")
    @identity.require(identity.not_anonymous())
    def join(self, game_id):
        game_id = int(game_id)
        requested_game = model.Game.get(game_id)
        if requested_game is not None:
            return dict(game=requested_game,
                        form=widgets.join_form,)
        else:
            raise ValueError("404")
    
    @expose("hvz.templates.game.create")
    # TODO: require admin
    @identity.require(identity.not_anonymous())
    def create(self):
        return dict()
    
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
    @identity.require(identity.not_anonymous()) # TODO: Admin
    @error_handler(view)
    @validate(validators=widgets.StageSchema)
    def action_stage(self, game_id, btnPrev=None, btnNext=None):
        user = identity.current.user
        game_id = int(game_id)
        requested_game = model.Game.get(game_id)
        if requested_game is not None:
            if btnNext:
                requested_game.next_state()
            elif btnPrev:
                requested_game.previous_state()
            link = util.game_link(game_id, redirect=True) + '#sect_stage'
            raise turbogears.redirect(link)
        else:
            raise ValueError("404")
    
    @expose()
    @identity.require(identity.not_anonymous())
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
    # TODO: require admin
    @identity.require(identity.not_anonymous())
    def action_create(self):
        new_game = model.Game()
        session.flush()
        raise turbogears.redirect(util.game_link(new_game, redirect=True))

class Root(turbogears.controllers.RootController):
    def __init__(self):
        self.game = GameController()
    
    @expose("hvz.templates.welcome")
    # @identity.require(identity.in_group("admin"))
    def index(self):
        import time
        # log.debug("Happy TurboGears Controller Responding For Duty")
        turbogears.flash("Your application is now running")
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
            msg = _("The credentials you supplied were not correct or "
                   "did not grant access to this resource.")
        elif identity.get_identity_errors():
            msg = _("You must provide your credentials before accessing "
                   "this resource.")
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

