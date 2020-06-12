#! /usr/bin/python3
# Variations on open_channel, accepter + opener perspectives

from lnprototest import TryAll, Connect, Block, FundChannel, ExpectMsg, ExpectTx, Msg, RawMsg, KeySet, Funding, Commit, remote_funding_pubkey, remote_revocation_basepoint, remote_payment_basepoint, remote_htlc_basepoint, remote_per_commitment_point, remote_delayed_payment_basepoint, sent, rcvd, LOCAL, REMOTE, commitsig_to_send, commitsig_to_recv, CheckEq, msat, channel_id, remote_funding_privkey
from fixtures import *  # noqa: F401,F403
from blocks import BLOCK_102


def test_open_channel(runner):
    # regtest chain hash
    chain_hash = '06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f'

    # Funding tx is 020000000001016b85f654d8186f4d5dd32a977b2cf8c4b01ff4634152acba16b654c1c85a83160100000000ffffffff01c6410f0000000000220020c46bf3d1686d6dbb2d9244f8f67b90370c5aa2747045f1aeccb77d818711738202473044022047e9e6e798ba9adb6c84bdcd6230a96fb6de9dcca84d81103fb2bc08906cb884022027599b1e80289eaf238e9a00119a79a0ccceab7d83d54719e10bd0c3300a0d34012102d6a3c2d0cf7904ab6af54d7c959435a452b24a63194e1c4e7c337d3ebbb3017b00000000
    funding = Funding(funding_txid='2f0b21d6bd32971ca6803de2bdc7370bbf12e0cd9ce73afc1c591f5c995b0841',
                      funding_output_index=0,
                      funding_amount=999878,
                      local_node_privkey='02',
                      local_funding_privkey='20',
                      remote_node_privkey=runner.get_node_privkey(),
                      remote_funding_privkey=remote_funding_privkey())

    local_keyset = KeySet(revocation_base_secret='21',
                          payment_base_secret='22',
                          htlc_base_secret='24',
                          delayed_payment_base_secret='23',
                          shachain_seed='00' * 32)

    test = [BLOCK_102,
            Connect(connprivkey='02'),
            ExpectMsg('init'),
            Msg('init', globalfeatures='', features=''),

            TryAll([
                # Accepter side: we initiate a new channel.
                [Msg('open_channel',
                     chain_hash=chain_hash,
                     temporary_channel_id='0000000000000000000000000000000000000000000000000000000000000000',
                     funding_satoshis=funding.amount,
                     push_msat=0,
                     dust_limit_satoshis=546,
                     max_htlc_value_in_flight_msat=4294967295,
                     channel_reserve_satoshis=9998,
                     htlc_minimum_msat=0,
                     feerate_per_kw=253,
                     to_self_delay=6,
                     max_accepted_htlcs=483,
                     funding_pubkey=funding.funding_pubkey(LOCAL).format().hex(),
                     revocation_basepoint=local_keyset.revocation_basepoint().format().hex(),
                     payment_basepoint=local_keyset.payment_basepoint().format().hex(),
                     delayed_payment_basepoint=local_keyset.delayed_payment_basepoint().format().hex(),
                     htlc_basepoint=local_keyset.htlc_basepoint().format().hex(),
                     first_per_commitment_point=local_keyset.per_commit_point(0).format().hex(),
                     channel_flags=1),

                 # Ignore unknown odd messages
                 TryAll([[], RawMsg(bytes.fromhex('270F'))]),

                 ExpectMsg('accept_channel',
                           temporary_channel_id='00' * 32,
                           funding_pubkey=remote_funding_pubkey(),
                           revocation_basepoint=remote_revocation_basepoint(),
                           payment_basepoint=remote_payment_basepoint(),
                           delayed_payment_basepoint=remote_delayed_payment_basepoint(),
                           htlc_basepoint=remote_htlc_basepoint(),
                           first_per_commitment_point=remote_per_commitment_point(0),
                           minimum_depth=3,
                           # If this is different, the commitment tx will be different!
                           to_self_delay=6,
                           channel_reserve_satoshis=9998),

                 # Ignore unknown odd messages
                 TryAll([[], RawMsg(bytes.fromhex('270F'))]),

                 # FIXME: Implement funding tx in python!
                 # Funding tx is 020000000001016b85f654d8186f4d5dd32a977b2cf8c4b01ff4634152acba16b654c1c85a83160100000000ffffffff01c6410f0000000000220020c46bf3d1686d6dbb2d9244f8f67b90370c5aa2747045f1aeccb77d818711738202473044022047e9e6e798ba9adb6c84bdcd6230a96fb6de9dcca84d81103fb2bc08906cb884022027599b1e80289eaf238e9a00119a79a0ccceab7d83d54719e10bd0c3300a0d34012102d6a3c2d0cf7904ab6af54d7c959435a452b24a63194e1c4e7c337d3ebbb3017b00000000
                 # txid=41085b995c1f591cfc3ae79ccde012bf0b37c7bde23d80a61c9732bdd6210b2f
                 Commit(funding,
                        opener=LOCAL,
                        local_keyset=local_keyset,
                        local_to_self_delay=sent('to_self_delay', int),
                        remote_to_self_delay=rcvd('to_self_delay', int),
                        local_amount=msat(sent('funding_satoshis', int)),
                        remote_amount=0,
                        local_dust_limit=546,
                        remote_dust_limit=546,
                        feerate=253,
                        option_static_remotekey=False),

                 Msg('funding_created',
                     temporary_channel_id=rcvd(),
                     # FIXME: Implement funding tx in python!
                     # Funding tx is 020000000001016b85f654d8186f4d5dd32a977b2cf8c4b01ff4634152acba16b654c1c85a83160100000000ffffffff01c6410f0000000000220020c46bf3d1686d6dbb2d9244f8f67b90370c5aa2747045f1aeccb77d818711738202473044022047e9e6e798ba9adb6c84bdcd6230a96fb6de9dcca84d81103fb2bc08906cb884022027599b1e80289eaf238e9a00119a79a0ccceab7d83d54719e10bd0c3300a0d34012102d6a3c2d0cf7904ab6af54d7c959435a452b24a63194e1c4e7c337d3ebbb3017b00000000
                     # txid=41085b995c1f591cfc3ae79ccde012bf0b37c7bde23d80a61c9732bdd6210b2f
                     funding_txid='2f0b21d6bd32971ca6803de2bdc7370bbf12e0cd9ce73afc1c591f5c995b0841',
                     funding_output_index=0,
                     signature=commitsig_to_send()),

                 ExpectMsg('funding_signed',
                           channel_id=channel_id(),
                           # test's commitment tx is 02000000012f0b21d6bd32971ca6803de2bdc7370bbf12e0cd9ce73afc1c591f5c995b08410000000000f436a980010f410f0000000000220020233d69d88092351875ce0b9fd5ea576b2307c539eaed7abdf97fbb26720f01ac4cff0020
                           signature=commitsig_to_recv()),

                 # Mine it and get it deep enough to confirm channel.
                 Block(blockheight=103, number=3, txs=['020000000001016b85f654d8186f4d5dd32a977b2cf8c4b01ff4634152acba16b654c1c85a83160100000000ffffffff01c6410f0000000000220020c46bf3d1686d6dbb2d9244f8f67b90370c5aa2747045f1aeccb77d818711738202473044022047e9e6e798ba9adb6c84bdcd6230a96fb6de9dcca84d81103fb2bc08906cb884022027599b1e80289eaf238e9a00119a79a0ccceab7d83d54719e10bd0c3300a0d34012102d6a3c2d0cf7904ab6af54d7c959435a452b24a63194e1c4e7c337d3ebbb3017b00000000']),

                 ExpectMsg('funding_locked',
                           channel_id=channel_id(),
                           next_per_commitment_point='032405cbd0f41225d5f203fe4adac8401321a9e05767c5f8af97d51d2e81fbb206'),

                 Msg('funding_locked',
                     channel_id=channel_id(),
                     next_per_commitment_point='027eed8389cf8eb715d73111b73d94d2c2d04bf96dc43dfd5b0970d80b3617009d'),

                 # Ignore unknown odd messages
                 TryAll([[], RawMsg(bytes.fromhex('270F'))])],

                # Now we test the 'opener' side of an open_channel (node initiates)
                [FundChannel(amount=999877),

                 # This gives a channel of 999877sat
                 ExpectMsg('open_channel',
                           chain_hash=chain_hash,
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
                           channel_flags='01'),

                 Msg('accept_channel',
                     temporary_channel_id=rcvd(),
                     dust_limit_satoshis=546,
                     max_htlc_value_in_flight_msat=4294967295,
                     channel_reserve_satoshis=9998,
                     htlc_minimum_msat=0,
                     minimum_depth=3,
                     max_accepted_htlcs=483,
                     # If these are different, the commitment tx will be different!
                     to_self_delay=6,
                     funding_pubkey=funding.funding_pubkey(LOCAL).format().hex(),
                     revocation_basepoint=local_keyset.revocation_basepoint().format().hex(),
                     payment_basepoint=local_keyset.payment_basepoint().format().hex(),
                     delayed_payment_basepoint=local_keyset.delayed_payment_basepoint().format().hex(),
                     htlc_basepoint=local_keyset.htlc_basepoint().format().hex(),
                     first_per_commitment_point=local_keyset.per_commit_point(0).format().hex()),

                 # Ignore unknown odd messages
                 TryAll([[], RawMsg(bytes.fromhex('270F'))]),

                 ExpectMsg('funding_created',
                           temporary_channel_id=rcvd('temporary_channel_id')),

                 Commit(funding=Funding(funding_txid=rcvd(),
                                        funding_output_index=rcvd(casttype=int),
                                        funding_amount=rcvd('open_channel.funding_satoshis', int),
                                        local_node_privkey='02',
                                        local_funding_privkey='20',
                                        remote_node_privkey=runner.get_node_privkey(),
                                        remote_funding_privkey=remote_funding_privkey()),
                        opener=REMOTE,
                        local_keyset=local_keyset,
                        local_to_self_delay=sent('to_self_delay', int),
                        remote_to_self_delay=rcvd('open_channel.to_self_delay', int),
                        local_amount=0,
                        remote_amount=msat(rcvd('open_channel.funding_satoshis', int)),
                        local_dust_limit=sent('accept_channel.dust_limit_satoshis', int),
                        remote_dust_limit=rcvd('open_channel.dust_limit_satoshis', int),
                        feerate=rcvd('open_channel.feerate_per_kw', int),
                        option_static_remotekey=False),

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
                     next_per_commitment_point=local_keyset.per_commit_point(1).format().hex()),

                 ExpectMsg('funding_locked',
                           channel_id=sent(),
                           next_per_commitment_point=remote_per_commitment_point(1)),

                 # Ignore unknown odd messages
                 TryAll([[], RawMsg(bytes.fromhex('270F'))]),
                 ]])]

    runner.run(test)
