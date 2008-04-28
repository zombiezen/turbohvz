#!/usr/bin/env python
#
#   email.py
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

"""Support for email"""

import turbogears
import turbomail
from turbomail.message import Message

__author__ = 'Ross Light'
__date__ = 'April 16, 2008'
__all__ = ['GenshiMessage',
           'sendmail',
           'send_generic_mail',]

class GenshiMessage(Message):
    """A message created from a Genshi template."""
    def __init__(self, sender, recipient, subject, template, variables={}, **kw):
        """
        Store the additonal template and variable information.
        
        @param template: A dot-path to a valid Genshi template.
        @type template: string
        
        @param variables: A dictionary containing named variables to
                          pass to the template engine.
        @type variables: dict
        """
        self._template = template
        self._variables = dict(sender=sender,
                               recipient=recipient,
                               subject=subject)
        self._variables.update(variables)
        super(GenshiMessage, self).__init__(sender, recipient, subject, **kw)

    def _process(self):
        """Automatically generate the plain and rich text content."""
        turbogears.view.base.load_engines()
        data = dict()
        for (i, j) in self._variables.iteritems():
            if callable(j):
                data[i] = j()
            else:
                data[i] = j
        engine = turbogears.view.engines.get('genshi')
        encoding = turbogears.config.get('genshi.encoding', 'utf-8')
        data['email_format'] = 'plain'
        self.plain = engine.render(data, template=self._template,
                                   format="text")
        data['email_format'] = 'rich'
        self.rich = engine.render(data, template=self._template)
        self.plain, self.rich = (self.plain.decode(encoding),
                                 self.rich.decode(encoding))
        return super(GenshiMessage, self)._process()

def sendmail(*args, **kw):
    """
    Conveniently sends an email.
    
    This will immediately return if mail has been turned off.  The sender is
    set to the value of the configuration value ``hvz.webmaster_email``.
    
    :Returns: The newly created message
    :ReturnType: turbomail.message.Message
    """
    if not turbogears.config.get('mail.on', False):
        # Mail has been turned off, ignore it.
        return
    from_address = turbogears.config.get('hvz.webmaster_email')
    new_message = GenshiMessage(from_address, *args, **kw)
    turbomail.enqueue(new_message)
    return new_message

def send_generic_mail(recipients, subject, message):
    """
    Conveniently sends a custom email.
    
    This will immediately return if mail has been turned off.  The sender is
    set to the value of the configuration value ``hvz.webmaster_email``.
    
    :Returns: The newly created message
    :ReturnType: turbomail.message.Message
    """
    return sendmail(recipients, subject, "hvz.templates.mail.generic",
                    dict(subject=subject,
                         content=message,))
