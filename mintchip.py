#!/usr/bin/env python

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


MINTCHIP_ID = 220676381741154309

import base64
import datetime
from google.appengine.ext import db


#from Crypto.Util.number import bytes_to_long
def bytes_to_long(s):
    h = '0x'
    for c in s:
        h += '%02x' % ord(c)
    return int(h, 16)


# is this a bug of the mintchip api?
def weird_bytes_to_long(s):
    h = ''
    for c in s:
        h += (hex(ord(c))[2:]).zfill(2)
    return int(h)


class ValueMessage(db.Model):
    recv_time = db.DateTimeProperty()
    payer_id = db.StringProperty()
    payee_id = db.StringProperty()
    paid_val = db.IntegerProperty()
    raw_msg = db.TextProperty()


class MintChip:
    chip_id = str(MINTCHIP_ID)

    def receive(self, raw_msg):
        msg = parse(raw_msg)
        if False:  # is_acceptable(raw_msg):
            return False
        else:
            entry = ValueMessage(
                    recv_time=datetime.datetime.utcnow(),
                    payer_id=str(msg['payer-id']),
                    payee_id=str(msg['payee-id']),
                    paid_val=msg['value'],
                    raw_msg=raw_msg)
            entry.put()
            return True

    def credit_logs(self, num_recent):
        q = db.Query(ValueMessage)
        q.order('-recv_time')
        ret = q.fetch(limit=num_recent)
        return ret


# tag-length-value
def readTLV(s):
    tag = ord(s[0])
    tmp = ord(s[1])
    if tmp > 127:
        long_len = tmp - 128
        length = bytes_to_long(s[2: 2 + long_len])
        value = s[2 + long_len: 2 + long_len + length]
        tailing = s[2 + long_len + length:]
    else:
        length = tmp
        value = s[2: 2 + length]
        tailing = s[2 + length:]
    return tag, length, value, tailing


def parse(msg):
    msg = base64.b64decode(msg)
    result = {}

    tlv = readTLV(msg)
    assert tlv[0] == 0x60 or tlv[-1]
    tlv = readTLV(tlv[2])
    assert tlv[0] == 0x30
    tlv = readTLV(tlv[2])
    assert tlv[0] == 0xA0
    ver_tlv = readTLV(tlv[2])
    assert ver_tlv[0] == 0x0A
    version = bytes_to_long(ver_tlv[2])
    assert version == 1
    tlv = readTLV(tlv[3])
    if tlv[0] == 0xA1:
        anno_tlv = readTLV(tlv[2])
        assert anno_tlv[0] == 0x16
        result['annotation'] = anno_tlv[2]
        tlv = readTLV(tlv[3])
    assert tlv[0] == 0xA2
    tlv = readTLV(tlv[2])
    msg_type_dict = {
            0xA0: 'auth-req',
            0xA1: 'vm-req',
            0xAA: 'auth-resp',
            0xAB: 'vm-resp',
    }
    assert tlv[0] in msg_type_dict
    result['type'] = msg_type_dict[tlv[0]]

    assert result['type'] == 'vm-resp'  # only parse value msg now
    if result['type'] == 'vm-resp':
        tlv = readTLV(tlv[2])
        assert tlv[0] == 0x30
        tlv = readTLV(tlv[2])
        assert tlv[0] == 0x30

        if tlv[3]:
            cert_tlv = readTLV(tlv[3])
            assert cert_tlv[0] == 0xA0
            assert not cert_tlv[3]
            tlv = list(tlv)
            tlv[3] = chr(48) + tlv[3][1:]
            result['payer-cert'] = tlv[3]

        tlv = readTLV(tlv[2])
        assert tlv[0] == 0x04
        result['secure-element-version'] = bytes_to_long(tlv[2])

        tlv = readTLV(tlv[3])
        assert tlv[0] == 0x04
        result['payer-id'] = weird_bytes_to_long(tlv[2])

        tlv = readTLV(tlv[3])
        assert tlv[0] == 0x04
        result['payee-id'] = weird_bytes_to_long(tlv[2])

        tlv = readTLV(tlv[3])
        assert tlv[0] == 0x04
        # result['currency'] = bytes_to_long(tlv[2])

        tlv = readTLV(tlv[3])
        assert tlv[0] == 0x04
        result['value'] = bytes_to_long(tlv[2])

        tlv = readTLV(tlv[3])
        assert tlv[0] == 0x04
        result['datatime'] = tlv[2]

        tlv = readTLV(tlv[3])
        assert tlv[0] == 0x04
        # secret value made for/by royal mint
        # result['tac'] = bytes_to_long(tlv[2])

        tlv = readTLV(tlv[3])
        assert tlv[0] == 0x04
        result['signature'] = tlv[2]

    return result


if __name__ == '__main__':
    msg = """
YIIDMTCCAy2gAwoBAaEIFgZMZW5vdm+iggMaq4IDFjCCAxIwgccEASYECBMQAAAAATZZBAgTEAAA
AACHMwQBAQQDAADIBATODQM/BAMn460EGGfyMmjrKmsOISMJ6U35TPWYf1aT5F5nIgSBgBARkXkJ
VQgpilQjQslkBtT6dcmgj1cklvI7+srq1hMtHhurSsY8ghMTFpZPdQZw4c9dxPnaWSk9v8AzbGtZ
FKByjYirbnsjSwv9XP2TjS8MhH+DvF8c7RN6vEsB12zOhoWm783Y+eiuBban6i38/8tUQ40StaRY
Lwf25j3d74u8oIICRDCCAa2gAwIBAgIBATANBgkqhkiG9w0BAQUFADBuMR8wHQYDVQQDDBZTUyBD
eWNsZSAwIFNTIE51bWJlciAxMSAwHgYDVQQLDBdlQ29pbiBTaWduaW5nIEF1dGhvcml0eTEcMBoG
A1UECgwTUm95YWwgQ2FuYWRpYW4gTWludDELMAkGA1UEBhMCQ0EwHhcNMTIwMzA3MDczNzM2WhcN
MjIwMzA3MDczNzM2WjBiMRkwFwYDVQQDDBAxMzEwMDAwMDAwMDEzNjU5MRowGAYDVQQLDBFlQ29p
biBBc3NldCBTdG9yZTEcMBoGA1UECgwTUm95YWwgQ2FuYWRpYW4gTWludDELMAkGA1UEBhMCQ0Ew
gZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAKZb+7A7e6YOJrAngyokRM66jeuJb+DRdB2IU32K
Zkw439q2ldxqvSWgaD539h8TreeMTcF+2zHqamA92IvUfes/S/N9nT/20yi9ec2LWQ/Tf4zsEgeU
zc88hXD+lGb5l/LznwrUL45KfYC4pLP/ECXwkuyDCMx338mtVdiFrRAJAgMBAAEwDQYJKoZIhvcN
AQEFBQADgYEADnfXLjOr6fq5XJEMh/7ERTRZfEbys47cByOvYR+tAVCJBzgR6kwJt178ILHeoga7
PAU3v5HffKrzOXa9u/Fbus8mBuystiIaWIFF2mZThQ3YiVEsv2PBvgWoUKottTTzJqhJuNNawBZR
t1CEKNq8nGrHyT3poW0Q6pkmCXbYnQY=
"""

    from pprint import pprint
    pprint(parse(msg))
