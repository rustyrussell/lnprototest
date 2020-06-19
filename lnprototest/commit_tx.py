#! /usr/bin/python3
# FIXME: clean this up for use as pyln.proto.tx
from bitcoin.core import COutPoint, CTxOut, CTxIn, Hash160, CMutableTransaction, CTxWitness, CScriptWitness
import bitcoin.core.script as script
from bitcoin.core.script import CScript
import struct
from hashlib import sha256
from .keyset import KeySet
from .signature import Sig
from typing import List, Tuple, Callable, Optional, Union
from .event import Event, ResolvableInt
from .runner import Runner
from pyln.proto.message import Message
from .utils import Side
from .funding import Funding
import coincurve
import time
import functools


# FIXME
class HTLC(object):
    pass


class Commitment(object):
    def __init__(self,
                 funding: Funding,
                 opener: Side,
                 local_keyset: KeySet,
                 remote_keyset: KeySet,
                 local_to_self_delay: int,
                 remote_to_self_delay: int,
                 local_amount: int,
                 remote_amount: int,
                 local_dust_limit: int,
                 remote_dust_limit: int,
                 feerate: int,
                 option_static_remotekey: bool = False):
        self.opener = opener
        self.funding = funding
        self.feerate = feerate
        self.keyset = [local_keyset, remote_keyset]
        self.self_delay = (local_to_self_delay, remote_to_self_delay)
        self.amounts = [local_amount, remote_amount]
        self.dust_limit = (local_dust_limit, remote_dust_limit)
        self.htlcs: List[HTLC] = []
        self.commitnum = 0
        self.option_static_remotekey = option_static_remotekey

    def revocation_privkey(self, side: Side) -> coincurve.PrivateKey:
        """Derive the privkey used for the revocation of side's commitment transaction."""
        # BOLT #3:
        # The `revocationpubkey` is a blinded key: when the local node wishes
        # to create a new commitment for the remote node, it uses its own
        # `revocation_basepoint` and the remote node's `per_commitment_point`
        # to derive a new `revocationpubkey` for the commitment.
        revocation_basepoint_secret = self.keyset[not side].revocation_base_secret
        revocation_basepoint = self.keyset[not side].revocation_basepoint()
        per_commitment_secret = self.keyset[side].per_commit_secret(self.commitnum)
        per_commitment_point = self.keyset[side].per_commit_point(self.commitnum)

        # BOLT #3:
        # ...
        #    revocationprivkey = revocation_basepoint_secret * SHA256(revocation_basepoint || per_commitment_point)
        #      + per_commitment_secret * SHA256(per_commitment_point || revocation_basepoint)
        revocation_tweak = sha256(revocation_basepoint.format()
                                  + per_commitment_point.format()).digest()
        val = revocation_basepoint_secret.multiply(revocation_tweak,
                                                   update=False)

        per_commit_tweak = sha256(per_commitment_point.format()
                                  + revocation_basepoint.format()).digest()

        val2 = per_commitment_secret.multiply(per_commit_tweak, update=False)
        return val.add(val2.secret, update=False)

    def revocation_pubkey(self, side: Side) -> coincurve.PublicKey:
        """Derive the pubkey used for side's commitment transaction."""
        return coincurve.PublicKey.from_secret(self.revocation_privkey(side).secret)

    def _basepoint_tweak(self, basesecret: coincurve.PrivateKey, side: Side) -> coincurve.PrivateKey:
        # BOLT #3:
        # ### `localpubkey`, `local_htlcpubkey`, `remote_htlcpubkey`,
        #  `local_delayedpubkey`, and `remote_delayedpubkey` Derivation
        # ...
        # The corresponding private keys can be similarly derived, if the
        # basepoint secrets are known (i.e. the private keys corresponding to
        # `localpubkey`, `local_htlcpubkey`, and `local_delayedpubkey` only):
        #
        #    privkey = basepoint_secret + SHA256(per_commitment_point || basepoint)
        per_commit_point = self.keyset[side].per_commit_point(self.commitnum)
        basepoint = coincurve.PublicKey.from_secret(basesecret.secret)

        tweak = sha256(per_commit_point.format() + basepoint.format()).digest()
        return basesecret.add(tweak, update=False)

    def delayed_pubkey(self, side: Side) -> coincurve.PublicKey:
        """Generate local delayed_pubkey for this side"""
        privkey = self._basepoint_tweak(self.keyset[side].delayed_payment_base_secret, side)
        return coincurve.PublicKey.from_secret(privkey.secret)

    def to_remote_pubkey(self, side: Side) -> coincurve.PublicKey:
        """Generate remote payment key for this side"""
        # BOLT #3: If `option_static_remotekey` is negotiated the
        # `remotepubkey` is simply the remote node's `payment_basepoint`,
        # otherwise it is calculated as above using the remote node's
        # `payment_basepoint`.
        if self.option_static_remotekey:
            privkey = self.keyset[not side].payment_base_secret
        else:
            privkey = self._basepoint_tweak(self.keyset[not side].payment_base_secret, side)
            print("to-remote for side {}: self->payment = {} (local would be {}), per_commit_point = {}, keyset->self_payment_key = {}"
                  .format(side,
                          coincurve.PublicKey.from_secret(self.keyset[not side].payment_base_secret.secret).format().hex(),
                          coincurve.PublicKey.from_secret(self.keyset[Side.local].payment_base_secret.secret).format().hex(),
                          self.keyset[side].per_commit_point(self.commitnum).format().hex(),
                          coincurve.PublicKey.from_secret(privkey.secret).format().hex()))
        return coincurve.PublicKey.from_secret(privkey.secret)

    def add_htlc(self, tba: HTLC) -> None:
        raise NotImplementedError()

    def del_htlc(self, tba: HTLC) -> None:
        raise NotImplementedError()

    def inc_commitnum(self) -> None:
        self.commitnum += 1

    @staticmethod
    def obscured_commit_num(opener_payment_basepoint: coincurve.PublicKey,
                            non_opener_payment_basepoint: coincurve.PublicKey,
                            commitnum: int) -> int:
        # BOLT #3:
        # The 48-bit commitment number is obscured by `XOR` with the lower 48 bits of:
        #
        #    SHA256(payment_basepoint from open_channel || payment_basepoint from accept_channel)
        shabytes = sha256(opener_payment_basepoint.format()
                          + non_opener_payment_basepoint.format()).digest()[-6:]
        obscurer = struct.unpack('>Q', bytes(2) + shabytes)[0]
        return commitnum ^ obscurer

    def _fee(self, num_untrimmed_htlcs: int) -> int:
        # BOLT #3: The base fee for a commitment transaction:
        #  - MUST be calculated to match:
        #      1. Start with `weight` = 724.
        #      2. For each committed HTLC, if that output is not trimmed as specified in
        #      [Trimmed Outputs](#trimmed-outputs), add 172 to `weight`.
        #      3. Multiply `feerate_per_kw` by `weight`, divide by 1000 (rounding down).
        return ((724 + 172 * num_untrimmed_htlcs) * self.feerate) // 1000

    def _to_local_output(self, fee: int, side: Side) -> Tuple[script.CScript, int]:
        # BOLT #3:
        # #### `to_local` Output
        #
        # This output sends funds back to the owner of this commitment
        # transaction and thus must be timelocked using
        # `OP_CHECKSEQUENCEVERIFY`. It can be claimed, without delay, by the
        # other party if they know the revocation private key. The output is a
        # version-0 P2WSH, with a witness script:
        #
        #     OP_IF
        #         # Penalty transaction
        #         <revocationpubkey>
        #     OP_ELSE
        #         `to_self_delay`
        #         OP_CHECKSEQUENCEVERIFY
        #         OP_DROP
        #         <local_delayedpubkey>
        #     OP_ENDIF
        #     OP_CHECKSIG
        to_self_script = script.CScript([script.OP_IF,
                                         self.revocation_pubkey(side).format(),
                                         script.OP_ELSE,
                                         self.self_delay[side],
                                         script.OP_CHECKSEQUENCEVERIFY,
                                         script.OP_DROP,
                                         self.delayed_pubkey(side).format(),
                                         script.OP_ENDIF,
                                         script.OP_CHECKSIG])

        # BOLT #3: The amounts for each output MUST be rounded down to whole
        # satoshis. If this amount, minus the fees for the HTLC transaction,
        # is less than the `dust_limit_satoshis` set by the owner of the
        # commitment transaction, the output MUST NOT be produced (thus the
        # funds add to fees).
        amount_to_self = self.amounts[side] // 1000

        if side == self.opener:
            amount_to_self -= fee

        return to_self_script, amount_to_self

    def _unsigned_tx(self, side: Side) -> CMutableTransaction:
        ocn = self.obscured_commit_num(self.keyset[self.opener].payment_basepoint(),
                                       self.keyset[not self.opener].payment_basepoint(),
                                       self.commitnum)
        print("ocn = {} ({} + {} num {})".format(ocn,
                                                 self.keyset[self.opener].payment_basepoint().format().hex(),
                                                 self.keyset[not self.opener].payment_basepoint().format().hex(),
                                                 self.commitnum))

        # BOLT #3:
        # ## Commitment Transaction
        # ...
        # * txin count: 1
        #    * `txin[0]` outpoint: `txid` and `output_index` from `funding_created` message
        #    * `txin[0]` sequence: upper 8 bits are 0x80, lower 24 bits are upper 24 bits of the obscured commitment number
        #    * `txin[0]` script bytes: 0
        #    * `txin[0]` witness: `0 <signature_for_pubkey1> <signature_for_pubkey2>`
        txin = CTxIn(COutPoint(bytes.fromhex(self.funding.txid), self.funding.output_index),
                     nSequence=0x80000000 | (ocn >> 24))

        # txouts, with ctlv_timeouts for htlc output tiebreak
        txouts: List[Tuple[CTxOut, int]] = []

        # Add in untrimmed HTLC outputs.
        if len(self.htlcs) != 0:
            raise NotImplementedError()

        num_untrimmed_htlcs = len(txouts)
        fee = self._fee(num_untrimmed_htlcs)

        out_redeemscript, sats = self._to_local_output(fee, side)
        if sats >= self.dust_limit[side]:
            txouts.append((CTxOut(sats,
                                  CScript([script.OP_0, sha256(out_redeemscript).digest()])),
                           0))

        # BOLT #3:
        # #### `to_remote` Output
        #
        # This output sends funds to the other peer and thus is a simple
        # P2WPKH to `remotepubkey`.
        amount_to_other = self.amounts[not side] // 1000
        if not side == self.opener:
            amount_to_other -= fee

        if amount_to_other >= self.dust_limit[side]:
            txouts.append((CTxOut(amount_to_other,
                                  CScript([script.OP_0,
                                           Hash160(self.to_remote_pubkey(side).format())])),
                           0))

        # BOLT #3:
        # ## Transaction Input and Output Ordering
        #
        # Lexicographic ordering: see
        # [BIP69](https://github.com/bitcoin/bips/blob/master/bip-0069.mediawiki).
        # In the case of identical HTLC outputs, the outputs are ordered in
        # increasing `cltv_expiry` order.

        # First sort by cltv_expiry
        txouts.sort(key=lambda txout: txout[1])
        # Now sort by BIP69
        txouts.sort(key=lambda txout: txout[0].scriptPubKey)

        # BOLT #3:
        # ## Commitment Transaction
        #
        # * version: 2
        # * locktime: upper 8 bits are 0x20, lower 24 bits are the
        #   lower 24 bits of the obscured commitment number
        return CMutableTransaction(vin=[txin],
                                   vout=[txout[0] for txout in txouts],
                                   nVersion=2,
                                   nLockTime=0x20000000 | (ocn & 0x00FFFFFF))

    def local_unsigned_tx(self) -> CMutableTransaction:
        return self._unsigned_tx(Side.local)

    def remote_unsigned_tx(self) -> CMutableTransaction:
        return self._unsigned_tx(Side.remote)

    def _sig(self, privkey: coincurve.PrivateKey, tx: CMutableTransaction) -> Sig:
        sighash = script.SignatureHash(self.funding.redeemscript(), tx, inIdx=0,
                                       hashtype=script.SIGHASH_ALL,
                                       amount=self.funding.amount,
                                       sigversion=script.SIGVERSION_WITNESS_V0)
        return Sig(privkey.secret.hex(), sighash.hex())

    def local_sig(self, tx: CMutableTransaction) -> Sig:
        return self._sig(self.funding.bitcoin_privkeys[Side.local], tx)

    def remote_sig(self, tx: CMutableTransaction) -> Sig:
        print('Signing {} redeemscript keys {} and {}: {} amount = {}'.format(
            Side.remote,
            self.funding.funding_pubkey(Side.local).format().hex(),
            self.funding.funding_pubkey(Side.remote).format().hex(),
            self.funding.redeemscript().hex(),
            self.funding.amount))
        return self._sig(self.funding.bitcoin_privkeys[Side.remote], tx)

    def signed_tx(self, unsigned_tx: CMutableTransaction) -> CMutableTransaction:
        # BOLT #3:
        # * `txin[0]` witness: `0 <signature_for_pubkey1> <signature_for_pubkey2>`
        tx = unsigned_tx.copy()
        sighash = script.SignatureHash(self.funding.redeemscript(), tx, inIdx=0,
                                       hashtype=script.SIGHASH_ALL,
                                       amount=self.funding.amount,
                                       sigversion=script.SIGVERSION_WITNESS_V0)
        sigs = [key.sign(sighash, hasher=None) for key in self.funding.funding_privkeys_for_tx()]
        tx.wit = CTxWitness([CScriptWitness([bytes(),
                                             sigs[0] + bytes([script.SIGHASH_ALL]),
                                             sigs[1] + bytes([script.SIGHASH_ALL]),
                                             self.funding.redeemscript()])])
        return tx


