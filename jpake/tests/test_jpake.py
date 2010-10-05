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
""" Functional test to simulate a JPake transaction.
"""
import unittest
import threading
import json
import time

from webtest import TestApp

from jpake.tests.client import JPAKE
from jpake.wsgiapp import make_app


class User(threading.Thread):

    def __init__(self, name, passwd, app, data=None, cid=None):
        threading.Thread.__init__(self)
        self.app = app
        self.name = name
        self.pake = JPAKE(passwd, signerid=name)
        self.data = data
        if data is not None:
            res = self.app.get('/new_channel')
            self.cid = str(json.loads(res.body))
        else:
            self.cid = cid
        self.curl = '/%s' % self.cid

    def _wait_data(self, etag=''):
        status = 304
        attempts = 0
        while status == 304 and attempts < 10:

            res = self.app.get(self.curl,
                                headers={'If-None-Match': etag})

            status = res.status_int
            attempts +=1
            if status == 304:
                time.sleep(.2)

        if status == 304:
            raise AssertionError('Failed to get next step')
        body = json.loads(res.body)
        def _clean(body):
            if isinstance(body, unicode):
                return str(body)
            res = {}
            for key, value in body.items():
                if isinstance(value, unicode):
                    value = str(value)
                elif isinstance(value, dict):
                    value = _clean(value)
                res[str(key)] = value
            return res
        return _clean(body)


class Sender(User):
    def run(self):
        # step 1
        print '%s sends step one' % self.name
        one = json.dumps(self.pake.one(), ensure_ascii=True)
        res = self.app.put(self.curl, params=one)
        etag = res.headers['ETag']

        print '%s now waits for step one from receiver' % self.name
        other_one = self._wait_data(etag)
        print '%s received step one' % self.name

        # step 2
        print '%s sends step two' % self.name
        two = json.dumps(self.pake.two(other_one))
        res = self.app.put(self.curl, params=two)
        etag = res.headers['ETag']
        time.sleep(.2)

        # now wait for step 2 from the other iside
        other_two = self._wait_data(etag)
        print '%s received step two from receiver' % self.name

        # then we build the key
        self.key = self.pake.three(other_two)

        # and we send the data (no crypting in the tests)
        print '%s sends the data' % self.name
        data = json.dumps(self.data)
        res = self.app.put(self.curl, params=data)


class Receiver(User):
    def run(self):
        # waiting for step 1
        print '%s waits for step one from sender' % self.name
        other_one = self._wait_data()

        # step 1
        print '%s sends step one to receiver' % self.name
        one = json.dumps(self.pake.one(), ensure_ascii=True)
        res = self.app.put(self.curl, params=one)
        etag = res.headers['ETag']

        # waiting for step 2
        print '%s waits for step two from sender' % self.name
        other_two = self._wait_data(etag)

        # sending step 2
        print '%s sends step two' % self.name
        two = json.dumps(self.pake.two(other_one))
        res = self.app.put(self.curl, params=two)
        etag = res.headers['ETag']

        # then we build the key
        self.key = self.pake.three(other_two)

        # and we get the data (no crypting in the tests)
        self.data = self._wait_data(etag)
        print '%s received the data' % self.name


class TestWsgiApp(unittest.TestCase):

    def setUp(self):
        self.app = TestApp(make_app({}))

    def test_session(self):
        # we want to send data in a secure channel
        data = {'username': 'bob',
                'password': 'secret'}

        # let's create two end-points
        bob = Sender('Bob', 'secret', self.app, data)

        # bob creates a cid, sarah has to provide
        sarah = Receiver('Sarah', 'secret', self.app, cid=bob.cid)

        # bob starts
        bob.start()

        # let's wait a bit
        time.sleep(.5)

        # sarah starts next
        sarah.start()

        # let's wait for the transaction to end
        bob.join()
        sarah.join()

        # bob and sarah should have the same key
        self.assertEqual(bob.key, sarah.key)

        # sarah should have receive the encrypted data from bob
        original_data = bob.data.items()
        original_data.sort()
        received_data = sarah.data.items()
        received_data.sort()
        self.assertEqual(original_data, received_data)
