#!/usr/bin/env python
#
#   controllers/user.py
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

import cherrypy
import turbogears
from turbogears import error_handler, expose, url, identity, validate
from turbogears.database import session
from turbogears.paginate import paginate

from hvz import forms, util, widgets
from hvz.controllers import base
from hvz.model.identity import User, Group

__author__ = 'Ross Light'
__date__ = 'April 18, 2008'
__all__ = ['UserController']

class UserController(base.BaseController):
    @expose("hvz.templates.user.index")
    @paginate('users', default_order='display_name')
    def index(self):
        all_users = session.query(User)
        grid = widgets.UserList(sortable=True)
        pager = widgets.Pager()
        return dict(users=all_users,
                    grid=grid,
                    pager=pager,)
    
    @expose("hvz.templates.user.view")
    def view(self, user_id):
        # Retrieve user
        if user_id.isdigit():
            requested_user = User.query.get(user_id)
        else:
            requested_user = User.by_user_name(user_id)
        if requested_user is None:
            raise NotFound()
        # Get template variables
        grid = widgets.GameList()
        games = [entry.game for entry in requested_user.entries]
        return dict(user=requested_user,
                    games=games,
                    game_grid=grid,)
    
    @expose("hvz.templates.user.edit")
    def edit(self, user_id):
        # Retrieve user
        if user_id.isdigit():
            requested_user = User.query.get(user_id)
        else:
            requested_user = User.by_user_name(user_id)
        if requested_user is None:
            raise NotFound()
        # Check for permission
        if not (identity.has_permission(u'edit-user') or
                identity.current.user == requested_user):
            raise identity.IdentityFailure("Current user cannot edit "
                                           "others' accounts.")
        # Compile template values
        values = {}
        for field in forms.edit_user_form.fields:
            name = field.name
            values[name] = getattr(requested_user, name)
        return dict(user=requested_user,
                    form=forms.edit_user_form,
                    values=values,)
    
    @expose("hvz.templates.user.register")
    def register(self):
        return dict(form=forms.register_form,)
    
    @expose("hvz.templates.user.thankyou")
    def thankyou(self, user_id):
        if user_id.isdigit():
            requested_user = User.query.get(user_id)
        else:
            requested_user = User.by_user_name(user_id)
        if requested_user is None:
            raise NotFound()
        return dict(user=requested_user)
    
    @expose()
    @error_handler(register)
    @validate(forms.register_form)
    def action_register(self, user_name, display_name, email_address,
                        password1, password2, profile):
        # Determine group
        group_config = turbogears.config.get("hvz.default_group", "player")
        if group_config is None:
            groups = []
        elif isinstance(group_config, basestring):
            groups = [Group.by_group_name(group_config)]
        elif isinstance(group_config, (list, tuple)):
            groups = [Group.by_group_name(name) for name in group_config]
        else:
            raise ValueError("Default group %r not recognized" % group_config)
        # Create user
        new_user = User(user_name, display_name, email_address, password1)
        if profile:
            new_user.profile = profile
        for group in groups:
            group.add_user(new_user)
        session.flush()
        # Handle interface
        msg = _("Your account has been created, %s.") % (unicode(new_user))
        turbogears.flash(msg)
        base.manual_login(new_user)
        link = util.user_link(new_user, 'thankyou', redirect=True)
        raise turbogears.redirect(link)
    
    @expose()
    @error_handler(edit)
    @validate(forms.edit_user_form)
    def action_edit(self, user_id, display_name, email_address, profile):
        # Query user
        requested_user = User.get(user_id)
        if requested_user is None:
            raise NotFound()
        # Check for permission
        if not (identity.has_permission(u'edit-user') or
                identity.current.user == requested_user):
            raise identity.IdentityFailure("Current user cannot edit "
                                           "others' accounts.")
        # Make necessary changes
        requested_user.display_name = display_name
        requested_user.email_address = email_address
        requested_user.profile = profile
        # Go to user's page
        turbogears.flash(_("Your changes have been saved."))
        raise turbogears.redirect(util.user_link(requested_user, redirect=True))
