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
import cPickle
import copy_reg
from collections import deque
import threading
import time


class MemcachedFailureError(Exception):
    pass


class IPCounter(object):
    """Keeps a counter for each IP.

    Every IP is kept into memcached with a counter and a last refresh data.
    When the last refresh date is > ttl, the counter starts back to 0.
    """
    def __init__(self, cache_server, prefix='counter', ttl=360):
        self._ttl = float(ttl)
        self._cache_server = cache_server
        self._lock = threading.RLock()
        self._prefix = prefix

    def _key(self, ip):
        return '%s:%s' % (self._prefix, ip)

    def increment(self, ip):
        """Increments the IP counter and returns the new value."""
        self._lock.acquire()
        try:
            # XXX race condition (gets/cas)
            count = self._cache_server.get(self._key(ip))
            if count is None:
                if not self._cache_server.set(self._key(ip), '1', self._ttl):
                    raise MemcachedFailureError()
                return 1
            else:
                res = self._cache_server.incr(self._key(ip))
                if res is None:
                    # the key has ttl-ed, we need to re-create one
                    if not self._cache_server.set(self._key(ip), '1',
                            self._ttl):
                        raise MemcachedFailureError()
                    return 1
                return res
        finally:
            self._lock.release()

    def count(self, ip):
        """Returns the current IP count."""
        count = self._cache_server.get(self._key(ip))
        if count is None:
            return 0
        return int(count)

    def __contains__(self, ip):
        return self.count(ip) > 0

    def remove(self, ip):
        self._lock.acquire()
        try:
            self._cache_server.delete(self._key(ip))
        finally:
            self._lock.release()
