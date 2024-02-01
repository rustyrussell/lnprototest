"""
Integration testing for BLIP 04 aka Jamming mitigation

Author: Vincenzo Palazzo <vincenzopalazzo@member.fsf.org>
"""
from lnprototest import Runner
from lnprototest.utils import run_runner, tx_spendable, merge_events_sequences
from lnprototest.utils.ln_spec_utils import (
    connect_to_node_helper,
    open_and_announce_channel_helper,
)

def test_set_endorse_htlc(runner: Runner) -> None:
    """Make sure that the lightning node is setting endorse htlc inside
    the update_add_htlc"""
    connections_events = connect_to_node_helper(
        runner=runner,
        tx_spendable=tx_spendable,
        conn_privkey="02",
    )
    opts = {}
    open_channel_events = open_and_announce_channel_helper(runner, "02", opts=opts)
    pre_events = merge_events_sequences(connections_events, open_channel_events)

    # TODO: add the test here!
    test_events = []
    run_runner(runner, merge_events_sequences(pre_events, test_events))
