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
Application entry point.
"""
import datetime
import time
import random
import re
import string
import json
from hashlib import md5

from paste.translogger import TransLogger

from webob.dec import wsgify
from webob.exc import (HTTPNotModified, HTTPNotFound, HTTPServiceUnavailable,
                       HTTPBadRequest)
from webob import Response

URL = re.compile('/(new_channel|[a-zA-Z0-9]*)/?')
ID_CHARS = string.ascii_letters + string.digits
CID_SIZE = 3
MAX_COMBOS = len(ID_CHARS) ** CID_SIZE


def json_response(data, dump=True, **kw):
    """Returns Response containing a json string"""
    if dump:
        data = json.dumps(data)
    resp = Response(data, content_type='application/json')
    for key, value in kw.items():
        setattr(resp, key, value)
    return resp


class JPakeApp(object):

    def __init__(self):
        self.channels = {}

    def _get_new_id(self):
        if len(self.channels) >= MAX_COMBOS:
            raise HTTPServiceUnavailable()

        def _new():
            return ''.join([random.choice(ID_CHARS)
                            for i in range(CID_SIZE)])

        new = _new()
        while new in self.channels:
            new = _new()
        return new

    @wsgify
    def __call__(self, request):
        url = request.environ['PATH_INFO']
        match = URL.match(url)
        if match is None:
            raise HTTPNotFound()

        url = match.groups()[0]
        method = request.method
        if method not in ('GET', 'PUT', 'DELETE'):
            raise HTTPBadRequest()

        if url != 'new_channel':
            kw = {'channel_id': url}
            url = 'channel'
        else:
            kw = {}

        method_name = '%s_%s' % (method.lower(), url)
        if not hasattr(self, method_name):
            raise HTTPNotFound()

        method = getattr(self, method_name)
        return method(request, **kw)

    def get_new_channel(self, request):
        """Returns a new channel id"""
        new_id = self._get_new_id()
        self.channels[new_id] = None, time.time()
        return json_response(new_id)

    def _etag(self, data, dt):
        return md5('%s:%s' % (len(data), dt.isoformat())).hexdigest()

    def put_channel(self, request, channel_id):
        """Append data into channel."""
        data = request.body
        now = datetime.datetime.now()
        etag = self._etag(data, now)
        self.channels[channel_id] = request.body, now, etag
        return json_response(True, etag=etag)

    def get_channel(self, request, channel_id):
        """Grabs data from channel if available."""
        data, when, etag = self.channels[channel_id]
        if request.if_none_match is not None:
            if (hasattr(request.if_none_match, 'etags') and
                etag in request.if_none_match.etags):
                raise HTTPNotModified()
        return json_response(data, dump=False, etag=etag)

    def delete_channel(self, request, channel_id):
        """Delete a channel."""
        if channel_id in self.channels:
            del self.channels[channel_id]
            deleted = True
        else:
            deleted = False
        return json_response(deleted)


def make_app(global_conf, **app_conf):
    """Returns a J-PAKE Application."""
    app = JPakeApp()
    if global_conf.get('translogger', 'false').lower() == 'true':
        app = TransLogger(app, logger_name='jpakeapp',
                          setup_console_handler=True)

    return app
