#! /usr/bin/env python3
# Init exchange, with unknown messages
#
import pyln.spec.bolt1

from typing import Any

from lnprototest import Connect, ExpectMsg, Msg, RawMsg, Runner
from lnprototest.event import ExpectDisconnect
from lnprototest.utils import run_runner


def test_unknowns(runner: Runner, namespaceoverride: Any) -> None:
    # We override default namespace since we only need BOLT1
    namespaceoverride(pyln.spec.bolt1.namespace)
    test = [
        Connect(connprivkey="03"),
        ExpectMsg("init"),
        Msg(
            "init",
            globalfeatures=runner.runner_features(globals=True),
            features=runner.runner_features(),
        ),
        # BOLT #1:
        # A receiving node:
        #   - upon receiving a message of _odd_, unknown type:
        #     - MUST ignore the received message.
        RawMsg(bytes.fromhex("270F")),
    ]
    run_runner(runner, test)


def test_unknowns_even_message(runner: Runner, namespaceoverride: Any) -> None:
    # We override default namespace since we only need BOLT1
    namespaceoverride(pyln.spec.bolt1.namespace)
    test = [
        Connect(connprivkey="03"),
        ExpectMsg("init"),
        Msg(
            "init",
            globalfeatures=runner.runner_features(globals=True),
            features=runner.runner_features(),
        ),
        # BOLT #1:
        # A receiving node:...
        #   - upon receiving a message of _even_, unknown type:
        #     - MUST close the connection.
        #     - MAY fail the channels.
        RawMsg(bytes.fromhex("2710")),
        ExpectDisconnect(),
    ]
    run_runner(runner, test)
