# Support for funding txs.
from typing import Tuple, Any, Optional
from .utils import Side, privkey_expand, regtest_hash
from .event import Event, ResolvableInt, ResolvableStr
from .namespace import event_namespace
from .runner import Runner
from .signature import Sig
from pyln.proto.message import Message
from hashlib import sha256
import coincurve
import io
from bitcoin.core import COutPoint, CScript, CTxIn, CTxOut, CMutableTransaction, CTxWitness, CTxInWitness, CScriptWitness, Hash160
import bitcoin.core.script as script
from bitcoin.wallet import P2WPKHBitcoinAddress


class Funding(object):
    def __init__(self,
                 funding_txid: str,
                 funding_output_index: int,
                 funding_amount: int,
                 local_node_privkey: str,
                 local_funding_privkey: str,
                 remote_node_privkey: str,
                 remote_funding_privkey: str,
                 chain_hash: str = regtest_hash):
        self.chain_hash = chain_hash
        self.txid = funding_txid
        self.output_index = funding_output_index
        self.amount = funding_amount
        self.bitcoin_privkeys = [privkey_expand(local_funding_privkey),
                                 privkey_expand(remote_funding_privkey)]
        self.node_privkeys = [privkey_expand(local_node_privkey),
                              privkey_expand(remote_node_privkey)]

    def node_id_sort(self, local: Any, remote: Any) -> Tuple[Any, Any]:
        """Sorts these two items into lexicographical node id order"""
        # BOLT #7:
        # - MUST set `node_id_1` and `node_id_2` to the public keys of the two
        #   nodes operating the channel, such that `node_id_1` is the
        #   lexicographically-lesser of the two compressed keys sorted in
        #   ascending lexicographic order.
        if self.node_id(Side.local).format() < self.node_id(Side.remote).format():
            return local, remote
        else:
            return remote, local

    def bitcoin_key_sort(self, local: Any, remote: Any) -> Tuple[Any, Any]:
        """Sorts these two items into lexicographical bitcoin key order"""
        # BOLT #3:
        # ## Funding Transaction Output
        #
        # * The funding output script is a P2WSH to: `2 <pubkey1> <pubkey2> 2
        #  OP_CHECKMULTISIG`
        # * Where `pubkey1` is the lexicographically lesser of the two
        #   `funding_pubkey` in compressed format, and where `pubkey2` is the
        #   lexicographically greater of the two.
        if self.funding_pubkey(Side.local).format() < self.funding_pubkey(Side.remote).format():
            return local, remote
        else:
            return remote, local

    def redeemscript(self) -> CScript:
        return CScript([script.OP_2]
                       + [k.format() for k in self.funding_pubkeys_for_tx()]
                       + [script.OP_2,
                          script.OP_CHECKMULTISIG])

    @staticmethod
    def from_utxo(txid_in: str,
                  tx_index_in: int,
                  sats: int,
                  privkey: str,
                  fee: int,
                  local_node_privkey: str,
                  local_funding_privkey: str,
                  remote_node_privkey: str,
                  remote_funding_privkey: str,
                  chain_hash: str = regtest_hash) -> Tuple['Funding', str]:
        """Make a funding transaction by spending this utxo using privkey: return Funding, tx."""

        # Create dummy one to start: we will fill in txid at the end.
        funding = Funding('', 0, sats - fee,
                          local_node_privkey,
                          local_funding_privkey,
                          remote_node_privkey,
                          remote_funding_privkey,
                          chain_hash)

        # input private key.
        inkey = privkey_expand(privkey)
        inkey_pub = coincurve.PublicKey.from_secret(inkey.secret)

        txin = CTxIn(COutPoint(bytes.fromhex(txid_in), tx_index_in))
        txout = CTxOut(sats - fee, CScript([script.OP_0, sha256(funding.redeemscript()).digest()]))
        tx = CMutableTransaction([txin], [txout])

        # now fill in funding txid.
        funding.txid = tx.GetTxid().hex()

        # while we're here, sign the transaction.
        address = P2WPKHBitcoinAddress.from_scriptPubKey(CScript([script.OP_0, Hash160(inkey_pub.format())]))

        sighash = script.SignatureHash(address.to_redeemScript(),
                                       tx, 0, script.SIGHASH_ALL, amount=sats,
                                       sigversion=script.SIGVERSION_WITNESS_V0)
        sig = inkey.sign(sighash, hasher=None) + bytes([script.SIGHASH_ALL])

        tx.wit = CTxWitness([CTxInWitness(CScriptWitness([sig, inkey_pub.format()]))])
        return funding, tx.serialize().hex()

    def channel_id(self) -> str:
        # BOLT #2: This message introduces the `channel_id` to identify the
        # channel. It's derived from the funding transaction by combining the
        # `funding_txid` and the `funding_output_index`, using big-endian
        # exclusive-OR (i.e. `funding_output_index` alters the last 2 bytes).
        chanid = bytearray.fromhex(self.txid)
        chanid[-1] ^= self.output_index % 256
        chanid[-2] ^= self.output_index // 256
        return chanid.hex()

    def funding_pubkey(self, side: Side) -> coincurve.PublicKey:
        return coincurve.PublicKey.from_secret(self.bitcoin_privkeys[side].secret)

    def funding_pubkeys_for_tx(self) -> Tuple[coincurve.PublicKey, coincurve.PublicKey]:
        """Returns funding pubkeys, in tx order"""
        # BOLT #3:
        # ## Funding Transaction Output
        #
        # * The funding output script is a P2WSH to: `2 <pubkey1> <pubkey2> 2
        #  OP_CHECKMULTISIG`
        # * Where `pubkey1` is the lexicographically lesser of the two
        #   `funding_pubkey` in compressed format, and where `pubkey2` is the
        #   lexicographically greater of the two.
        return self.bitcoin_key_sort(self.funding_pubkey(Side.local),
                                     self.funding_pubkey(Side.remote))

    def funding_privkeys_for_tx(self) -> Tuple[coincurve.PrivateKey, coincurve.PrivateKey]:
        """Returns funding private keys, in tx order"""
        return self.bitcoin_key_sort(self.bitcoin_privkeys[Side.local],
                                     self.bitcoin_privkeys[Side.remote])

    def node_id(self, side: Side) -> coincurve.PublicKey:
        return coincurve.PublicKey.from_secret(self.node_privkeys[side].secret)

    def node_ids(self) -> Tuple[coincurve.PublicKey, coincurve.PublicKey]:
        """Returns node pubkeys, in order"""
        return self.node_id_sort(self.node_id(Side.local),
                                 self.node_id(Side.remote))

    def node_id_privkeys(self) -> Tuple[coincurve.PrivateKey, coincurve.PrivateKey]:
        """Returns node private keys, in order"""
        return self.node_id_sort(self.node_privkeys[Side.local],
                                 self.node_privkeys[Side.remote])

    def funding_pubkeys_for_gossip(self) -> Tuple[coincurve.PublicKey, coincurve.PublicKey]:
        """Returns funding public keys, in gossip order"""
        return self.node_id_sort(self.funding_pubkey(Side.local),
                                 self.funding_pubkey(Side.remote))

    def funding_privkeys_for_gossip(self) -> Tuple[coincurve.PublicKey, coincurve.PublicKey]:
        """Returns funding private keys, in gossip order"""
        return self.node_id_sort(self.bitcoin_privkeys[Side.local],
                                 self.bitcoin_privkeys[Side.remote])

    def _unsigned_channel_announcment(self,
                                      features: str,
                                      short_channel_id: str) -> Message:
        """Produce a channel_announcement message with dummy sigs"""
        node_ids = self.node_ids()
        bitcoin_keys = self.funding_pubkeys_for_gossip()
        return Message(event_namespace.get_msgtype('channel_announcement'),
                       node_signature_1=Sig(bytes(64)),
                       node_signature_2=Sig(bytes(64)),
                       bitcoin_signature_1=Sig(bytes(64)),
                       bitcoin_signature_2=Sig(bytes(64)),
                       features=features,
                       chain_hash=self.chain_hash,
                       short_channel_id=short_channel_id,
                       node_id_1=node_ids[0].format(),
                       node_id_2=node_ids[1].format(),
                       bitcoin_key_1=bitcoin_keys[0].format(),
                       bitcoin_key_2=bitcoin_keys[1].format())

    def channel_announcement(self,
                             short_channel_id: str,
                             features: str) -> Message:
        """Produce a (signed) channel_announcement message"""
        ann = self._unsigned_channel_announcment(features, short_channel_id)
        # BOLT #7:
        # - MUST compute the double-SHA256 hash `h` of the message, beginning
        #   at offset 256, up to the end of the message.
        #   - Note: the hash skips the 4 signatures but hashes the rest of the
        #     message, including any future fields appended to the end.
        buf = io.BytesIO()
        ann.write(buf)
        # Note the first two 'type' bytes!
        h = sha256(sha256(buf.getvalue()[2 + 256:]).digest()).digest()

        # BOLT #7:
        # - MUST set `node_signature_1` and `node_signature_2` to valid
        #   signatures of the hash `h` (using `node_id_1` and `node_id_2`'s
        #   respective secrets).
        node_privkeys = self.node_id_privkeys()
        ann.set_field('node_signature_1', Sig(node_privkeys[0].secret.hex(), h.hex()))
        ann.set_field('node_signature_2', Sig(node_privkeys[1].secret.hex(), h.hex()))

        bitcoin_privkeys = self.funding_privkeys_for_gossip()
        # - MUST set `bitcoin_signature_1` and `bitcoin_signature_2` to valid
        #   signatures of the hash `h` (using `bitcoin_key_1` and
        #   `bitcoin_key_2`'s respective secrets).
        ann.set_field('bitcoin_signature_1', Sig(bitcoin_privkeys[0].secret.hex(), h.hex()))
        ann.set_field('bitcoin_signature_2', Sig(bitcoin_privkeys[1].secret.hex(), h.hex()))

        return ann

    def channel_update(self,
                       short_channel_id: str,
                       side: Side,
                       disable: bool,
                       cltv_expiry_delta: int,
                       htlc_minimum_msat: int,
                       fee_base_msat: int,
                       fee_proportional_millionths: int,
                       timestamp: int,
                       htlc_maximum_msat: Optional[int]) -> Message:
        # BOLT #7: The `channel_flags` bitfield is used to indicate the
        # direction of the channel: it identifies the node that this update
        # originated from and signals various options concerning the
        # channel. The following table specifies the meaning of its individual
        # bits:
        #
        # | Bit Position  | Name        | Meaning                          |
        # | ------------- | ----------- | -------------------------------- |
        # | 0             | `direction` | Direction this update refers to. |
        # | 1             | `disable`   | Disable the channel.             |

        # BOLT #7:
        #   - if the origin node is `node_id_1` in the message:
        #     - MUST set the `direction` bit of `channel_flags` to 0.
        #   - otherwise:
        #     - MUST set the `direction` bit of `channel_flags` to 1.
        if self.funding_pubkey(side) == self.funding_pubkeys_for_gossip()[0]:
            channel_flags = 0
        else:
            channel_flags = 1

        if disable:
            channel_flags |= 2

        # BOLT #7: The `message_flags` bitfield is used to indicate the
        # presence of optional fields in the `channel_update` message:
        #
        # | Bit Position  | Name                      | Field                            |
        # | ------------- | ------------------------- | -------------------------------- |
        # | 0             | `option_channel_htlc_max` | `htlc_maximum_msat`              |
        message_flags = 0
        if htlc_maximum_msat:
            message_flags |= 1

        # Begin with a fake signature.
        update = Message(event_namespace.get_msgtype('channel_update'),
                         short_channel_id=short_channel_id,
                         signature=Sig(bytes(64)),
                         chain_hash=self.chain_hash,
                         timestamp=timestamp,
                         message_flags=message_flags,
                         channel_flags=channel_flags,
                         cltv_expiry_delta=cltv_expiry_delta,
                         htlc_minimum_msat=htlc_minimum_msat,
                         fee_base_msat=fee_base_msat,
                         fee_proportional_millionths=fee_proportional_millionths)
        if htlc_maximum_msat:
            update.set_field('htlc_maximum_msat', htlc_maximum_msat)

        # BOLT #7:
        # - MUST set `signature` to the signature of the double-SHA256 of the
        #   entire remaining packet after `signature`, using its own `node_id`.
        buf = io.BytesIO()
        update.write(buf)
        # Note the first two 'type' bytes!
        h = sha256(sha256(buf.getvalue()[2 + 64:]).digest()).digest()

        update.set_field('signature', Sig(self.node_privkeys[side].secret.hex(), h.hex()))

        return update

    def node_announcement(self,
                          side: Side,
                          features: str,
                          rgb_color: Tuple[int, int, int],
                          alias: str,
                          addresses: bytes,
                          timestamp: int) -> Message:
        # Begin with a fake signature.
        ann = Message(event_namespace.get_msgtype('node_announcement'),
                      signature=Sig(bytes(64)),
                      features=features,
                      timestamp=timestamp,
                      node_id=self.node_id(side).format().hex(),
                      rgb_color=bytes(rgb_color).hex(),
                      alias=bytes(alias, encoding='utf-8').zfill(32),
                      addresses=addresses)

        # BOLT #7:
        #  - MUST set `signature` to the signature of the double-SHA256 of the entire
        #  remaining packet after `signature` (using the key given by `node_id`).
        buf = io.BytesIO()
        ann.write(buf)
        # Note the first two 'type' bytes!
        h = sha256(sha256(buf.getvalue()[2 + 64:]).digest()).digest()

        ann.set_field('signature', Sig(self.node_privkeys[side].secret.hex(), h.hex()))
        return ann

    def close_tx(self, fee: int, privkey_dest: str) -> str:
        """Create a (mutual) close tx"""
        txin = CTxIn(COutPoint(bytes.fromhex(self.txid), self.output_index))

        out_privkey = privkey_expand(privkey_dest)

        txout = CTxOut(self.amount - fee,
                       CScript([script.OP_0,
                                Hash160(coincurve.PublicKey.from_secret(out_privkey.secret).format())]))

        tx = CMutableTransaction(vin=[txin], vout=[txout])
        sighash = script.SignatureHash(self.redeemscript(), tx, inIdx=0,
                                       hashtype=script.SIGHASH_ALL,
                                       amount=self.amount,
                                       sigversion=script.SIGVERSION_WITNESS_V0)

        sigs = [key.sign(sighash, hasher=None) for key in self.funding_privkeys_for_tx()]
        # BOLT #3:
        # ## Closing Transaction
        # ...
        #    * `txin[0]` witness: `0 <signature_for_pubkey1> <signature_for_pubkey2>`
        witness = CScriptWitness([bytes(),
                                  sigs[0] + bytes([script.SIGHASH_ALL]),
                                  sigs[1] + bytes([script.SIGHASH_ALL]),
                                  self.redeemscript()])
        tx.wit = CTxWitness([CTxInWitness(witness)])
        return tx.serialize().hex()


