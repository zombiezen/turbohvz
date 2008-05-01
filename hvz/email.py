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

"""
Support for email

:Variables:
    cell_providers : dict
        Dictionary of cell phone supported providers.  Each value is a
        ``(name, sms_domain)`` pair.
"""

import turbogears
import turbomail
from turbomail.message import Message

__author__ = 'Ross Light'
__date__ = 'April 16, 2008'
__all__ = ['GenshiMessage',
           'sendmail',
           'send_generic_mail',
           'send_sms',]

cell_providers = \
{
    'att': (_("AT&T"), 'mms.att.net'),
    'nextel': (_("Nextel"), 'messaging.nextel.com'),
    'sprint': (_("Sprint"), 'messaging.sprintpcs.com'),
    't-mobile': (_("T-Mobile"), 'tmomail.net'),
    'verizon': (_("Verizon"), 'vtext.com'),
    'virgin': (_("Virgin Mobile"), 'vmobl.com'),
    'boost': (_("Boost"), 'myboostmobile.com'),
}

class GenshiMessage(Message):
    """A message created from a Genshi template."""
    def __init__(self, sender, recipient, subject, template, variables={}, **kw):
        """
        Store the additonal template and variable information.
        
        :Parameters:
            template : str
                A dot-path to a valid Genshi template.
            variables : dict
                A dictionary containing named variables to pass to the
                template engine.
        """
        self.plain_only = kw.pop('plain_only', False)
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
        self.plain = self._clean_plain(self.plain)
        self.plain = self.plain.decode(encoding)
        if not self.plain_only:
            data['email_format'] = 'rich'
            self.rich = engine.render(data, template=self._template)
            self.rich = self.rich.decode(encoding)
        return super(GenshiMessage, self)._process()
    
    @staticmethod
    def _clean_plain(text):
        text = text.strip()
        lines = []
        for line in text.splitlines():
            line = line.strip()
            try:
                last_line = lines[-1]
            except IndexError:
                last_line = None
            if line or last_line:
                # Only allow one blank line between text chunks
                lines.append(line)
        return '\r\n'.join(lines)
        '\r\n'.join(line.strip() for line in text.splitlines())

def sendmail(recipient, subject, template, variables={}, **kw):
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
    variables = variables.copy()
    variables.setdefault('message_format', 'email')
    from_address = turbogears.config.get('hvz.webmaster_email')
    new_message = GenshiMessage(from_address, recipient, subject,
                                template, variables, **kw)
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

def send_sms(numbers, subject, template, variables={}):
    """
    Sends a text message.
    
    :Parameters:
        numbers : tuple or list of tuple
            Numbers to send to.  Each item must be a ``(number, provider)``
            pair where number is a ten-digit US phone number.
        subject : unicode
            Subject to send with
        message : unicode
            Text to send
    :Returns: The newly created message
    :ReturnType: turbomail.message.Message
    """
    def _make_address(item):
        number, provider = item
        if len(number) != 10:
            raise ValueError('Number is not a valid US phone number')
        provider_name, provider_domain = cell_providers[provider]
        return number + '@' + provider_domain
    if isinstance(numbers, tuple):
        numbers = [numbers]
    addresses = [_make_address(item) for item in numbers]
    variables = variables.copy()
    variables.setdefault('message_format', 'sms')
    return sendmail(addresses, subject, template, variables, plain_only=True)
