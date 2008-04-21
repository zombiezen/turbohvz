#!/usr/bin/env python
#
#   controllers/base.py
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

import logging

import cherrypy
import turbogears
from turbogears import error_handler, expose, url, identity, validate
from turbogears.database import session

from hvz import forms, model, util, widgets #, json

__author__ = 'Ross Light'
__date__ = 'April 18, 2008'
__all__ = ['log',
           'manual_login',
           'NotFound',
           'BaseController',
           'Root',]

log = logging.getLogger("hvz.controllers")

def manual_login(user):
    # Log in user
    identity_object = identity.current_provider.authenticated_identity(user)
    key = turbogears.visit.current().key
    identity_object.visit_key = key
    identity.set_current_identity(identity_object)
    # Associate with session
    visit_link = model.identity.VisitIdentity.query.get(key)
    if visit_link is None:
        visit_link = model.identity.VisitIdentity()
        visit_link.visit_key = key
        visit_link.user = user
        session.save(visit_link)
    else:
        visit_link.user = user

class NotFound(Exception):
    """Exception raised when a controller can't find a resource."""

class BaseController(turbogears.controllers.Controller):
    @turbogears.errorhandling.dispatch_error.when(
        "isinstance(tg_exceptions, model.errors.ModelError)")
    def handle_model_error(self, tg_source, tg_errors, tg_exception,
                           *args, **kw):
        return dict(tg_template="hvz.templates.modelerror",
                    error=tg_exception,)
    
    @turbogears.errorhandling.dispatch_error.when(
        "isinstance(tg_exceptions, NotFound)")
    def handle_not_found(self, tg_source, tg_errors, tg_exception,
                         *args, **kw):
        return dict(tg_template="hvz.templates.notfound", 
                    requested_uri=cherrypy.request.path,)

class Root(turbogears.controllers.RootController, BaseController):
    def __init__(self):
        import random
        from hvz.controllers.game import GameController
        from hvz.controllers.user import UserController
        self.game = GameController()
        self.user = UserController()
        # Make sure we have real randomness
        random.seed()
    
    @expose("hvz.templates.welcome")
    def index(self):
        return dict()
    
    @expose("hvz.templates.login")
    def login(self, forward_url=None, previous_url=None, *args, **kw):
        if not identity.current.anonymous and \
           identity.was_login_attempted() and \
           not identity.get_identity_errors():
            path = (forward_url or previous_url or '/')
            raise turbogears.redirect(path, kw)
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
        raise turbogears.redirect('/')
    
    @expose("hvz.templates.sudo")
    @identity.require(identity.has_permission('sudo-login'))
    def sudo(self):
        return dict()
    
    @expose()
    @identity.require(identity.has_permission('sudo-login'))
    def action_sudo(self, user_name):
        requested_user = model.identity.User.by_user_name(user_name)
        if requested_user is None:
            raise NotFound()
        manual_login(requested_user)
        raise turbogears.redirect('/')