class AcceptFunding(Event):
    """Event to accept funding information from a peer.  Stashes 'Funding'."""
    def __init__(self,
                 funding_txid: ResolvableStr,
                 funding_output_index: ResolvableInt,
                 funding_amount: ResolvableInt,
                 local_node_privkey: ResolvableStr,
                 local_funding_privkey: ResolvableStr,
                 remote_node_privkey: ResolvableStr,
                 remote_funding_privkey: ResolvableStr,
                 chain_hash: str = regtest_hash):
        super().__init__()
        self.funding_txid = funding_txid
        self.funding_output_index = funding_output_index
        self.funding_amount = funding_amount
        self.local_node_privkey = local_node_privkey
        self.local_funding_privkey = local_funding_privkey
        self.remote_node_privkey = remote_node_privkey
        self.remote_funding_privkey = remote_funding_privkey
        self.chain_hash = chain_hash

    def action(self, runner: Runner) -> bool:
        super().action(runner)

        funding = Funding(chain_hash=self.chain_hash,
                          **self.resolve_args(runner,
                                              {'funding_txid': self.funding_txid,
                                               'funding_output_index': self.funding_output_index,
                                               'funding_amount': self.funding_amount,
                                               'local_node_privkey': self.local_node_privkey,
                                               'local_funding_privkey': self.local_funding_privkey,
                                               'remote_node_privkey': self.remote_node_privkey,
                                               'remote_funding_privkey': self.remote_funding_privkey}))
        runner.add_stash('Funding', funding)
        return True


