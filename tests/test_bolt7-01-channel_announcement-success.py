#! /usr/bin/env python3
# Simple gossip tests.

from lnprototest import Connect, Block, ExpectMsg, Msg, RawMsg, Funding, LOCAL, MustNotMsg, Disconnect, Runner
from fixtures import *  # noqa: F401,F403
from blocks import BLOCK_102
import time


def test_gossip(runner: Runner) -> None:
    # Funding tx spending 16835ac8c154b616baac524163f41fb0c4f82c7b972ad35d4d6f18d854f6856b/1, feerate 253 to bitcoin privkeys 10 and 20
    funding_tx = '020000000001016b85f654d8186f4d5dd32a977b2cf8c4b01ff4634152acba16b654c1c85a83160100000000ffffffff01c5410f0000000000220020c46bf3d1686d6dbb2d9244f8f67b90370c5aa2747045f1aeccb77d8187117382024730440220798d96d5a057b5b7797988a855217f41af05ece3ba8278366e2f69763c72e785022065d5dd7eeddc0766ddf65557c92b9c52c301f23f94d2cf681860d32153e6ae1e012102d6a3c2d0cf7904ab6af54d7c959435a452b24a63194e1c4e7c337d3ebbb3017b00000000'

    funding = Funding(funding_txid='1d3160756ceeaf5474f389673aafe0484e58260927871ce92f388f72b0409c18',
                      funding_output_index=0,
                      funding_amount=999877,
                      local_node_privkey='02',
                      local_funding_privkey='10',
                      remote_node_privkey='03',
                      remote_funding_privkey='20')

    test = [BLOCK_102,
            Connect(connprivkey='03'),
            ExpectMsg('init'),
            Msg('init', globalfeatures='', features=''),

            # Funding tx spending 16835ac8c154b616baac524163f41fb0c4f82c7b972ad35d4d6f18d854f6856b/1, feerate 253 to bitcoin privkeys 10 and 20
            # txid 189c40b0728f382fe91c87270926584e48e0af3a6789f37454afee6c7560311d
            Block(blockheight=103, number=6, txs=[funding_tx]),

            RawMsg(funding.channel_announcement('103x1x0', '')),

            # New peer connects, asking for initial_routing_sync.  We *won't* relay channel_announcement, as there is no channel_update.
            Connect(connprivkey='05'),
            ExpectMsg('init'),
            Msg('init', globalfeatures='', features='08'),
            MustNotMsg('channel_announcement'),
            Disconnect(),

            RawMsg(funding.channel_update('103x1x0',
                                          LOCAL,
                                          disable=False,
                                          cltv_expiry_delta=144,
                                          htlc_minimum_msat=0,
                                          fee_base_msat=1000,
                                          fee_proportional_millionths=10,
                                          timestamp=int(time.time()),
                                          htlc_maximum_msat=None),
                   connprivkey='03'),

            # Now we'll relay to a new peer.
            Connect(connprivkey='05'),
            ExpectMsg('init'),
            Msg('init', globalfeatures='', features='08'),
            ExpectMsg('channel_announcement',
                      short_channel_id='103x1x0'),
            ExpectMsg('channel_update',
                      short_channel_id='103x1x0',
                      message_flags=0,
                      channel_flags=0),
            Disconnect(),

            # BOLT #7:
            # A node:
            #   - SHOULD monitor the funding transactions in the blockchain, to
            #   identify channels that are being closed.
            #  - if the funding output of a channel is being spent:
            #    - SHOULD be removed from the local network view AND be
            #      considered closed.

            # FIXME: Make funding.py do close tx.
            Block(blockheight=109, txs=['020000000001011d3160756ceeaf5474f389673aafe0484e58260927871ce92f388f72b0409c180000000000ffffffff010e410f00000000001600141b42e1fc7b1cd93a469fa67ed5eabf36ce354dd60400483045022100d93a21312af5b9a46041d2189e5b72f593fc865d920f705d76a25a728de5790302207995cc2dd45ff20c96ccea8b117be41581da8b84466dabfeea728ed858a3a7fd0147304402206d9f5e3b2b2540002ffc37815cef3fbc4ba7646a7bca1aa7605941edd735dee802205130da104d584df6b59c18704c94cd4edd032aed7e0c3044dc8815183552f2dd0147522103d30199d74fb5a22d47b6e054e2f378cedacffcb89904a61d75d0dbd407143e652103e60fce93b59e9ec53011aabc21c23e97b2a31369b87a5ae9c44ee89e2a6dec0a52ae00000000']),

            Connect(connprivkey='05'),
            ExpectMsg('init'),
            Msg('init', globalfeatures='', features='08'),
            MustNotMsg('channel_announcement'),
            MustNotMsg('channel_update')]

    runner.run(test)
