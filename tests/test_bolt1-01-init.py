#! /usr/bin/python
# Variations on init exchange.
# Spec: MUST respond to known feature bits as specified in [BOLT #9](09-features.md).

from lnprototest import TryAll, Connect, Disconnect, EventError, ExpectMsg, Msg, ExpectError
import pyln.proto.message.bolt1
from fixtures import *  # noqa: F401,F403


def has_bit(msg, field, bitnum):
    if len(msg.fields[field]) < bitnum // 8:
        return False
    return (msg.fields[field][bitnum // 8] & (1 << (bitnum % 8)) != 0)


# SHOULD NOT set features greater than 13 in `globalfeatures`.
def no_gf13(event, msg):
    for i in range(13, len(msg.fields['globalfeatures']) * 8):
        if has_bit(msg, 'globalfeatures', i):
            raise EventError(event, "globalfeatures bit {} set".format(i))


# We assume these are unused.
def no_34_35(event, msg):
    if has_bit(msg, 'features', 34) or has_bit(msg, 'features', 35):
        raise EventError(event, "features set bits 34/35 unexpected: {}".format(msg))


def test_init(runner, namespaceoverride):
    # We override default namespace since we only need BOLT1
    namespaceoverride(pyln.proto.message.bolt1.namespace)
    test = [Connect(connprivkey='03'),
            ExpectMsg('init'),
            Msg('init', globalfeatures='', features=''),

            # optionally disconnect that first one
            TryAll([[], Disconnect()]),

            Connect(connprivkey='02'),
            TryAll([
                # Even if we don't send anything, it should send init.
                [ExpectMsg('init')],

                # Minimal possible init message.
                # Spec: MUST send `init` as the first Lightning message for any connection.
                [ExpectMsg('init'),
                 Msg('init', globalfeatures='', features='')],

                # SHOULD NOT set features greater than 13 in `globalfeatures`.
                [ExpectMsg('init', if_match=no_gf13),
                 # init msg with unknown odd global bit (19): no error
                 Msg('init', globalfeatures='020000', features='')],

                # Sanity check that bits 34 and 35 are not used!
                [ExpectMsg('init', if_match=no_34_35),
                 # init msg with unknown odd local bit (19): no error
                 Msg('init', globalfeatures='', features='020000')],

                # init msg with unknown even local bit (34): you will error
                [ExpectMsg('init'),
                 Msg('init', globalfeatures='', features='0100000000'),
                 ExpectError()],

                # init msg with unknown even global bit (34): you will error
                [ExpectMsg('init'),
                 Msg('init', globalfeatures='0100000000', features=''),
                 ExpectError()],

                # FIXME: Test based on features of runner!
            ])]

    runner.run(test)
