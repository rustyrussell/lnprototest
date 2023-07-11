"""
Lightning network Speck utils, is a collection of methods that helps to
work with some concept of lightning network RFC

It also contains a method to generate the correct sequence of channel opening
and, and it feels a dictionary with all the propriety that needs to
be used after this sequence of steps.

author: Vincenzo PAlazzo https://github.com/vincenzopalazzo
"""
from typing import List, Optional


class LightningUtils:
    """
    Main implementation class of the lightning networks utils.

    The implementation class contains only static methods that
    apply the rules specified in the lightning network RFC.
    """

    @staticmethod
    def derive_short_channel_id(block_height: int, tx_idx: int, tx_output) -> str:
        """
        Derive the short channel id with the specified
        parameters, and return the result as string.

        RFC definition: https://github.com/lightning/bolts/blob/93909f67f6a48ee3f155a6224c182e612dd5f187/07-routing-gossip.md#definition-of-short_channel_id

        The short_channel_id is the unique description of the funding transaction. It is constructed as follows:
            - the most significant 3 bytes: indicating the block height
            - the next 3 bytes: indicating the transaction index within the block
            - the least significant 2 bytes: indicating the output index that pays to the channel.

        e.g: a short_channel_id might be written as 539268x845x1, indicating a channel on the
        output 1 of the transaction at index 845 of the block at height 539268.

        block_height: str
            Block height.
        tx_idx: int
            Transaction index inside the block.
        tx_output: int
            Output index inside the transaction.
        """
        return f"{block_height}x{tx_idx}x{tx_output}"


def connect_to_node_helper(
    runner: "Runner",
    tx_spendable: str,
    conn_privkey: str = "02",
    global_features: Optional[List[int]] = None,
    features: Optional[List[int]] = None,
) -> List["Event"]:
    """Helper function to make a connection with the node"""
    from lnprototest.utils.bitcoin_utils import tx_spendable
    from lnprototest import (
        Connect,
        Block,
        ExpectMsg,
        Msg,
    )

    return [
        Block(blockheight=102, txs=[tx_spendable]),
        Connect(connprivkey=conn_privkey),
        ExpectMsg("init"),
        Msg(
            "init",
            globalfeatures=runner.runner_features(globals=True)
            if global_features is None
            else (
                runner.runner_features(
                    global_features,
                    globals=True,
                )
            ),
            features=runner.runner_features()
            if features is None
            else (runner.runner_features(features)),
        ),
    ]


def open_and_announce_channel_helper(
    runner: "Runner", conn_privkey: str = "02", opts: dict = {}
) -> List["Event"]:
    from lnprototest.utils import gen_random_keyset, pubkey_of
    from lnprototest.utils.bitcoin_utils import (
        BitcoinUtils,
        utxo,
        funding_amount_for_utxo,
    )
    from lnprototest.utils.ln_spec_utils import LightningUtils
    from lnprototest import (
        Block,
        ExpectMsg,
        Msg,
        Commit,
        Side,
        CreateFunding,
        remote_funding_pubkey,
        remote_revocation_basepoint,
        remote_payment_basepoint,
        remote_delayed_payment_basepoint,
        remote_htlc_basepoint,
        remote_per_commitment_point,
        remote_funding_privkey,
        msat,
    )
    from lnprototest.stash import (
        rcvd,
        funding,
        sent,
        commitsig_to_recv,
        channel_id,
        commitsig_to_send,
        funding_txid,
        funding_tx,
        stash_field_from_event,
    )

    # Make up a channel between nodes 02 and 03, using bitcoin privkeys 10 and 20
    local_keyset = gen_random_keyset()
    local_funding_privkey = "20"
    if "block_height" in opts:
        block_height = opts["block_height"]
    else:
        block_height = 103

    short_channel_id = LightningUtils.derive_short_channel_id(block_height, 1, 0)
    opts["short_channel_id"] = short_channel_id
    opts["block_height"] = block_height + 6
    return [
        Msg(
            "open_channel",
            chain_hash=BitcoinUtils.blockchain_hash(),
            temporary_channel_id="00" * 32,
            funding_satoshis=funding_amount_for_utxo(0),
            push_msat=0,
            dust_limit_satoshis=546,
            max_htlc_value_in_flight_msat=4294967295,
            channel_reserve_satoshis=9998,
            htlc_minimum_msat=0,
            feerate_per_kw=253,
            # clightning uses to_self_delay=6; we use 5 to test differentiation
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
        ExpectMsg(
            "accept_channel",
            funding_pubkey=remote_funding_pubkey(),
            revocation_basepoint=remote_revocation_basepoint(),
            payment_basepoint=remote_payment_basepoint(),
            delayed_payment_basepoint=remote_delayed_payment_basepoint(),
            htlc_basepoint=remote_htlc_basepoint(),
            first_per_commitment_point=remote_per_commitment_point(0),
            minimum_depth=stash_field_from_event("accept_channel", dummy_val=3),
            channel_reserve_satoshis=9998,
        ),
        # Create and stash Funding object and FundingTx
        CreateFunding(
            *utxo(0),
            local_node_privkey="02",
            local_funding_privkey=local_funding_privkey,
            remote_node_privkey=runner.get_node_privkey(),
            remote_funding_privkey=remote_funding_privkey(),
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
            "funding_signed", channel_id=channel_id(), signature=commitsig_to_recv()
        ),
        # Mine it and get it deep enough to confirm channel.
        Block(
            blockheight=103,
            number=stash_field_from_event(
                "accept_channel", field_name="minimum_depth", dummy_val=3
            ),
            txs=[funding_tx()],
        ),
        ExpectMsg(
            "channel_ready",
            channel_id=channel_id(),
            second_per_commitment_point=remote_per_commitment_point(1),
        ),
        Msg(
            "channel_ready",
            channel_id=channel_id(),
            second_per_commitment_point=local_keyset.per_commit_point(1),
        ),
        # wait confirmations
        Block(blockheight=103, number=6),
        # BOLT 2:
        #
        # Once both nodes have exchanged channel_ready (and optionally announcement_signatures),
        # the channel can be used to make payments via Hashed Time Locked Contracts.
    ]
