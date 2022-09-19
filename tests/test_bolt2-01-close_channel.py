#! /usr/bin/env python3
"""
testing bolt2 closing channel operation described in the lightning network speck
https://github.com/lightning/bolts/blob/master/02-peer-protocol.md#channel-close

The overview of what we test in this integration testing is described by the following
figure.

 +-------+                              +-------+
 |       |--(1)-----  shutdown  ------->|       |
 |       |<-(2)-----  shutdown  --------|       |
 |       |                              |       |
 |       | <complete all pending HTLCs> |       |
 |       |    <must not add HTLCs>      |       |
 |   A   |                 ...          |   B   |
 |       |                              |       |
 |       |--(3)-- closing_signed  F1--->|       |
 |       |<-(4)-- closing_signed  F2----|       |
 |       |              ...             |       |
 |       |--(?)-- closing_signed  Fn--->|       |
 |       |<-(?)-- closing_signed  Fn----|       |
 +-------+                              +-------+

BOLT 2 proposal https://github.com/lightning/bolts/pull/972

 author: https://github.com/vincenzopalazzo
"""
from lnprototest import (
    ExpectMsg,
    Msg,
    Runner,
    MustNotMsg,
)
from helpers import run_runner, merge_events_sequences, tx_spendable
from lnprototest.stash import channel_id
from spec_helper import open_and_announce_channel_helper, connect_to_node_helper
from lnprototest.utils import BitcoinUtils, ScriptType


def test_close_channel_shutdown_msg_normal_case_receiver_side(runner: Runner) -> None:
    """Close the channel with the other peer, and check if the
    shutdown message works in the expected way.

    In particular, this test will check the receiver side.

     ________________________________
    | runner -> shutdown -> ln-node |
    | runner <- shutdown <- ln-node |
    --------------------------------
    """
    # the option that the helper method feels for us
    test_opts = {}
    pre_events_conn = connect_to_node_helper(
        runner, tx_spendable=tx_spendable, conn_privkey="03"
    )
    pre_events = open_and_announce_channel_helper(
        runner, conn_privkey="03", opts=test_opts
    )
    # merge the two events
    pre_events = merge_events_sequences(pre_events_conn, pre_events)
    channel_idx = channel_id()

    script = BitcoinUtils.build_valid_script()
    test = [
        # runner sent shutdown message to ln implementation
        # BOLT 2:
        # - MUST NOT send an `update_add_htlc` after a shutdown.
        Msg(
            "shutdown",
            channel_id=channel_idx,
            scriptpubkey=script,
        ),
        MustNotMsg("update_add_htlc"),
        ExpectMsg(
            "shutdown", ignore=ExpectMsg.ignore_all_gossip, channel_id=channel_idx
        ),
        # TODO: including in bitcoin function the possibility to sign this values
        # Msg(
        #    "closing_signed",
        #    channel_id=channel_idx,
        #    fee_satoshis='100',
        #    signature="0000",
        # ),
        # ExpectMsg("closing_signed")
    ]
    run_runner(runner, merge_events_sequences(pre=pre_events, post=test))


def test_close_channel_shutdown_msg_wrong_script_pubkey_receiver_side(
    runner: Runner,
) -> None:
    """Test close operation from the receiver view point, in the case when
    the sender set a wrong script pub key not specified in the spec.
     ______________________________________________________
    | runner -> shutdown (wrong script pub key) -> ln-node |
    | runner <-         warning msg             <- ln-node |
    -------------------------------------------------------
    """
    # the option that the helper method feels for us
    test_opts = {}
    pre_events_conn = connect_to_node_helper(
        runner, tx_spendable=tx_spendable, conn_privkey="03"
    )
    pre_events = open_and_announce_channel_helper(
        runner, conn_privkey="03", opts=test_opts
    )
    # merge the two events
    pre_events = merge_events_sequences(pre_events_conn, pre_events)
    channel_idx = channel_id()

    script = BitcoinUtils.build_valid_script(ScriptType.INVALID_CLOSE_SCRIPT)

    test = [
        # runner sent shutdown message to the ln implementation
        Msg(
            "shutdown",
            channel_id=channel_idx,
            scriptpubkey=script,
        ),
        MustNotMsg("add_htlc"),
        MustNotMsg("shutdown"),
        ExpectMsg("warning", ignore=ExpectMsg.ignore_all_gossip),
    ]
    run_runner(runner, merge_events_sequences(pre=pre_events, post=test))
