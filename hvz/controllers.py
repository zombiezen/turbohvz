#!/usr/bin/env python
#
#   controllers.py
#   HvZ
#

import logging

import cherrypy
import turbogears
from turbogears import expose, url, identity, redirect
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
        requested_game = model.Game.get(game_id)
        if requested_game is not None:
            grid = widgets.EntryList()
            return dict(game=requested_game,
                        grid=grid,)
        else:
            raise ValueError("404")

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
    
    @expose("hvz.templates.login")
    def login(self, forward_url=None, previous_url=None, *args, **kw):
        if not identity.current.anonymous and \
           identity.was_login_attempted() and \
           not identity.get_identity_errors():
            raise redirect(url(forward_url or previous_url or '/', kw))
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
        raise redirect("/")

