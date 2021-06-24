#! /usr/bin/env python3

from lnprototest import TryAll, Connect, Block, ExpectMsg, Msg, Runner, KeySet, regtest_hash, bitfield, channel_type_csv, OneOf, ExpectError
from helpers import tx_spendable, funding_amount_for_utxo, pubkey_of
from typing import Any
import pytest


def test_open_channel(runner: Runner, with_proposal: Any) -> None:
    """Tests for https://github.com/lightningnetwork/lightning-rfc/pull/880"""
    with_proposal(channel_type_csv)

    # This is not a feature bit, so use support_ to mark it.
    if runner.has_option('supports_open_accept_channel_types') is None:
        pytest.skip('Needs supports_open_accept_channel_types')

    local_funding_privkey = '20'

    local_keyset = KeySet(revocation_base_secret='21',
                          payment_base_secret='22',
                          htlc_base_secret='24',
                          delayed_payment_base_secret='23',
                          shachain_seed='00' * 32)

    avail_types = []
    # We expect them to ignore the first (bogus) one!
    for t in (bitfield(8), bitfield(13), '', bitfield(13, 21)):
        avail_types.append('{features=' + t + '}')

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
                tlvs='{channel_types={types=[' + ','.join(avail_types) + ']}}'),

            # BOLT #2
            #   - if it sets `channel_type`:
            #     - MUST set it to one of the `channel_types` from `open_channel`
            OneOf([ExpectMsg('accept_channel',
                             tlvs='{channel_type={type={features=' + bitfield(13) + '}}}')],
                  [ExpectMsg('accept_channel',
                             tlvs='{channel_type={type={features=' + bitfield(13, 21) + '}}}')],
                  [ExpectMsg('accept_channel',
                             tlvs='{channel_type={type={features=' + '' + '}}}')])]

    runner.run(test)


def test_open_channel_bad_type(runner: Runner, with_proposal: Any) -> None:
    """Tests for https://github.com/lightningnetwork/lightning-rfc/pull/880"""
    with_proposal(channel_type_csv)

    # This is not a feature bit, so use support_ to mark it.
    if runner.has_option('supports_open_accept_channel_types') is None:
        pytest.skip('Needs supports_open_accept_channel_types')

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
                tlvs='{channel_types={types=[{features=' + bitfield(1) + '}]}}'),

            # BOLT #2
            # The receiving node MUST fail the channel if:
            #   - It supports `channel_types` and none of the `channel_types`
            #     are suitable.
            ExpectError()]

    runner.run(test)
