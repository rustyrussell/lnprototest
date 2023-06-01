# Variations on open_channel, accepter + opener perspectives
from lnprototest import (
    TryAll,
    Block,
    FundChannel,
    ExpectMsg,
    ExpectTx,
    Msg,
    RawMsg,
    AcceptFunding,
    CreateFunding,
    Commit,
    Runner,
    remote_funding_pubkey,
    remote_revocation_basepoint,
    remote_payment_basepoint,
    remote_htlc_basepoint,
    remote_per_commitment_point,
    remote_delayed_payment_basepoint,
    Side,
    CheckEq,
    msat,
    remote_funding_privkey,
    regtest_hash,
    bitfield,
)
from lnprototest.stash import (
    sent,
    rcvd,
    commitsig_to_send,
    commitsig_to_recv,
    channel_id,
    funding_txid,
    funding_tx,
    funding,
    stash_field_from_event,
)
from helpers import (
    utxo,
    tx_spendable,
    run_runner,
    merge_events_sequences,
    funding_amount_for_utxo,
    pubkey_of,
    gen_random_keyset,
)
from spec_helper import connect_to_node_helper


def test_open_channel_announce_features(runner: Runner) -> None:
    """Check that the announce features works correctly"""
    connections_events = connect_to_node_helper(
        runner=runner, tx_spendable=tx_spendable, conn_privkey="02"
    )

    test_events = [
        TryAll(
            # BOLT-a12da24dd0102c170365124782b46d9710950ac1 #9:
            # | 20/21 | `option_anchor_outputs`          | Anchor outputs
            Msg("init", globalfeatures="", features=bitfield(13, 21)),
            # BOLT #9:
            # | 12/13 | `option_static_remotekey`        | Static key for remote output
            Msg("init", globalfeatures="", features=bitfield(13)),
            # And not.
            Msg("init", globalfeatures="", features=""),
        ),
    ]
    run_runner(runner, merge_events_sequences(connections_events, test_events))


def test_open_channel_from_accepter_side(runner: Runner) -> None:
    """Check the open channel from an accepter view point"""
    local_funding_privkey = "20"
    local_keyset = gen_random_keyset(int(local_funding_privkey))
    connections_events = connect_to_node_helper(
        runner=runner, tx_spendable=tx_spendable, conn_privkey="02"
    )

    # Accepter side: we initiate a new channel.
    test_events = [
        Msg(
            "open_channel",
            chain_hash=regtest_hash,
            temporary_channel_id="00" * 32,
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
        ),
        # Ignore unknown odd messages
        TryAll([], RawMsg(bytes.fromhex("270F"))),
        ExpectMsg(
            "accept_channel",
            temporary_channel_id=sent(),
            funding_pubkey=remote_funding_pubkey(),
            revocation_basepoint=remote_revocation_basepoint(),
            payment_basepoint=remote_payment_basepoint(),
            delayed_payment_basepoint=remote_delayed_payment_basepoint(),
            htlc_basepoint=remote_htlc_basepoint(),
            first_per_commitment_point=remote_per_commitment_point(0),
            minimum_depth=stash_field_from_event("accept_channel"),
            channel_reserve_satoshis=9998,
        ),
        # Ignore unknown odd messages
        TryAll([], RawMsg(bytes.fromhex("270F"))),
        # Create and stash Funding object and FundingTx
        CreateFunding(
            *utxo(0),
            local_node_privkey="02",
            local_funding_privkey=local_funding_privkey,
            remote_node_privkey=runner.get_node_privkey(),
            remote_funding_privkey=remote_funding_privkey()
        ),
        Commit(
            funding=funding(),
            opener=Side.local,
            local_keyset=local_keyset,
            local_to_self_delay=rcvd("to_self_delay", int),
            remote_to_self_delay=sent("to_self_delay", int),
            local_amount=msat(sent("funding_satoshis", int)),
            remote_amount=0,
            local_dust_limit=546,
            remote_dust_limit=546,
            feerate=253,
            local_features=sent("init.features"),
            remote_features=rcvd("init.features"),
        ),
        Msg(
            "funding_created",
            temporary_channel_id=rcvd(),
            funding_txid=funding_txid(),
            funding_output_index=0,
            signature=commitsig_to_send(),
        ),
        ExpectMsg(
            "funding_signed",
            channel_id=channel_id(),
            signature=commitsig_to_recv(),
        ),
        # Mine it and get it deep enough to confirm channel.
        Block(blockheight=103, number=3, txs=[funding_tx()]),
        ExpectMsg(
            "channel_ready",
            channel_id=channel_id(),
            second_per_commitment_point="032405cbd0f41225d5f203fe4adac8401321a9e05767c5f8af97d51d2e81fbb206",
        ),
        Msg(
            "channel_ready",
            channel_id=channel_id(),
            second_per_commitment_point="027eed8389cf8eb715d73111b73d94d2c2d04bf96dc43dfd5b0970d80b3617009d",
        ),
        # Ignore unknown odd messages
        TryAll([], RawMsg(bytes.fromhex("270F"))),
    ]
    run_runner(runner, merge_events_sequences(connections_events, test_events))