ResolvableFunding = Union[Funding, Callable[['Runner', 'Event', str], Funding]]


class Commit(Event):
    def __init__(self,
                 opener: Side,
                 local_keyset: KeySet,
                 funding: ResolvableFunding,
                 local_to_self_delay: ResolvableInt,
                 remote_to_self_delay: ResolvableInt,
                 local_amount: ResolvableInt,
                 remote_amount: ResolvableInt,
                 local_dust_limit: ResolvableInt,
                 remote_dust_limit: ResolvableInt,
                 feerate: ResolvableInt,
                 option_static_remotekey: bool = False):
        super().__init__()
        self.funding = funding
        self.opener = opener
        self.local_keyset = local_keyset
        self.local_to_self_delay = local_to_self_delay
        self.remote_to_self_delay = remote_to_self_delay
        self.local_amount = local_amount
        self.remote_amount = remote_amount
        self.local_dust_limit = local_dust_limit
        self.remote_dust_limit = remote_dust_limit
        self.feerate = feerate
        self.option_static_remotekey = option_static_remotekey

    def action(self, runner: Runner) -> None:
        super().action(runner)

        commit = Commitment(local_keyset=self.local_keyset,
                            remote_keyset=runner.get_keyset(),
                            option_static_remotekey=self.option_static_remotekey,
                            opener=self.opener,
                            **self.resolve_args(runner,
                                                {'funding': self.funding,
                                                 'local_to_self_delay': self.local_to_self_delay,
                                                 'remote_to_self_delay': self.remote_to_self_delay,
                                                 'local_amount': self.local_amount,
                                                 'remote_amount': self.remote_amount,
                                                 'local_dust_limit': self.local_dust_limit,
                                                 'remote_dust_limit': self.remote_dust_limit,
                                                 'feerate': self.feerate}))
        runner.add_stash('Commit', commit)


