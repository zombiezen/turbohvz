#!/usr/bin/env python
#
#   model/errors.py
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

__author__ = 'Ross Light'
__date__ = 'April 18, 2008'
__docformat__ = 'reStructuredText'
__all__ = ['ModelError',
           'WrongStateError',
           'InvalidTimeError',
           'PlayerNotFoundError',
           'BadImageError',]

class ModelError(Exception):
    """
    Base class for model errors.
    
    Model errors usually occur when the players try to cheat, so try to catch
    these and display a friendly error message.
    
    :IVariables:
        game_object
            The game object raising the exception
        message : unicode
            The exception's message
    """
    def __init__(self, game_object, message=None):
        self.game_object = game_object
        if message is None:
            self.message = message
        else:
            self.message = unicode(message)
    
    def __repr__(self):
        cls_name = type(self).__name__
        cls_module = type(self).__module__
        type_name = cls_module + '.' + cls_name
        if self.message is None:
            return "%s(%r)" % (type_name, self.game_object)
        else:
            return "%s(%r, %r)" % (type_name, self.game_object, self.message)
    
    def __str__(self):
        return unicode(self).encode()
    
    def __unicode__(self):
        return self.message

class WrongStateError(ModelError):
    """
    Raised when an action takes place in the wrong state.
    
    :IVariables:
        current_state : int
            The state the object is in
        needed_state : int
            The state the object must be in to make the action valid
    """
    def __init__(self, game_object, current_state, needed_state, *args, **kw):
        super(WrongStateError, self).__init__(game_object, *args, **kw)
        self.current_state = current_state
        self.needed_state = needed_state
    
    def __repr__(self):
        return "hvz.model.WrongStateError(%r, %r, %r)" % (self.game_object,
                                                          self.current_state,
                                                          self.needed_state)
    
    def __unicode__(self):
        # Get message or default
        if self.message is None:
            msg = _("That action cannot be performed; it must be "
                    "%(needed_name)s (it is currently %(current_name)s).")
        else:
            msg = self.message
        # Get state names
        names = getattr(self.game_object, 'STATE_NAMES', {})
        current_name = names.get(self.current_state,
                                 unicode(self.current_state))
        needed_name = names.get(self.needed_state,
                                unicode(self.needed_state))
        # Format and return
        return msg % dict(game_object=self.game_object,
                          current=self.current_state,
                          needed=self.needed_state,
                          current_name=current_name,
                          needed_name=needed_name,)

class InvalidTimeError(ModelError):
    """
    Raised when an action happens at an invalid time (i.e. non-chronological
    kills).
    """

class PlayerNotFoundError(ModelError):
    """Raised when a player can't be found (i.e. an invalid GID is given)."""

class BadImageError(Exception):
    """Exception raised if there is an image is unacceptable."""
