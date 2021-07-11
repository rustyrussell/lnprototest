#! /usr/bin/env python3

from lnprototest import Event, EventError, TryAll, Connect, Block, ExpectMsg, Msg, Runner, KeySet, regtest_hash, bitfield, channel_type_csv, OneOf, ExpectError, has_bit, Side, CheckEq, FundChannel, AcceptFunding, ExpectTx, remote_funding_privkey, ChannelType, Commit, msat, remote_per_commitment_point
from lnprototest.stash import sent, rcvd, funding, sent_msg, rcvd_msg, commitsig_to_send, commitsig_to_recv, channel_id
from helpers import tx_spendable, funding_amount_for_utxo, pubkey_of
from typing import Any
from pyln.proto.message import Message
import pytest
import functools


def has_feature(bit: int, event: Event, msg: Message, runner: Runner) -> None:
    if not has_bit(msg.fields['features'], bit) and not has_bit(msg.fields['features'], bit ^ 1):
        raise EventError(event, "features set bit {} unset: {}".format(bit, msg.to_str()))


def test_open_channel(runner: Runner, with_proposal: Any) -> None:
    """Tests for https://github.com/lightningnetwork/lightning-rfc/pull/880"""
    with_proposal(channel_type_csv)

    # This is not a feature bit, so use support_ to mark it.
    if runner.has_option('supports_open_accept_channel_type') is None:
        pytest.skip('Needs supports_open_accept_channel_type')

    local_funding_privkey = '20'

    local_keyset = KeySet(revocation_base_secret='21',
                          payment_base_secret='22',
                          htlc_base_secret='24',
                          delayed_payment_base_secret='23',
                          shachain_seed='00' * 32)

    # BOLT-channel_types #9:
    # The currently defined types are:
    #  - no features (no bits set)
    #  - `option_static_remotekey` (bit 12)
    #  - `option_anchor_outputs` and `option_static_remotekey` (bits 20 and 12)
    #  - `option_anchors_zero_fee_htlc_tx` and `option_static_remotekey` (bits 22 and 12)
    channel_type_nofeatures = '{channel_type={type=' + '' + '}}'
    channel_type_static_remotekey = '{channel_type={type=' + bitfield(12) + '}}'
    channel_type_anchor_outputs = '{channel_type={type=' + bitfield(20, 12) + '}}'
    channel_type_anchors_zero = '{channel_type={type=' + bitfield(22, 12) + '}}'

    test = [Block(blockheight=102, txs=[tx_spendable]),
            Connect(connprivkey='02'),

            Msg('init', globalfeatures='', features=bitfield(13, 21, 23)),
            FundChannel(amount=999877),

            # BOLT-channel_types #9:
            #   - if it includes `channel_type`:
            #     - MUST set it to a defined type representing the type it wants.
            #     - MUST use the smallest bitmap possible to represent the channel tyoe.
            # 	  - SHOULD NOT set it to a type containing a feature which was not negotiated.
            OneOf(
                [
                    # They support option_anchors_zero_fee_htlc_tx?  Could specify any type in tlv.
                    ExpectMsg('init', if_match=functools.partial(has_feature, 22)),
                    OneOf([ExpectMsg('open_channel', tlvs=channel_type_nofeatures)],
                          [ExpectMsg('open_channel', tlvs=channel_type_static_remotekey)],
                          [ExpectMsg('open_channel', tlvs=channel_type_anchor_outputs)],
                          [ExpectMsg('open_channel', tlvs=channel_type_anchors_zero)])
                ],
                [
                    # They support option_anchor_outputs only?
                    ExpectMsg('init', if_match=functools.partial(has_feature, 20)),
                    OneOf([ExpectMsg('open_channel', tlvs=channel_type_nofeatures)],
                          [ExpectMsg('open_channel', tlvs=channel_type_static_remotekey)],
                          [ExpectMsg('open_channel', tlvs=channel_type_anchor_outputs)])
                ],
                [
                    # They support option_static_remotekey only?
                    ExpectMsg('init', if_match=functools.partial(has_feature, 12)),
                    OneOf([ExpectMsg('open_channel', tlvs=channel_type_nofeatures)],
                          [ExpectMsg('open_channel', tlvs=channel_type_static_remotekey)])
                ],
                [
                    # They support none of the above?
                    ExpectMsg('init'),
                    ExpectMsg('open_channel', tlvs=channel_type_nofeatures)
                ]),

            Msg('accept_channel',
                temporary_channel_id=rcvd(),
                dust_limit_satoshis=546,
                max_htlc_value_in_flight_msat=4294967295,
                channel_reserve_satoshis=9998,
                htlc_minimum_msat=0,
                minimum_depth=3,
                max_accepted_htlcs=483,
                # We use 5, because c-lightning runner uses 6, so this is different.
                to_self_delay=5,
                funding_pubkey=pubkey_of(local_funding_privkey),
                revocation_basepoint=local_keyset.revocation_basepoint(),
                payment_basepoint=local_keyset.payment_basepoint(),
                delayed_payment_basepoint=local_keyset.delayed_payment_basepoint(),
                htlc_basepoint=local_keyset.htlc_basepoint(),
                first_per_commitment_point=local_keyset.per_commit_point(0),
                tlvs=rcvd('open_channel.tlvs.channel_type.type')),

            # Now they should *use* that channel type!
            ExpectMsg('funding_created',
                      temporary_channel_id=rcvd('temporary_channel_id')),

            # Now we can finally stash the funding information.
            AcceptFunding(rcvd('funding_created.funding_txid'),
                          funding_output_index=rcvd('funding_created.funding_output_index', int),
                          funding_amount=rcvd('open_channel.funding_satoshis', int),
                          local_node_privkey='02',
                          local_funding_privkey=local_funding_privkey,
                          remote_node_privkey=runner.get_node_privkey(),
                          remote_funding_privkey=remote_funding_privkey(),
                          channel_type=ChannelType.resolve(rcvd_msg('open_channel'),
                                                           sent_msg('accept_channel'),
                                                           # Won't fall back to features!
                                                           '', '')),

            Commit(funding=funding(),
                   opener=Side.remote,
                   local_keyset=local_keyset,
                   local_to_self_delay=rcvd('open_channel.to_self_delay', int),
                   remote_to_self_delay=sent('accept_channel.to_self_delay', int),
                   local_amount=0,
                   remote_amount=msat(rcvd('open_channel.funding_satoshis', int)),
                   local_dust_limit=sent('accept_channel.dust_limit_satoshis', int),
                   remote_dust_limit=rcvd('open_channel.dust_limit_satoshis', int),
                   feerate=rcvd('open_channel.feerate_per_kw', int)),

            # Now we've created commit, we can check sig is valid!
            CheckEq(rcvd('funding_created.signature'), commitsig_to_recv()),

            Msg('funding_signed',
                channel_id=channel_id(),
                signature=commitsig_to_send()),

            # It will broadcast tx
            ExpectTx(rcvd('funding_created.funding_txid')),

            # Mine three blocks to confirm channel.
            Block(blockheight=103, number=3),

            Msg('funding_locked',
                channel_id=sent(),
                next_per_commitment_point=local_keyset.per_commit_point(1)),

            ExpectMsg('funding_locked',
                      channel_id=sent(),
                      next_per_commitment_point=remote_per_commitment_point(1))]

    runner.run(test)


