# Support for funding txs.
from typing import Tuple, Union, Any, Dict, Optional
from .utils import Side, LOCAL, REMOTE, privkey_expand
from .event import Event, ResolvableInt, ResolvableStr, Resolvable
from .namespace import event_namespace
from .runner import Runner
from .signature import Sig
from pyln.proto.message import Message
from hashlib import sha256
import coincurve
import io


def keyorder(key1: Union[coincurve.PublicKey, coincurve.PrivateKey], val1: Any,
             key2: Union[coincurve.PublicKey, coincurve.PrivateKey], val2: Any) -> Tuple[Any, Any]:
    """Sorts these two items into lexicographical order, as widely used in BOLTs"""
    if isinstance(key1, coincurve.PrivateKey):
        pubkey1 = coincurve.PublicKey.from_secret(key1.secret)
    else:
        assert isinstance(key1, coincurve.PublicKey)
        pubkey1 = key1

    if isinstance(key2, coincurve.PrivateKey):
        pubkey2 = coincurve.PublicKey.from_secret(key2.secret)
    else:
        assert isinstance(key2, coincurve.PublicKey)
        pubkey2 = key2

    if pubkey1.format() < pubkey2.format():
        return val1, val2
    return val2, val1


class Funding(object):
    def __init__(self,
                 funding_txid: ResolvableStr,
                 funding_output_index: ResolvableInt,
                 funding_amount: ResolvableInt,
                 local_node_privkey: ResolvableStr,
                 local_funding_privkey: ResolvableStr,
                 remote_node_privkey: ResolvableStr,
                 remote_funding_privkey: ResolvableStr,
                 # default is regtest, of course.
                 chain_hash: str = '06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f'):
        self.chain_hash = chain_hash
        self.unresolved: Dict[str, Resolvable] = {}

        # These may need resolve_args.
        self.bitcoin_privkeys = [privkey_expand('ff'), privkey_expand('ff')]
        self.node_privkeys = [privkey_expand('ff'), privkey_expand('ff')]

        if callable(funding_txid):
            self.unresolved['funding_txid'] = funding_txid
        else:
            assert isinstance(funding_txid, str)
            self.txid = funding_txid

        if callable(funding_output_index):
            self.unresolved['funding_output_index'] = funding_output_index
        else:
            assert isinstance(funding_output_index, int)
            self.output_index = funding_output_index

        if callable(funding_amount):
            self.unresolved['funding_amount'] = funding_amount
        else:
            assert isinstance(funding_amount, int)
            self.amount = funding_amount

        if callable(local_node_privkey):
            self.unresolved['local_node_privkey'] = local_node_privkey
        else:
            assert isinstance(local_node_privkey, str)
            self.node_privkeys[LOCAL] = privkey_expand(local_node_privkey)

        if callable(remote_node_privkey):
            self.unresolved['remote_node_privkey'] = remote_node_privkey
        else:
            assert isinstance(remote_node_privkey, str)
            self.node_privkeys[REMOTE] = privkey_expand(remote_node_privkey)

        if callable(local_funding_privkey):
            self.unresolved['local_funding_privkey'] = local_funding_privkey
        else:
            assert isinstance(local_funding_privkey, str)
            self.bitcoin_privkeys[LOCAL] = privkey_expand(local_funding_privkey)

        if callable(remote_funding_privkey):
            self.unresolved['remote_funding_privkey'] = remote_funding_privkey
        else:
            assert isinstance(remote_funding_privkey, str)
            self.bitcoin_privkeys[REMOTE] = privkey_expand(remote_funding_privkey)

    def resolve_args(self, event: Event, runner: Runner) -> None:
        """Called at runtime when Funding is used in a Commit event"""
        for k, v in event.resolve_args(runner, self.unresolved).items():
            if k == 'funding_txid':
                self.txid = v
            elif k == 'funding_output_index':
                self.output_index = int(v)
            elif k == 'funding_amount':
                self.amount = int(v)
            elif k == 'local_node_privkey':
                self.node_privkeys[LOCAL] = privkey_expand(v)
            elif k == 'remote_node_privkey':
                self.node_privkeys[REMOTE] = privkey_expand(v)
            elif k == 'local_funding_privkey':
                self.bitcoin_privkeys[LOCAL] = privkey_expand(v)
            elif k == 'remote_funding_privkey':
                self.bitcoin_privkeys[REMOTE] = privkey_expand(v)
            else:
                raise RuntimeError('Unexpected arg {}'.format(k))

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
        return keyorder(self.bitcoin_privkeys[LOCAL], self.funding_pubkey(LOCAL),
                        self.bitcoin_privkeys[REMOTE], self.funding_pubkey(REMOTE))

    def funding_privkeys_for_tx(self) -> Tuple[coincurve.PrivateKey, coincurve.PrivateKey]:
        """Returns funding private keys, in tx order"""
        return keyorder(self.bitcoin_privkeys[LOCAL], self.bitcoin_privkeys[LOCAL],
                        self.bitcoin_privkeys[REMOTE], self.bitcoin_privkeys[REMOTE])

    def node_id(self, side: Side) -> coincurve.PublicKey:
        return coincurve.PublicKey.from_secret(self.node_privkeys[side].secret)

    def node_ids(self) -> Tuple[coincurve.PublicKey, coincurve.PublicKey]:
        """Returns node pubkeys, in order"""
        # BOLT #7:
        # - MUST set `node_id_1` and `node_id_2` to the public keys of the two
        #   nodes operating the channel, such that `node_id_1` is the
        #   lexicographically-lesser of the two compressed keys sorted in
        #   ascending lexicographic order.
        return keyorder(self.node_privkeys[LOCAL], self.node_id(LOCAL),
                        self.node_privkeys[REMOTE], self.node_id(REMOTE))

    def node_id_privkeys(self) -> Tuple[coincurve.PrivateKey, coincurve.PrivateKey]:
        """Returns node private keys, in order"""
        return keyorder(self.node_privkeys[LOCAL], self.node_privkeys[LOCAL],
                        self.node_privkeys[REMOTE], self.node_privkeys[REMOTE])

    def funding_pubkeys_for_gossip(self) -> Tuple[coincurve.PublicKey, coincurve.PublicKey]:
        """Returns funding public keys, in gossip order"""
        return keyorder(self.node_privkeys[LOCAL], self.funding_pubkey(LOCAL),
                        self.node_privkeys[REMOTE], self.funding_pubkey(REMOTE))

    def funding_privkeys_for_gossip(self) -> Tuple[coincurve.PublicKey, coincurve.PublicKey]:
        """Returns funding private keys, in gossip order"""
        return keyorder(self.node_privkeys[LOCAL], self.bitcoin_privkeys[LOCAL],
                        self.node_privkeys[REMOTE], self.bitcoin_privkeys[REMOTE])

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
        if self.funding_pubkey(LOCAL) == self.funding_pubkeys_for_gossip()[0]:
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
