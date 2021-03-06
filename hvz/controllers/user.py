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

"""User and alliance handling"""

from __future__ import division

import cherrypy
import turbogears
from turbogears import error_handler, expose, url, identity, redirect, validate
from turbogears.database import session
from turbogears.paginate import paginate

from hvz import email, forms, util, widgets
from hvz.controllers import base
from hvz.model.identity import User, Group
from hvz.model.images import Image
from hvz.model.social import Alliance

__author__ = 'Ross Light'
__date__ = 'April 18, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['UserController',
           'AllianceController',]

def _calc_avg(raw_data):
    from datetime import timedelta
    data = [datum for datum in raw_data if datum is not None]
    if len(data) == 0:
        return None
    else:
        if isinstance(data[0], timedelta):
            return sum(data, timedelta()) // len(data)
        else:
            return sum(data) / len(data)

class UserController(base.BaseController):
    def __init__(self):
        self.alliance = AllianceController()
    
    @expose("hvz.templates.user.index")
    @paginate('users', limit=20, default_order='display_name')
    def index(self):
        all_users = session.query(User)
        grid = widgets.UserList(sortable=True)
        pager = widgets.Pager()
        emails = [user.email_address for user in session.query(User)]
        return dict(users=all_users,
                    grid=grid,
                    pager=pager,
                    emails=emails,)
    
    @expose("hvz.templates.user.view")
    def view(self, user_id):
        # Retrieve user
        if user_id.isdigit():
            requested_user = User.query.get(user_id)
        else:
            requested_user = User.by_user_name(user_id)
        if requested_user is None:
            raise base.NotFound()
        # Generate statistics
        entries = requested_user.entries
        show_oz = (lambda e: not e.is_original_zombie or
                             e.game.revealed_original_zombie)
        total_kills = sum(entry.kills for entry in entries
                          if show_oz(entry))
        total_killed = len([entry for entry in entries
                            if not entry.is_human and show_oz(entry)])
        if total_killed == 0:
            kill_ratio = 0.0
        else:
            kill_ratio = float(total_kills / total_killed)
        avg_survival = _calc_avg(entry.survival_time for entry in entries)
        avg_undead = _calc_avg(entry.undead_time for entry in entries
                               if show_oz(entry))
        stats = dict(
            total_games=len(entries),
            total_kills=total_kills,
            total_killed=total_killed,
            avg_survival=avg_survival,
            avg_undead=avg_undead,
            kill_ratio=kill_ratio,)
        # Get template variables
        grid = widgets.GameList()
        alliance_grid = widgets.AllianceList()
        games = [entry.game for entry in entries]
        games.sort(key=(lambda g: g.created), reverse=True)
        return dict(user=requested_user,
                    games=games,
                    game_grid=grid,
                    alliance_grid=alliance_grid,
                    stats=stats,)
    
    @expose("hvz.templates.user.edit")
    def edit(self, user_id):
        # Retrieve user
        if user_id.isdigit():
            requested_user = User.query.get(user_id)
        else:
            requested_user = User.by_user_name(user_id)
        if requested_user is None:
            raise base.NotFound()
        # Check for permission
        if not (identity.has_permission(u'edit-user') or
                identity.current.user == requested_user):
            raise identity.IdentityFailure("Current user cannot edit "
                                           "others' accounts.")
        # Compile template values
        values = base.build_form_values(forms.edit_user_form, requested_user)
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
            raise base.NotFound()
        return dict(user=requested_user)
    
    @expose("hvz.templates.user.changepassword")
    @identity.require(identity.not_anonymous())
    def changepassword(self):
        requested_user = identity.current.user
        return dict(form=forms.password_change_form,
                    user=requested_user,)
    
    @expose()
    @error_handler(register)
    @validate(forms.register_form)
    def action_register(self, user_name, display_name, email_address,
                        cell_number, cell_provider,
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
        if cell_number:
            new_user.cell_number = cell_number.replace('-', '')[:10]
            new_user.cell_provider = cell_provider
        else:
            new_user.cell_number = None
            new_user.cell_provider = None
        if profile:
            new_user.profile = profile
        for group in groups:
            group.add_user(new_user)
        session.flush()
        # Log info
        base.log.info("%r Created", new_user)
        # Send email
        email.sendmail(new_user.email_address,
                       _("Welcome to Humans vs. Zombies!"),
                       "hvz.templates.mail.welcome",
                       dict(user=new_user,))
        # Handle interface
        msg = _("Your account has been created, %s.") % (unicode(new_user))
        turbogears.flash(msg)
        base.manual_login(new_user)
        link = util.user_link(new_user, 'thankyou', redirect=True)
        raise redirect(link)
    
    @expose()
    @error_handler(edit)
    @validate(forms.edit_user_form)
    def action_edit(self, user_id, display_name, email_address,
                    cell_number, cell_provider,
                    profile, new_image, clear_user_image=False,):
        # Query user
        requested_user = User.query.get(user_id)
        if requested_user is None:
            raise base.NotFound()
        # Check for permission
        if not (identity.has_permission(u'edit-user') or
                identity.current.user == requested_user):
            raise identity.IdentityFailure("Current user cannot edit "
                                           "others' accounts.")
        # Create image
        allow_images = turbogears.config.get('hvz.user_images', True)
        if allow_images and not clear_user_image and new_image.filename:
            image_obj = Image()
            image_obj.write(new_image.file)
        else:
            image_obj = None
        # Make necessary changes
        requested_user.display_name = display_name
        requested_user.email_address = email_address
        if cell_number:
            requested_user.cell_number = cell_number.replace('-', '')[:10]
            requested_user.cell_provider = cell_provider
        else:
            requested_user.cell_number = None
            requested_user.cell_provider = None
        requested_user.profile = profile
        if clear_user_image:
            if requested_user.image is not None:
                requested_user.image.delete()
        elif image_obj:
            if requested_user.image is not None:
                requested_user.image.delete()
            requested_user.image = image_obj
        # Log info
        base.log.info("%r Edited", requested_user)
        # Go to user's page
        turbogears.flash(_("Your changes have been saved."))
        raise redirect(util.user_link(requested_user, redirect=True))
    
    @expose()
    @error_handler(changepassword)
    @validate(forms.password_change_form)
    def action_changepassword(self, user_id, original_password,
                              password1, password2):
        # Query user
        requested_user = User.query.get(user_id)
        if requested_user is None:
            raise base.NotFound()
        # Check for permission
        if identity.current.user != requested_user:
            raise identity.IdentityFailure("Current user cannot change "
                                           "others' passwords.")
        # Make necessary changes
        requested_user.password = password1
        # Log info
        base.log.info("%r Password Changed", requested_user)
        # Go back to user's page
        turbogears.flash(_("Your password has been changed."))
        raise redirect(util.user_link(requested_user, redirect=True))

class AllianceController(base.BaseController):
    @expose("hvz.templates.alliances.index")
    @paginate('alliances', limit=20, default_order='display_name')
    def index(self):
        all_alliances = session.query(Alliance)
        grid = widgets.AllianceList(sortable=True)
        pager = widgets.Pager()
        return dict(alliances=all_alliances,
                    grid=grid,
                    pager=pager,)
    
    @expose("hvz.templates.alliances.view")
    def view(self, alliance_id):
        requested_alliance = Alliance.query.get(alliance_id)
        if requested_alliance is None:
            raise base.NotFound()
        grid = widgets.UserList(sortable=False)
        return dict(alliance=requested_alliance,
                    grid=grid,)
