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
"""
IP Filtering middleware. This middleware will:

- Reject all new attempts made by an IP, if this IP already made too many
  attempts.
- Reject IPs are are making too many bad requests

To perform this, we keep a LRU of the last N ips in memory and increment the
calls. If an IP as a high number of calls, it's blacklisted.

For the bad request counter, the same technique is used.

Blacklisted IPs are kept in memory with a TTL.
"""
import threading
import time


# TODO gets/cas

class Blacklist(object):
    """IP Blacklist with TTL and memcache support.

    IPs are saved/loaded from Memcached so several apps can share the
    blacklist.
    """
    def __init__(self, cache_server, key='blacklist'):
        self._lock = threading.RLock()
        self._cache = cache_server
        self._key = key

    def _ip_key(self, ip):
        return '%s:%s' % (self._key, ip)

    def add(self, ip, ttl=360):
        with self._lock:
            # keeping a list of blacklisted IPs
            ips = self._cache.gets(self._key)
            if ips is None:
                ips = set(ip)
            if ip not in ips:
                ips.add(ip)

            if not self._cache.set(self._key, ips):
                raise MemcachedFailureError()

            # one key per ip as well, for the TTL
            if not self._cache.set(self._ip_key(ip), 1,
                                        time=ttl):
                raise MemcachedFailureError()

    def __contains__(self, ip):
        return self._cache.get(self._ip_key(ip)) is not None

    def get_ips(self):
        ## XXX only for the admin UI
        with self._lock:
            ips = self._cache.get(self._key)
            if ips is None:
                return set()

            # removing ttl-ed ips
            # XXX needs something better here
            res = []
            for ip in ips:
                if self._cache.get(self._ip_key(ip)) is None:
                    continue
                res.append(ip)

            if res != ips:
                self._cache.set(self._key, set(res))

            return res

    def __len__(self):
        return len(self.get_ips())

    def _remove_from_list(self, ip):
        ips = self._cache.gets(self._key)
        if ips is None:
            return
        if ip in ips:
            ips.remove(ip)
        if not self._cache.set(self._key, ips):
            raise MemcachedFailureError()

    def remove(self, ip):
        with self._lock:
            if not self._cache.delete(self._ip_key(ip)):
                raise MemcachedFailureError()
            self._remove_from_list(ip)