def _commitsig_to_send(runner: Runner, event: Event, field: str) -> str:
    """Get remote side's remote sig"""
    tx = runner.get_stash(event, 'Commit').remote_unsigned_tx()
    return runner.get_stash(event, 'Commit').local_sig(tx)


def commitsig_to_send() -> Callable[[Runner, Event, str], str]:
    """Get the appropriate signature for the local side to send to the remote"""
    return _commitsig_to_send


def _commitsig_to_recv(runner: Runner, event: Event, field: str) -> str:
    """Get local side's remote sig"""
    tx = runner.get_stash(event, 'Commit').local_unsigned_tx()
    print('local_tx = {}'.format(tx.serialize().hex()))
    return runner.get_stash(event, 'Commit').remote_sig(tx)


def commitsig_to_recv() -> Callable[[Runner, Event, str], str]:
    """Get the appropriate signature for the remote side to send to the local"""
    return _commitsig_to_recv


def _channel_id(runner: Runner, event: Event, field: str) -> str:
    """Get the channel id"""
    return runner.get_stash(event, 'Commit').funding.channel_id()


def channel_id() -> Callable[[Runner, Event, str], str]:
    """Get the channel_id for the current Commit"""
    return _channel_id


def _channel_announcement(short_channel_id: str, features: bytes, runner: Runner, event: Event, field: str) -> Message:
    """Get the channel announcement"""
    return runner.get_stash(event, 'Commit').channel_announcement(short_channel_id, features)


