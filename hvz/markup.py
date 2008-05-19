#!/usr/bin/env python
#
#   markup.py
#   TurboHvZ
#
#   Copyright (C) 2008 Ross Light
#   Originally released as public domain
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
BBCode renderer

Derived from "Post Markup" by Will McGugan http://www.willmcgugan.com

Modified by Ross Light for TurboHvZ.
"""

import re
from urllib import quote, unquote, quote_plus
from urlparse import urlparse, urlunparse
from copy import copy

__author__ = 'Will McGugan'
__license__ = 'Public Domain'
__docformat__ = 'plaintext'
__all__ = ['create',
           'render_bbcode',
           'TagBase',
           'SimpleTag',
           'LinkTag',
           'QuoteTag',
           'SearchTag',
           'ImgTag',
           'ListTag',
           'ListItemTag',
           'SimpleCodeTag',
           'PygmentsCodeTag',
           'PostMarkup',]

pygments_available = True
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, ClassNotFound
    from pygments.formatters import HtmlFormatter
except ImportError:
    # Make Pygments optional
    pygments_available = False


re_url = re.compile(r"((https?):((//)|(\\\\))+[\w\d:#@%/;$()~_?\+-=\\\.&]*)", re.MULTILINE| re.UNICODE)
def url_tagify(s, tag=u'url'):
        
    def repl(match):
        item = match.group(0)
        return '[%s]%s[/%s]' % (tag, item, tag)
    
    return re_url.sub(repl, s)
    
    


def create(include=None, exclude=None, use_pygments=pygments_available):

    """Create a postmarkup object that coverts bbcode to XML snippets.

    include -- List or similar iterable containing the names of the tags to use
               If omitted, all tags will be used
    exclude -- List or similar iterable containing the names of the tags to exclude.
               If omitted, no tags will be excluded
    use_pygments -- If True, Pygments (http://pygments.org/) will be used for the code tag,
                    otherwise it will use <pre>code</pre>
    """

    markup = PostMarkup()

    def add_tag(name, tag_class, *args):
        if include is None or name in include:
            if exclude is not None and name in exclude:
                return
            return markup.add_tag(name, tag_class, *args)

    add_tag(u'b', SimpleTag, u'b', u'strong')
    add_tag(u'i', SimpleTag, u'i', u'em')
    add_tag(u'u', SimpleTag, u'u', u'u')
    add_tag(u's', SimpleTag, u's', u'strike')
    add_tag(u'link', LinkTag, u'link')
    add_tag(u'url', LinkTag, u'url')
    add_tag(u'quote', QuoteTag)
    add_tag(u'img', ImgTag, u'img')

    add_tag(u'wiki', SearchTag, u'wiki',
            u"http://en.wikipedia.org/wiki/Special:Search?search=%s", u'wikipedia.org')
    add_tag(u'google', SearchTag, u'google',
            u"http://www.google.com/search?hl=en&q=%s&btnG=Google+Search", u'google.com')
    add_tag(u'dictionary', SearchTag, u'dictionary',
            u"http://dictionary.reference.com/browse/%s", u'dictionary.com')
    add_tag(u'dict', SearchTag, u'dict',
            u"http://dictionary.reference.com/browse/%s", u'dictionary.com')

    add_tag(u'list', ListTag)
    add_tag(u'*', ListItemTag)

    if use_pygments:
        assert pygments_available, "Install pygments (http://pygments.org/) or call create with use_pygments=False"
        add_tag(u'code', PygmentsCodeTag, u'code')
    else:
        add_tag(u'code', SimpleCodeTag, u'code')

    return markup


_bbcode_postmarkup = None
def render_bbcode(bbcode, encoding="ascii"):

    """Renders a bbcode string in to XHTML. This is a shortcut if you don't
    need to customize any tags.

    bbcode -- A string containing the bbcode
    encoding -- If bbcode is not unicode, then then it will be encoded with
    this encoding (defaults to 'ascii'). Ignore the encoding if you already have
    a unicode string

    """

    global _bbcode_postmarkup
    if _bbcode_postmarkup is None:
        _bbcode_postmarkup = create(use_pygments=pygments_available)
    return _bbcode_postmarkup(bbcode, encoding)


re_html=re.compile('<.*?>|\&.*?\;')
def textilize(s):
    """Remove markup from html"""
    return re_html.sub("", s)

re_excerpt = re.compile(r'\[".*?\]+?.*?\[/".*?\]+?', re.DOTALL)
re_remove_markup = re.compile(r'\[.*?\]', re.DOTALL)

def remove_markup(post):
    """Removes BBCode tags from a string."""
    return re_remove_markup.sub("", post)

def get_excerpt(post):
    """Returns an excerpt between ["] and [/"]

    post -- BBCode string"""

    match = re_excerpt.search(post)
    if match is None:
        return ""
    excerpt = match.group(0)
    excerpt = excerpt.replace(u'\n', u"<br/>")
    return remove_markup(excerpt)


class TagBase(object):
    """
    Base class for a Post Markup tag.
    """

    def __init__(self, name):
        self.name = name
        self.params = None
        self.auto_close = False
        self.enclosed = False
        self.open_pos = None
        self.close_pos = None
        self.raw = None
        self.block = False

    def open(self, open_pos):
        """Called when the tag is opened. Should return a string or a
        stringifyable object."""
        self.open_pos = open_pos
        return ''

    def close(self, close_pos, content):
        """Called when the tag is closed. Should return a string or a
        stringifyable object."""
        self.close_pos = close_pos
        self.content = content
        return ''

    def get_tag_contents(self):
        """Gets the contents of the tag."""
        content_elements = self.content[self.open_pos+1:self.close_pos]
        contents = u"".join([unicode(element) for element in content_elements\
                             if isinstance(element, StringToken)])
        contents = textilize(contents)
        return contents

    def get_raw_tag_contents(self):
        """Gets the raw contents (includes html tags) of the tag."""
        content_elements = self.content[self.open_pos+1:self.close_pos]
        contents = u"".join(element.raw for element in content_elements)
        return contents

# A proxy object that calls a callback when converted to a string
class TagStringify(object):
    def __init__(self, callback, raw):
        self.callback = callback
        self.raw = raw
    def __unicode__(self):
        return self.callback()
    def __repr__(self):
        return self.__unicode__()


class SimpleTag(TagBase):

    """Simple substitution tag."""

    def __init__(self, name, substitute):
        TagBase.__init__(self, name)
        self.substitute = substitute

    def open(self, open_pos):
        """Called to render the opened tag."""
        return u"<%s>"%(self.substitute)

    def close(self, close_pos, content):
        """Called to render the closed tag."""
        return u"</%s>"%(self.substitute)


class LinkTag(TagBase):

    """Tag that generates a link (</a>)."""

    def __init__(self, name):
        TagBase.__init__(self, name)

    def open(self, open_pos):
                
        self.open_pos = open_pos
        return TagStringify(self._open, self.raw)

    def close(self, close_pos, content):        

        self.close_pos = close_pos
        self.content = content
        return TagStringify(self._close, self.raw)

    def _open(self):
        
        self.domain = u''
        nest_level = self.tag_data['link_nest_level'] = self.tag_data.get('link_nest_level', 0) + 1
        
        if nest_level > 1:
            return u""            
        
        if self.params:
            url = self.params
        else:
            url = self.get_tag_contents()

        self.domain = ""
        #Unquote the url
        self.url = unquote(url)

        #Disallow javascript links
        if u"javascript:" in self.url.lower():
            return ""

        #Disallow non http: links
        url_parsed = urlparse(self.url)
        if url_parsed[0] and not url_parsed[0].lower().startswith(u'http'):
            return ""

        #Prepend http: if it is not present
        if not url_parsed[0]:
            self.url="http://"+self.url
            url_parsed = urlparse(self.url)

        #Get domain
        self.domain = url_parsed[1].lower()

        #Remove www for brevity
        if self.domain.startswith(u'www.'):
            self.domain = self.domain[4:]

        #Quote the url
        #self.url="http:"+urlunparse( map(quote, (u"",)+url_parsed[1:]) )
        self.url= unicode( urlunparse(quote(component, safe='/=&?:+') for component in url_parsed) )

        #Sanity check
        if not self.url:
            return u""

        if self.domain:
            return u'<a href="%s" title="%s">'%(_escape(self.url),
                                                _escape(self.url))
        else:
            return u""

    def _close(self):
        
        self.tag_data['link_nest_level'] -= 1
        
        if self.tag_data['link_nest_level'] > 0:
            return u''
                
        if self.domain:
            return u'</a>'+self.annotate_link(self.domain)
        else:
            return u''

    def annotate_link(self, domain):
        """Annotates a link with the domain name.
        Override this to disable or change link annotation.
        """
        return u" [%s]"%_escape(domain)


class QuoteTag(TagBase):
    """
    Generates a blockquote with a message regarding the author of the quote.
    """
    def __init__(self):
        TagBase.__init__(self, 'quote')

    def open(self, open_pos):
        return u'<blockquote><em>%s</em><br/>'%(self.params)

    def close(self, close_pos, content):
        return u"</blockquote>"


class SearchTag(TagBase):
    """
    Creates a link to a search term.
    """

    def __init__(self, name, url, label=u""):
        TagBase.__init__(self, name)
        self.url = url
        self.search = u""
        self.label = label or name

    def __unicode__(self):

        link = u'<a href="%s">'%self.url

        if u'%' in link:
            return link%quote_plus(self.get_tag_contents().encode('latin-1'))
        else:
            return link

    def open(self, open_pos):
        self.open_pos = open_pos
        return TagStringify(self._open, self.raw)

    def close(self, close_pos, content):

        self.close_pos = close_pos
        self.content = content
        return TagStringify(self._close, self.raw)

    def _open(self):
        if self.params:
            search=self.params
        else:
            search=self.get_tag_contents()
        link = u'<a href="%s" title="%s">' % (_escape(self.url),
                                              _escape(self.label))
        if u'%' in link:
            return link%quote_plus(search.encode('latin-1'))
        else:
            return link

    def _close(self):

        if self.label:
            return u'</a>' + self.annotate_link(self.label)
        else:
            return u''

    def annotate_link(self, domain):
        return u" [%s]"%_escape(domain)


class ImgTag(TagBase):

    def __init__(self, name):
        TagBase.__init__(self, name)
        self.enclosed=True

    def open(self, open_pos):
        self.open_pos = open_pos
        return TagStringify(self._open, self.raw)

    def close(self, close_pos, content):

        self.close_pos = close_pos
        self.content = content
        return TagStringify(self._close, self.raw)

    def _open(self):
        contents = self.get_raw_tag_contents()
        contents = _escape(contents.replace(u'"', "%22"))
        return u'<img src="%s"></img><div style="display:none">'%(contents)

    def _close(self):
        return u"</div>"



class ListTag(TagBase):

    """Simple substitution tag."""

    def __init__(self):
        TagBase.__init__(self, "list")
        self.block = True

    def open(self, open_pos):
        """Called to render the opened tag."""
        if self.params == "1":
            self.close_tag = u"</ol>"
            return u"<ol>"
        elif self.params == "a":
            self.close_tag = u"</ol>"
            return u'<ol style="list-style-type: lower-alpha;">'
        elif self.params == "A":
            self.close_tag = u"</ol>"
            return u'<ol style="list-style-type: upper-alpha;">'
        else:
            self.close_tag = u"</ul>"
            return u"<ul>"

    def close(self, close_pos, content):
        """Called to render the closed tag."""
        return self.close_tag


class ListItemTag(TagBase):

    _open_tag = None

    def __init__(self):
        TagBase.__init__(self, u"*")
        self.closed = False
        self.block = True

    def open(self, open_pos):
        """Called to render the opened tag."""

        if self.closed:
            return u""

        tag_data = self.tag_data

        ret = u""
        if ( "ListItemTag.open_tag" in tag_data and
            tag_data["ListItemTag.open_tag"] is not None ):

            ret = u"</li>"
            tag_data["ListItemTag.open_tag"].closed = True

        tag_data["ListItemTag.open_tag"] = self
        return ret + u"<li>"

    def close(self, close_pos, content):
        """Called to render the closed tag."""

        if self.closed:
            return u""

        self.closed = True
        self.tag_data["ListItemTag.open_tag"] = None
        return u"</li>"


class SimpleCodeTag(SimpleTag):
    def __init__(self, name):
        SimpleTag.__init__(self, name, 'pre')
        self.enclosed = True


class PygmentsCodeTag(TagBase):

    # Set this to True if you want to display line numbers
    line_numbers = False

    def __init__(self, name):
        TagBase.__init__(self, name)
        self.enclosed = True
        self.block = True

    def open(self, open_pos):
        self.open_pos = open_pos
        return TagStringify(self._open, self.raw)

    def close(self, close_pos, content):

        self.close_pos = close_pos
        self.content = content
        return TagStringify(self._close, self.raw)

    def _open(self):

        try:
            lexer = get_lexer_by_name(self.params, stripall=True)
        except ClassNotFound:
            contents = _escape(self.get_raw_tag_contents())
            self.no_close = True
            return u'''<div class="code"><pre>%s</pre></div><div style='display:none'>'''%contents
        formatter = HtmlFormatter(linenos=self.line_numbers, cssclass="code")
        code = self.get_raw_tag_contents()
        result = highlight(code, lexer, formatter)
        return result + u"\n<div style='display:none'>"

    def _close(self):

        return u"</div>"


# http://effbot.org/zone/python-replace.htm
class MultiReplace:

    def __init__(self, repl_dict):
        # "compile" replacement dictionary

        # assume char to char mapping
        charmap = map(chr, range(256))
        for k, v in repl_dict.items():
            if len(k) != 1 or len(v) != 1:
                self.charmap = None
                break
            charmap[ord(k)] = v
        else:
            self.charmap = string.join(charmap, "")
            return

        # string to string mapping; use a regular expression
        keys = repl_dict.keys()
        keys.sort() # lexical order
        keys.reverse() # use longest match first
        pattern = "|".join(re.escape(key) for key in keys)
        self.pattern = re.compile(pattern)
        self.dict = repl_dict

    def replace(self, str):
        # apply replacement dictionary to string
        if self.charmap:
            return string.translate(str, self.charmap)
        def repl(match, get=self.dict.get):
            item = match.group(0)
            return get(item, item)
        return self.pattern.sub(repl, str)


class StringToken(object):

    def __init__(self, raw):
        self.raw = raw

    def __unicode__(self):
        ret = PostMarkup.standard_replace.replace(self.raw)
        return ret


def _escape(s):
    return PostMarkup.standard_replace.replace(s.rstrip('\n'))

class PostMarkup(object):

    standard_replace = MultiReplace({   u'<':u'&lt;',
                                        u'>':u'&gt;',
                                        u'&':u'&amp;',
                                        u'\n':u'<br/>'})

    TOKEN_TAG, TOKEN_PTAG, TOKEN_TEXT = range(3)


    @staticmethod
    def TagFactory(tag_class, *args):
        """
        Returns a callable that returns a new tag instance.
        """
        def make():
            return tag_class(*args)

        return make


    # I tried to use RE's. Really I did.
    def tokenize(self, post):

        text = True
        pos = 0

        def find_first(post, pos, c):
            f1 = post.find(c[0], pos)
            f2 = post.find(c[1], pos)
            if f1 == -1:
                return f2
            if f2 == -1:
                return f1
            return min(f1, f2)

        while True:

            brace_pos = post.find(u'[', pos)
            if brace_pos == -1:
                yield PostMarkup.TOKEN_TEXT, post[pos:]
                return
            if brace_pos - pos > 0:
                yield PostMarkup.TOKEN_TEXT, post[pos:brace_pos]

            pos = brace_pos
            end_pos = pos+1

            open_tag_pos = post.find(u'[', end_pos)
            end_pos = find_first(post, end_pos, u']=')
            if end_pos == -1:
                yield PostMarkup.TOKEN_TEXT, post[pos:]
                return
            
            if open_tag_pos != -1 and open_tag_pos < end_pos:                
                yield PostMarkup.TOKEN_TEXT, post[pos:open_tag_pos]
                end_pos = open_tag_pos
                pos = end_pos
                continue

            if post[end_pos] == ']':
                yield PostMarkup.TOKEN_TAG, post[pos:end_pos+1]
                pos = end_pos+1
                continue

            if post[end_pos] == '=':
                try:
                    end_pos += 1
                    while post[end_pos] == ' ':
                        end_pos += 1
                    if post[end_pos] != '"':
                        end_pos = post.find(u']', end_pos+1)
                        if end_pos == -1:
                            return
                        yield PostMarkup.TOKEN_TAG, post[pos:end_pos+1]
                    else:
                        end_pos = find_first(post, end_pos, u'"]')
                        if end_pos==-1:
                            return
                        if post[end_pos] == '"':
                            end_pos = post.find(u'"', end_pos+1)
                            if end_pos == -1:
                                return
                            end_pos = post.find(u']', end_pos+1)
                            if end_pos == -1:
                                return
                            yield PostMarkup.TOKEN_PTAG, post[pos:end_pos+1]
                        else:
                            yield PostMarkup.TOKEN_TAG, post[pos:end_pos+1]
                    pos = end_pos+1
                except IndexError:
                    return


    def __init__(self):

        self.tags={}


    def default_tags(self):
        """
        Sets up a minimal set of tags.
        """
        self.tags[u'b'] = PostMarkup.TagFactory(SimpleTag, u'b', u'strong')
        self.tags[u'i'] = PostMarkup.TagFactory(SimpleTag, u'i', u'em')
        self.tags[u'u'] = PostMarkup.TagFactory(SimpleTag, u'u', u'u')
        self.tags[u's'] = PostMarkup.TagFactory(SimpleTag, u's', u'strike')

        return self


    def add_tag(self, name, tag_class, *args):
        """Add a tag factory to the markup.

        name -- Name of the tag
        tag_class -- Class derived from BaseTag
        args -- Aditional parameters for the tag class

        """
        tag = PostMarkup.TagFactory(tag_class, *args)
        self.tags[name] = tag
        return tag


    def __call__(self, *args, **kwargs):
        return self.render_to_html(*args, **kwargs)


    def render_to_html(self,
                       post_markup,
                       encoding="ascii",
                       exclude_tags=None):
        
        """Converts Post Markup to XHTML.

        post_markup -- String containing bbcode
        encoding -- Encoding of string, defaults to "ascii"

        """

        if not isinstance(post_markup, unicode):
            post_markup = unicode(post_markup, encoding, 'replace')        
            
        if exclude_tags is None:
            exclude_tags = []

        tag_data = {}
        post = []
        tag_stack = []
        break_stack = []
        enclosed = False
        
        previous_tag = None

        def check_tag_stack(tag_name):
            """Check to see if a tag has been opened."""
            for tag in reversed(tag_stack):
                if tag_name == tag.name:
                    return True
            return False

        def redo_break_stack():
            """Re-opens tags that have been closed prematurely."""
            while break_stack:
                tag = copy(break_stack.pop())
                tag.raw = u""
                tag_stack.append(tag)
                post.append(tag.open(len(post)))

        for tag_type, tag_token in self.tokenize(post_markup):
            #print tag_type, tag_token
            raw_tag_token = tag_token
            if tag_type == PostMarkup.TOKEN_TEXT:
                redo_break_stack()
                if previous_tag is not None and previous_tag.block:
                    tag_token = tag_token.lstrip()
                post.append(StringToken(tag_token))
                continue
            elif tag_type == PostMarkup.TOKEN_TAG:
                tag_token = tag_token[1:-1].lstrip()
                if ' ' in tag_token:
                    tag_name, tag_attribs = tag_token.split(u' ', 1)
                    tag_attribs = tag_attribs.strip()
                else:
                    if '=' in tag_token:
                        tag_name, tag_attribs = tag_token.split(u'=', 1)
                        tag_attribs = tag_attribs.strip()
                    else:
                        tag_name = tag_token
                        tag_attribs = u""
            else:
                tag_token = tag_token[1:-1].lstrip()
                tag_name, tag_attribs = tag_token.split(u'=', 1)
                tag_attribs = tag_attribs.strip()[1:-1]

            tag_name = tag_name.strip().lower()

            end_tag = False
            if tag_name.startswith(u'/'):
                end_tag = True
                tag_name = tag_name[1:]
                
            if tag_name in exclude_tags:
                continue

            if not end_tag:
                if enclosed:
                    post.append(StringToken(raw_tag_token))
                    continue
                if tag_name not in self.tags:
                    continue
                tag = self.tags[tag_name]()
                tag.tag_data = tag_data
                enclosed = tag.enclosed
                tag.raw = raw_tag_token

                redo_break_stack()
                tag.params=tag_attribs
                tag_stack.append(tag)
                post.append(tag.open(len(post)))
                if tag.auto_close:
                    end_tag = True
                
                # Remove leading newlines from blocks
                if tag.block:
                    try:
                        last_token = post[-2]
                    except IndexError:
                        pass
                    else:
                        if isinstance(last_token, StringToken):
                            last_token.raw = last_token.raw.rstrip()
                
                previous_tag = tag

            if end_tag:
                if not check_tag_stack(tag_name):
                    if enclosed:
                        post.append(StringToken(raw_tag_token))
                    continue
                enclosed = False
                try:
                    last_token = post[-1]
                except IndexError:
                    last_token = None
                while tag_stack[-1].name != tag_name:
                    tag = tag_stack.pop()
                    break_stack.append(tag)
                    if not enclosed:
                        post.append(tag.close(len(post), post))
                tag = tag_stack.pop()
                if tag.block and isinstance(last_token, StringToken):
                    last_token.raw = last_token.raw.rstrip()
                post.append(tag.close(len(post), post))
                previous_tag = tag

        if tag_stack:
            redo_break_stack()
            while tag_stack:
                post.append(tag_stack.pop().close(len(post), post))

        html = u"".join(unicode(p) for p in post)
        return html
