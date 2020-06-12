#! /usr/bin/env python3
# Init exchange, with unknown messages
#

from lnprototest import (TryAll, Connect, ExpectMsg, Msg, RawMsg, ExpectError, Runner)
import pyln.proto.message.bolt1
from fixtures import *  # noqa: F401,F403
from typing import Any


def test_unknowns(runner: Runner, namespaceoverride: Any) -> None:
    # We override default namespace since we only need BOLT1
    namespaceoverride(pyln.proto.message.bolt1.namespace)
    test = [Connect(connprivkey='03'),
            ExpectMsg('init'),
            Msg('init', globalfeatures='', features=''),
            TryAll([
                [],
                # BOLT #1:
                # A receiving node:
                #   - upon receiving a message of _odd_, unknown type:
                #     - MUST ignore the received message.
                [RawMsg(bytes.fromhex('270F'))],


                # BOLT #1:
                # A receiving node:...
                #   - upon receiving a message of _even_, unknown type:
                #     - MUST close the connection.
                #     - MAY fail the channels.
                [RawMsg(bytes.fromhex('2710')),
                 ExpectError()]
            ])]

    runner.run(test)