def channel_announcement(short_channel_id: str, features: bytes) -> Callable[[Runner, Event, str], str]:
    """Get the channel_announcement for the current Commit"""
    return functools.partial(_channel_announcement, short_channel_id, features)


def _channel_update(short_channel_id: str,
                    side: Side,
                    disable: bool,
                    cltv_expiry_delta: int,
                    htlc_minimum_msat: int,
                    fee_base_msat: int,
                    fee_proportional_millionths: int,
                    timestamp: Optional[int],
                    htlc_maximum_msat: Optional[int],
                    runner: Runner, event: Event, field: str) -> Message:
    """Get the channel_update"""
    if timestamp is None:
        timestamp = int(time.time())
    return runner.get_stash(event, 'Commit').channel_update(short_channel_id, side, disable, cltv_expiry_delta, htlc_maximum_msat, fee_base_msat, fee_proportional_millionths, timestamp, htlc_maximum_msat)


def channel_update(short_channel_id: str,
                   side: Side,
                   disable: bool,
                   cltv_expiry_delta: int,
                   htlc_minimum_msat: int,
                   fee_base_msat: int,
                   fee_proportional_millionths: int,
                   htlc_maximum_msat: Optional[int],
                   timestamp: Optional[int] = None) -> Callable[[Runner, Event, str], str]:
    """Get a channel_update for the current Commit"""
    return functools.partial(_channel_update, short_channel_id, side, disable, cltv_expiry_delta, htlc_minimum_msat, fee_base_msat, fee_proportional_millionths, htlc_maximum_msat, timestamp)


