#!/usr/bin/env python
#
#   json.py
#   HvZ
#

"""
A JSON-based API(view) for your app.

Most rules would look like::

    @jsonify.when("isinstance(obj, YourClass)")
    def jsonify_yourclass(obj):
        return [obj.val1, obj.val2]

@jsonify can convert your objects to following types: lists, dicts, numbers and
strings.
"""

__author__ = 'Ross Light'
__date__ = 'March 30, 2008'
__all__ = []

from turbojson.jsonify import jsonify