def test_open_channel_bad_type(runner: Runner, with_proposal: Any) -> None:
    """Tests for https://github.com/lightningnetwork/lightning-rfc/pull/880"""
    with_proposal(channel_type_csv)

    # This is not a feature bit, so use support_ to mark it.
    if runner.has_option('supports_open_accept_channel_type') is None:
        pytest.skip('Needs supports_open_accept_channel_type')

    local_funding_privkey = '20'

    local_keyset = KeySet(revocation_base_secret='21',
                          payment_base_secret='22',
                          htlc_base_secret='24',
                          delayed_payment_base_secret='23',
                          shachain_seed='00' * 32)

    test = [Block(blockheight=102, txs=[tx_spendable]),
            Connect(connprivkey='02'),
            ExpectMsg('init'),

            TryAll(
                # BOLT-a12da24dd0102c170365124782b46d9710950ac1 #9:
                # | 20/21 | `option_anchor_outputs`          | Anchor outputs
                Msg('init', globalfeatures='', features=bitfield(13, 21)),
                # BOLT #9:
                # | 12/13 | `option_static_remotekey`        | Static key for remote output
                Msg('init', globalfeatures='', features=bitfield(13)),
                # And not.
                Msg('init', globalfeatures='', features='')),

            Msg('open_channel',
                chain_hash=regtest_hash,
                temporary_channel_id='00' * 32,
                funding_satoshis=funding_amount_for_utxo(0),
                push_msat=0,
                dust_limit_satoshis=546,
                max_htlc_value_in_flight_msat=4294967295,
                channel_reserve_satoshis=9998,
                htlc_minimum_msat=0,
                feerate_per_kw=253,
                # We use 5, because c-lightning runner uses 6, so this is different.
                to_self_delay=5,
                max_accepted_htlcs=483,
                funding_pubkey=pubkey_of(local_funding_privkey),
                revocation_basepoint=local_keyset.revocation_basepoint(),
                payment_basepoint=local_keyset.payment_basepoint(),
                delayed_payment_basepoint=local_keyset.delayed_payment_basepoint(),
                htlc_basepoint=local_keyset.htlc_basepoint(),
                first_per_commitment_point=local_keyset.per_commit_point(0),
                channel_flags=1,
                tlvs='{channel_type={type=' + bitfield(1) + '}}'),

            # BOLT #2
            # The receiving node MUST fail the channel if:
            #   - It supports `channel_types` and none of the `channel_types`
            #     are suitable.
            ExpectError()]

    runner.run(test)