class CreateFunding(Event):
    """Event to create a funding tx from a P2WPKH UTXO.  Stashes 'Funding' and 'FundingTx'."""
    def __init__(self,
                 txid_in: str,
                 tx_index_in: int,
                 sats_in: int,
                 spending_privkey: str,
                 fee: int,
                 local_node_privkey: ResolvableStr,
                 local_funding_privkey: ResolvableStr,
                 remote_node_privkey: ResolvableStr,
                 remote_funding_privkey: ResolvableStr,
                 chain_hash: str = regtest_hash):
        super().__init__()
        self.txid_in = txid_in
        self.tx_index_in = tx_index_in
        self.sats_in = sats_in
        self.spending_privkey = spending_privkey
        self.fee = fee
        self.local_node_privkey = local_node_privkey
        self.local_funding_privkey = local_funding_privkey
        self.remote_node_privkey = remote_node_privkey
        self.remote_funding_privkey = remote_funding_privkey
        self.chain_hash = chain_hash

    def action(self, runner: Runner) -> bool:
        super().action(runner)

        funding, tx = Funding.from_utxo(self.txid_in,
                                        self.tx_index_in,
                                        self.sats_in,
                                        self.spending_privkey,
                                        self.fee,
                                        chain_hash=self.chain_hash,
                                        **self.resolve_args(runner,
                                                            {'local_node_privkey': self.local_node_privkey,
                                                             'local_funding_privkey': self.local_funding_privkey,
                                                             'remote_node_privkey': self.remote_node_privkey,
                                                             'remote_funding_privkey': self.remote_funding_privkey}))

        runner.add_stash('Funding', funding)
        runner.add_stash('FundingTx', tx)
        return True