def test_open_channel_opener_side(runner: Runner) -> None:
    local_funding_privkey = "20"
    local_keyset = gen_random_keyset(int(local_funding_privkey))
    connections_events = connect_to_node_helper(
        runner=runner, tx_spendable=tx_spendable, conn_privkey="02"
    )

    # Now we test the 'opener' side of an open_channel (node initiates)
    test_events = [
        FundChannel(amount=999877),
        # This gives a channel of 999877sat
        ExpectMsg(
            "open_channel",
            chain_hash=regtest_hash,
            funding_satoshis=999877,
            push_msat=0,
            dust_limit_satoshis=546,
            htlc_minimum_msat=0,
            channel_reserve_satoshis=9998,
            to_self_delay=6,
            funding_pubkey=remote_funding_pubkey(),
            revocation_basepoint=remote_revocation_basepoint(),
            payment_basepoint=remote_payment_basepoint(),
            delayed_payment_basepoint=remote_delayed_payment_basepoint(),
            htlc_basepoint=remote_htlc_basepoint(),
            first_per_commitment_point=remote_per_commitment_point(0),
            # FIXME: Check more fields!
            channel_flags="01",
        ),
        Msg(
            "accept_channel",
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
        ),
        # Ignore unknown odd messages
        TryAll([], RawMsg(bytes.fromhex("270F"))),
        ExpectMsg("funding_created", temporary_channel_id=rcvd("temporary_channel_id")),
        # Now we can finally stash the funding information.
        AcceptFunding(
            rcvd("funding_created.funding_txid"),
            funding_output_index=rcvd("funding_created.funding_output_index", int),
            funding_amount=rcvd("open_channel.funding_satoshis", int),
            local_node_privkey="02",
            local_funding_privkey=local_funding_privkey,
            remote_node_privkey=runner.get_node_privkey(),
            remote_funding_privkey=remote_funding_privkey(),
        ),
        Commit(
            funding=funding(),
            opener=Side.remote,
            local_keyset=local_keyset,
            local_to_self_delay=rcvd("open_channel.to_self_delay", int),
            remote_to_self_delay=sent("accept_channel.to_self_delay", int),
            local_amount=0,
            remote_amount=msat(rcvd("open_channel.funding_satoshis", int)),
            local_dust_limit=sent("accept_channel.dust_limit_satoshis", int),
            remote_dust_limit=rcvd("open_channel.dust_limit_satoshis", int),
            feerate=rcvd("open_channel.feerate_per_kw", int),
            local_features=sent("init.features"),
            remote_features=rcvd("init.features"),
        ),
        # Now we've created commit, we can check sig is valid!
        CheckEq(rcvd("funding_created.signature"), commitsig_to_recv()),
        Msg(
            "funding_signed",
            channel_id=channel_id(),
            signature=commitsig_to_send(),
        ),
        # It will broadcast tx
        ExpectTx(rcvd("funding_created.funding_txid")),
        # Mine three blocks to confirm channel.
        Block(blockheight=103, number=3),
        Msg(
            "channel_ready",
            channel_id=sent(),
            second_per_commitment_point=local_keyset.per_commit_point(1),
        ),
        ExpectMsg(
            "channel_ready",
            channel_id=sent(),
            second_per_commitment_point=remote_per_commitment_point(1),
        ),
        # Ignore unknown odd messages
        TryAll([], RawMsg(bytes.fromhex("270F"))),
    ]
    run_runner(runner, merge_events_sequences(connections_events, test_events))
