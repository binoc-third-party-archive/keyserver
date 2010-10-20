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
import unittest
import time

from keyexchange.filtering import IPFiltering
from webtest import TestApp, AppError
from webob.exc import HTTPForbidden, HTTPBadRequest


class FakeApp(object):
    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        if 'boo' in path:
            start_response('400 Bad Request',
                           [('Content-Type', 'text/plain')])
            return ['400 Bad Request', 'error']
        else:
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return ['something', 'valid']


class TestIPFiltering(unittest.TestCase):

    def setUp(self):
        # this setting will blacklist an IP that does more than 5 calls
        app = IPFiltering(FakeApp(), queue_size=10, blacklist_ttl=.5,
                          treshold=.5, br_queue_size=3,
                          br_blacklist_ttl=.5)
        self.app = TestApp(app)

    def test_reached_max(self):
        env = {'REMOTE_ADDR': '127.0.0.1'}

        # no ip, no chocolate
        try:
            self.app.get('/', status=403)
        except HTTPForbidden:
            pass

        # doing 5 calls
        for i in range(5):
            self.app.get('/', status=200, extra_environ=env)

        # the next call should be rejected
        try:
            self.app.get('/', status=403, extra_environ=env)
        except HTTPForbidden:
            pass

        # TTL test - we make the assumption that the beginning of the
        # test took less than 1.5s

        # we should be on track now
        time.sleep(1.5)
        self.app.get('/', status=200, extra_environ=env)


    def test_reached_br_max(self):
        env = {'REMOTE_ADDR': '127.0.0.3'}

        # doing 2 calls
        for i in range(2):
            self.assertRaises(AppError, self.app.get, '/boo', status=200,
                              extra_environ=env)


        # the next call should be rejected
        try:
            self.app.get('/', status=403, extra_environ=env)
        except HTTPForbidden:
            pass

        # TTL test - we make the assumption that the beginning of the
        # test took less than 1.5s

        # we should be on track now
        time.sleep(1.5)
        self.app.get('/', status=200, extra_environ=env)


    def test_basics(self):
        app = self.app.app
        app.br_treshold = app.treshold = 1.1
        env = {'REMOTE_ADDR': '127.0.0.1'}

        # saturating the queue now to make sure its LRU-ing right
        for i in range(15):
            try:
                self.app.get('/', extra_environ=env)
            except HTTPForbidden:
                pass

        self.assertEqual(len(app._last_ips), 10)
        env = {'REMOTE_ADDR': '127.0.0.2'}

        for i in range(15):
            try:
                self.app.get('/boo', extra_environ=env)
            except (AppError, HTTPForbidden):
                pass

        # let's see how's the queue is doing
        self.assertEqual(len(app._last_br_ips), 3)
