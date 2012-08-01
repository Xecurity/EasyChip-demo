"""
    Copyright (C) 2012 Bo Zhu <zhu@xecurity.ca>

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.
"""


import webapp2
import cgi
import json
import urllib2
try:
    from Crypto.Random import random
    random.getrandbits(1)
except:
    import random  # dev_appserver.py can't use pycrypto
from google.appengine.api import channel
from mintchip import MintChip


class ChannelHandler(webapp2.RequestHandler):
    def get(self):
        client_id = hex(random.getrandbits(128))[2:].rstrip('L')
        token = channel.create_channel(client_id, duration_minutes=60)
        result = {
                'channel_id': client_id,
                'token': token
        }
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(result))


class BuyHandler(webapp2.RequestHandler):
    def post(self):
        body_json = json.loads(cgi.escape(self.request.body))
        data = {
                'payer_email': body_json['payer_email'],
                'payee_id': '1310000000008733',
                'amount': '1',  # 1 cent
                #'amount': 1,  # int is not allowed by gcm?
                'annotation': 'Paid via EasyChip',
                'channel_id': body_json['channel_id'],
                'callback_url': 'https://easychip-demo.appspot.com/pay',
                'random': hex(random.getrandbits(128))[2:].rstrip('L')
        }
        data = json.dumps(data)
        req = urllib2.Request(
                url='https://xecure-easychip.appspot.com/api/charge',
                data=data,
                headers={'Content-Type': 'application/json'}
        )

        #resp = urllib2.urlopen(req, timeout=120).read()
        try:
            resp = urllib2.urlopen(req, timeout=120).read()
        except urllib2.HTTPError as err:
            self.response.set_status(err.code)
            self.response.write(err.read())
            return
        except Exception as err:
            if hasattr(err, 'reason'):
                self.response.set_status(500)
                self.response.write('Error: ' + str(err.reason))
                return
            else:
                self.response.set_status(500)
                self.response.write('Error: ' + str(err))
                return
        if resp == 'OK':
            self.response.set_status(200)
            self.response.write('OK')
        else:
            # should never reach here
            self.response.set_status(500)
            self.response.write('Error: Disallowed Response')


class HistoryHandler(webapp2.RequestHandler):
    def get(self):
        chip = MintChip()
        records = chip.credit_logs(num_recent=10)
        result = []
        for r in records:
            amount = '%.2f' % (r.paid_val / 100.0)
            result.append({
                    'payer': r.payer_id,
                    'amount': amount,
                    'time': r.recv_time.ctime(),
            })
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write(json.dumps(result))


class PayHandler(webapp2.RequestHandler):
    def post(self):
        body_json = json.loads(cgi.escape(self.request.body))
        chip = MintChip()
        chip.receive(body_json['value_message'])
        channel.send_message(body_json['channel_id'], 'paid')


app = webapp2.WSGIApplication([
    ('/channel', ChannelHandler),
    ('/buy', BuyHandler),
    ('/pay', PayHandler),
    ('/history', HistoryHandler),
], debug=True)
