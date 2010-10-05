# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Sync Server
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Tarek Ziade (tarek@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
""" Various helpers.
"""
import string
import json

from webob import Response

CID_CHARS = '123456789' + string.ascii_letters
FILL_CHAR = '0'
_BASE = len(CID_CHARS)


def json_response(data, dump=True, **kw):
    """Returns Response containing a json string"""
    if dump:
        data = json.dumps(data)
    resp = Response(data, content_type='application/json')
    for key, value in kw.items():
        setattr(resp, key, value)
    return resp


def b62encode(num, fixed_length=3):
    """Encodes a base 10 number into a pseudo-base 62 one."""
    if num == 0:
        return CID_CHARS[0]
    res = []
    while num:
        rem = num % _BASE
        num = num // _BASE
        res.append(CID_CHARS[rem])
    res.reverse()
    res = ''.join(res)
    # left-filling with 0s
    if len(res) < fixed_length:
        res = '0' * (fixed_length - len(res)) + res
    return res


def b62decode(key):
    """Decodes a key from pseudo-base62 to base 10"""
    key = key.lstrip('0')
    size = len(key)
    num = 0
    idx = 0
    for char in key:
        power = size - (idx + 1)
        num += CID_CHARS.index(char) * (_BASE ** power)
        idx += 1
    return num


class MemoryClient(dict):
    """Fallback if a memcache client is not installed.
    """
    def __init__(self, servers):
        pass

    def set(self, key, value):
        self[key] = value
        return True

    def add(self, key, value):
        if key in self:
            return False
        self[key] = value
        return True

    def replace(self, key, value):
        if key not in self:
            return False
        self[key] = value
        return True

    def delete(self, key):
        if not key in self:
            return True  # that's how memcache libs do...
        del self[key]
        return True
