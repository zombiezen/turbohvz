#!/usr/bin/env python
#
#   controllers/feeds.py
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

from uuid import UUID, uuid4

__author__ = 'Ross Light'
__date__ = 'May 13, 2008'
__all__ = ['Feed',
           'FeedItem',]

class Feed(object):
    """
    A syndicated news feed.
    
    :IVariables:
        title : unicode
            Name of the feed
        id : str
            An identifier for the feed (may be a URI)
        description : unicode
            A brief description of the feed
        items : list
            The items inside the feed.  Order is not assured.
        sorted_items : list
            An automatically generated list of the items, sorted by newest
            first.
        main_link : str
            A URI for the page this feed represents
        icon : str
            A URI that locates the feed's image
    """
    formats = {
        'atom1_0':
            ("Atom 1.0", "application/atom+xml", "hvz.templates.feeds.atom"),
        'rss2_0':
            ("RSS 2.0", "application/rss+xml", "hvz.templates.feeds.rss2",),
    }
    # Aliases
    formats['atom'] = formats['atom1_0']
    formats['rss'] = formats['rss2_0']
    
    def __init__(self, title, description=None, link=None, feed_id=None):
        self.title = title
        self.description = description
        self.main_link = link
        if feed_id is None:
            self.id = uuid4().urn
        elif isinstance(feed_id, UUID):
            self.id = feed_id.urn
        else:
            self.id = str(feed_id)
        self.items = []
    
    def add_item(self, *args, **kw):
        if len(args) == 1 and isinstance(args[0], FeedItem):
            self.items.append(args[0])
        else:
            self.items.append(FeedItem(*args, **kw))
    
    def render(self, format='atom'):
        import cherrypy
        from turbogears.view import render
        from hvz.model.dates import now
        from hvz.release import version
        try:
            format_name, format_type, format_template = self.formats[format]
        except KeyError:
            raise ValueError("Invalid feed format: %r" % format)
        # Render out the feed completely
        # This is necessary because you can't override Content-type inside a
        # controller method, so we return raw data rendered by the TurboGears
        # templating system.
        data = dict(feed=self,
                    now=now(),
                    version=version,
                    version_info=("TurboHvZ %s" % version),)
        return render(data, format_template, 'xml', format_type)
    
    @property
    def sorted_items(self):
        return sorted(self.items,
                      key=(lambda i: i.created),
                      reverse=True)

class FeedItem(object):
    """
    A single item in a feed.
    
    :IVariables:
        title : unicode
            The name of the item
        id : str
            An identifier for the item
        date : datetime.datetime
            The time at which the item was updated
        created : datetime.datetime
            The time at which the item was published
        link : str
            A link to what the item represents
        summary : unicode
            A short summary of what the item represents
    """
    def __init__(self, title, summary, link=None, item_id=None, date=None):
        from hvz.model.dates import now, make_aware
        self.title = title
        self.summary = summary
        self.link = link
        if item_id is None:
            self.id = uuid4().urn
        elif isinstance(item_id, UUID):
            self.id = feed_id.urn
        else:
            self.id = str(item_id)
        if date is None:
            date = now()
        else:
            date = make_aware(date)
        self.date = self.created = date