def test_commitment_number() -> None:
    # BOLT #3:
    # In the following:
    #  - *local* transactions are considered, which implies that all payments to *local* are delayed.
    #  - It's assumed that *local* is the funder.
    ...
    #     commitment_number: 42

    # BOLT #3:
    # INTERNAL: local_payment_basepoint_secret: 111111111111111111111111111111111111111111111111111111111111111101
    # ...
    # INTERNAL: remote_payment_basepoint_secret: 444444444444444444444444444444444444444444444444444444444444444401
    opener_pubkey = coincurve.PublicKey.from_secret(bytes.fromhex('1111111111111111111111111111111111111111111111111111111111111111'))
    non_opener_pubkey = coincurve.PublicKey.from_secret(bytes.fromhex('4444444444444444444444444444444444444444444444444444444444444444'))

    # BOLT #3: Here are the points used to derive the obscuring factor
    # for the commitment number:
    # local_payment_basepoint: 034f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa
    # remote_payment_basepoint: 032c0b7cf95324a07d05398b240174dc0c2be444d96b159aa6c7f7b1e668680991
    # # obscured commitment number = 0x2bb038521914 ^ 42
    assert opener_pubkey.format().hex() == '034f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa'
    assert non_opener_pubkey.format().hex() == '032c0b7cf95324a07d05398b240174dc0c2be444d96b159aa6c7f7b1e668680991'

    assert Commitment.obscured_commit_num(opener_pubkey, non_opener_pubkey, 42) == 0x2bb038521914 ^ 42


def test_simple_commitment() -> None:
    # Damn, we can't use test vectors because they don't provide all the secrets!
    tx = Commitment(funding=Funding(funding_txid='8984484a580b825b9972d7adb15050b3ab624ccd731946b3eeddb92f4e7ef6be',
                                    funding_output_index=0,
                                    funding_amount=10000000,
                                    local_node_privkey='01',
                                    local_funding_privkey='01',
                                    remote_node_privkey='01',
                                    remote_funding_privkey='02'),
                    opener=Side.local,
                    local_keyset=KeySet('02', '03', '04', '05', '06' * 32),
                    remote_keyset=KeySet('12', '13', '14', '15', '16' * 32),
                    local_to_self_delay=144,
                    remote_to_self_delay=145,
                    local_amount=7000000000,
                    remote_amount=3000000000,
                    local_dust_limit=546,
                    remote_dust_limit=546,
                    feerate=15000,
                    option_static_remotekey=False)

    fee = tx._fee(0)
    out_redeemscript, sats = tx._to_local_output(fee, Side.local)
    assert sats == 6989140
    assert out_redeemscript == bytes.fromhex('6321') + tx.revocation_pubkey(Side.local).format() + bytes.fromhex('67029000b27521') + tx.delayed_pubkey(Side.local).format() + bytes.fromhex('68ac')
