#! /usr/bin/python3
# FIXME: clean this up for use as pyln.proto.tx
from bitcoin.core import COutPoint, CTxOut, CTxIn, Hash160, CMutableTransaction, CTxWitness, CScriptWitness
import bitcoin.core.script as script
from bitcoin.core.script import CScript
import struct
import hashlib
from hashlib import sha256
from .keyset import KeySet
from .errors import SpecFileError
from .signature import Sig
from typing import List, Tuple, Callable, Union, Optional, Dict
from .event import Event, ResolvableInt, ResolvableStr, negotiated, msat
from .runner import Runner
from .utils import Side, check_hex
from .funding import Funding
import coincurve


class HTLC(object):
    def __init__(self,
                 owner: Side,
                 amount_msat: int,
                 payment_secret: str,
                 cltv_expiry: int,
                 onion_routing_packet: str):
        """A HTLC offered by @owner"""
        self.owner = owner
        self.amount_msat = amount_msat
        self.payment_secret = check_hex(payment_secret, 64)
        self.cltv_expiry = cltv_expiry
        self.onion_routing_packet = check_hex(onion_routing_packet, 1366 * 2)

    def raw_payment_hash(self) -> bytes:
        return sha256(bytes.fromhex(self.payment_secret)).digest()

    def payment_hash(self) -> str:
        return self.raw_payment_hash().hex()

    def __str__(self) -> str:
        return "htlc({},{},{})".format(self.owner, self.amount_msat, self.payment_hash())

    @staticmethod
    def htlc_timeout_fee(feerate_per_kw: int) -> int:
        # BOLT #3:
        # The fee for an HTLC-timeout transaction:
        #   - MUST BE calculated to match:
        #     1. Multiply `feerate_per_kw` by 663 and divide by 1000 (rounding down).
        return feerate_per_kw * 663 // 1000

    @staticmethod
    def htlc_success_fee(feerate_per_kw: int) -> int:
        # BOLT #3:
        # The fee for an HTLC-success transaction:
        #   - MUST BE calculated to match:
        #     1. Multiply `feerate_per_kw` by 703 and divide by 1000 (rounding down).
        return feerate_per_kw * 703 // 1000


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
        self.htlcs: Dict[int, HTLC] = {}
        self.commitnum = 0
        self.option_static_remotekey = option_static_remotekey

    @staticmethod
    def ripemd160(b: bytes) -> bytes:
        hasher = hashlib.new('ripemd160')
        hasher.update(b)
        return hasher.digest()

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

    def local_htlc_pubkey(self, side: Side) -> coincurve.PublicKey:
        privkey = self._basepoint_tweak(self.keyset[side].htlc_base_secret, side)
        return coincurve.PublicKey.from_secret(privkey.secret)

    def remote_htlc_pubkey(self, side: Side) -> coincurve.PublicKey:
        privkey = self._basepoint_tweak(self.keyset[not side].htlc_base_secret, side)
        return coincurve.PublicKey.from_secret(privkey.secret)

    def add_htlc(self, htlc: HTLC, htlc_id: int) -> bool:
        if htlc_id in self.htlcs:
            return False
        self.htlcs[htlc_id] = htlc
        self.amounts[htlc.owner] -= htlc.amount_msat
        return True

    def del_htlc(self, htlc: HTLC, xfer_funds: bool) -> bool:
        for k, v in self.htlcs.items():
            if v == htlc:
                if xfer_funds:
                    gains_to = not htlc.owner
                else:
                    gains_to = htlc.owner  # type: ignore
                self.amounts[gains_to] += htlc.amount_msat
                del self.htlcs[k]
                return True
        return False

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

    def _offered_htlc_output(self, htlc: HTLC, side: Side) -> Tuple[script.CScript, int]:
        # BOLT #3: This output sends funds to either an HTLC-timeout
        # transaction after the HTLC-timeout or to the remote node
        # using the payment preimage or the revocation key. The output
        # is a P2WSH, with a witness script:
        #
        # # To remote node with revocation key
        # OP_DUP OP_HASH160 <RIPEMD160(SHA256(revocationpubkey))> OP_EQUAL
        # OP_IF
        #     OP_CHECKSIG
        # OP_ELSE
        #     <remote_htlcpubkey> OP_SWAP OP_SIZE 32 OP_EQUAL
        #     OP_NOTIF
        #         # To local node via HTLC-timeout transaction (timelocked).
        #         OP_DROP 2 OP_SWAP <local_htlcpubkey> 2 OP_CHECKMULTISIG
        #     OP_ELSE
        #         # To remote node with preimage.
        #         OP_HASH160 <RIPEMD160(payment_hash)> OP_EQUALVERIFY
        #         OP_CHECKSIG
        #     OP_ENDIF
        # OP_ENDIF
        htlc_script = script.CScript([script.OP_DUP,
                                      script.OP_HASH160,
                                      Hash160(self.revocation_pubkey(side).format()),
                                      script.OP_EQUAL,
                                      script.OP_IF,
                                      script.OP_CHECKSIG,
                                      script.OP_ELSE,
                                      self.remote_htlc_pubkey(side).format(),
                                      script.OP_SWAP,
                                      script.OP_SIZE,
                                      32,
                                      script.OP_EQUAL,
                                      script.OP_NOTIF,
                                      script.OP_DROP,
                                      2,
                                      script.OP_SWAP,
                                      self.local_htlc_pubkey(side).format(),
                                      2,
                                      script.OP_CHECKMULTISIG,
                                      script.OP_ELSE,
                                      script.OP_HASH160,
                                      self.ripemd160(htlc.raw_payment_hash()),
                                      script.OP_EQUALVERIFY,
                                      script.OP_CHECKSIG,
                                      script.OP_ENDIF,
                                      script.OP_ENDIF])

        # BOLT #3: The amounts for each output MUST be rounded down to whole
        # satoshis.
        return htlc_script, htlc.amount_msat // 1000

    def _received_htlc_output(self, htlc: HTLC, side: Side) -> Tuple[script.CScript, int]:
        # BOLT #3: This output sends funds to either the remote node after the
        # HTLC-timeout or using the revocation key, or to an HTLC-success
        # transaction with a successful payment preimage. The output is a
        # P2WSH, with a witness script:
        #
        # # To remote node with revocation key
        # OP_DUP OP_HASH160 <RIPEMD160(SHA256(revocationpubkey))> OP_EQUAL
        # OP_IF
        #     OP_CHECKSIG
        # OP_ELSE
        #     <remote_htlcpubkey> OP_SWAP OP_SIZE 32 OP_EQUAL
        #     OP_IF
        #         # To local node via HTLC-success transaction.
        #         OP_HASH160 <RIPEMD160(payment_hash)> OP_EQUALVERIFY
        #         2 OP_SWAP <local_htlcpubkey> 2 OP_CHECKMULTISIG
        #     OP_ELSE
        #         # To remote node after timeout.
        #         OP_DROP <cltv_expiry> OP_CHECKLOCKTIMEVERIFY OP_DROP
        #         OP_CHECKSIG
        #     OP_ENDIF
        # OP_ENDIF
        htlc_script = script.CScript([script.OP_DUP,
                                      script.OP_HASH160,
                                      Hash160(self.revocation_pubkey(side).format()),
                                      script.OP_EQUAL,
                                      script.OP_IF,
                                      script.OP_CHECKSIG,
                                      script.OP_ELSE,
                                      self.remote_htlc_pubkey(side).format(),
                                      script.OP_SWAP,
                                      script.OP_SIZE,
                                      32,
                                      script.OP_EQUAL,
                                      script.OP_IF,
                                      script.OP_HASH160,
                                      self.ripemd160(htlc.raw_payment_hash()),
                                      script.OP_EQUALVERIFY,
                                      2,
                                      script.OP_SWAP,
                                      self.local_htlc_pubkey(side).format(),
                                      2,
                                      script.OP_CHECKMULTISIG,
                                      script.OP_ELSE,
                                      script.OP_DROP,
                                      htlc.cltv_expiry,
                                      script.OP_CHECKLOCKTIMEVERIFY,
                                      script.OP_DROP,
                                      script.OP_CHECKSIG,
                                      script.OP_ENDIF,
                                      script.OP_ENDIF])

        # BOLT #3: The amounts for each output MUST be rounded down to whole
        # satoshis.
        return htlc_script, htlc.amount_msat // 1000

    def untrimmed_htlcs(self, side: Side) -> List[HTLC]:
        htlcs = []
        for _, htlc in self.htlcs.items():
            # BOLT #3:
            #   - for every offered HTLC:
            #     - if the HTLC amount minus the HTLC-timeout fee would be less than
            #     `dust_limit_satoshis` set by the transaction owner:
            #       - MUST NOT contain that output.
            #     - otherwise:
            #       - MUST be generated as specified in
            #       [Offered HTLC Outputs](#offered-htlc-outputs).
            if htlc.owner == side:
                # FIXME: Use Millisatoshi type?
                if htlc.amount_msat - msat(htlc.htlc_timeout_fee(self.feerate)) < msat(self.dust_limit[side]):
                    continue
            else:
                # BOLT #3:
                #   - for every received HTLC:
                #     - if the HTLC amount minus the HTLC-success fee would be less
                #      than `dust_limit_satoshis` set by the transaction owner:
                #       - MUST NOT contain that output.
                #     - otherwise:
                #       - MUST be generated as specified in
                #       [Received HTLC Outputs](#received-htlc-outputs).
                if htlc.amount_msat - msat(htlc.htlc_success_fee(self.feerate)) < msat(self.dust_limit[side]):
                    continue
            htlcs.append(htlc)

        return htlcs

    def htlc_outputs(self, side: Side) -> List[Tuple[HTLC, int, bytes]]:
        """Give CTxOut, cltv_expiry, redeemscript for each non-trimmed HTLC"""
        ret: List[Tuple[CTxOut, int, bytes]] = []

        for htlc in self.untrimmed_htlcs(side):
            if htlc.owner == side:
                redeemscript, sats = self._offered_htlc_output(htlc, side)
            else:
                redeemscript, sats = self._received_htlc_output(htlc, side)
            ret.append((CTxOut(sats,
                               CScript([script.OP_0, sha256(redeemscript).digest()])),
                        htlc.cltv_expiry,
                        redeemscript))

        return ret

    def _unsigned_tx(self, side: Side) -> Tuple[CMutableTransaction, List[Optional[HTLC]]]:
        """Create the commitment transaction.

Returns it and a list of matching HTLCs for each output

        """
        ocn = self.obscured_commit_num(self.keyset[self.opener].payment_basepoint(),
                                       self.keyset[not self.opener].payment_basepoint(),
                                       self.commitnum)

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

        # txouts, with ctlv_timeouts (for htlc output tiebreak) and htlc
        txouts: List[Tuple[CTxOut, int, Optional[HTLC]]] = []

        for htlc in self.untrimmed_htlcs(side):
            if htlc.owner == side:
                redeemscript, sats = self._offered_htlc_output(htlc, side)
            else:
                redeemscript, sats = self._received_htlc_output(htlc, side)
            print("*** Got htlc redeemscript {} / {}".format(redeemscript, redeemscript.hex()))
            txouts.append((CTxOut(sats,
                                  CScript([script.OP_0, sha256(redeemscript).digest()])),
                           htlc.cltv_expiry,
                           htlc))

        num_untrimmed_htlcs = len(txouts)
        fee = self._fee(num_untrimmed_htlcs)

        out_redeemscript, sats = self._to_local_output(fee, side)
        if sats >= self.dust_limit[side]:
            txouts.append((CTxOut(sats,
                                  CScript([script.OP_0, sha256(out_redeemscript).digest()])),
                           0,
                           None))

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
                           0,
                           None))

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
        txouts.sort(key=lambda txout: txout[0].serialize())

        # BOLT #3:
        # ## Commitment Transaction
        #
        # * version: 2
        # * locktime: upper 8 bits are 0x20, lower 24 bits are the
        #   lower 24 bits of the obscured commitment number
        return (CMutableTransaction(vin=[txin],
                                    vout=[txout[0] for txout in txouts],
                                    nVersion=2,
                                    nLockTime=0x20000000 | (ocn & 0x00FFFFFF)),
                [txout[2] for txout in txouts])

    def htlc_tx(self,
                commit_tx: CMutableTransaction,
                outnum: int,
                side: Side,
                amount_sat: int,
                locktime: int) -> CMutableTransaction:
        # BOLT #3:
        # ## HTLC-Timeout and HTLC-Success Transactions
        #
        # These HTLC transactions are almost identical, except the
        # HTLC-timeout transaction is timelocked. Both
        # HTLC-timeout/HTLC-success transactions can be spent by a valid
        # penalty transaction.

        # BOLT #3:
        # ## HTLC-Timeout and HTLC-Success Transactions
        # ...
        # * txin count: 1
        # * `txin[0]` outpoint: `txid` of the commitment transaction and
        #    `output_index` of the matching HTLC output for the HTLC transaction
        # * `txin[0]` sequence: `0`
        # * `txin[0]` script bytes: `0`
        txin = CTxIn(COutPoint(commit_tx.GetTxid(), outnum),
                     nSequence=0x0)

        # BOLT #3:
        # ## HTLC-Timeout and HTLC-Success Transactions
        # ...
        # * txout count: 1
        # * `txout[0]` amount: the HTLC amount minus fees (see [Fee
        #    Calculation](#fee-calculation))
        # * `txout[0]` script: version-0 P2WSH with witness script as shown below
        #
        # The witness script for the output is:
        # OP_IF
        #     # Penalty transaction
        #     <revocationpubkey>
        # OP_ELSE
        #     `to_self_delay`
        #     OP_CHECKSEQUENCEVERIFY
        #     OP_DROP
        #     <local_delayedpubkey>
        # OP_ENDIF
        # OP_CHECKSIG
        redeemscript = script.CScript([script.OP_IF,
                                       self.revocation_pubkey(side).format(),
                                       script.OP_ELSE,
                                       self.self_delay[side],
                                       script.OP_CHECKSEQUENCEVERIFY,
                                       script.OP_DROP,
                                       self.delayed_pubkey(side).format(),
                                       script.OP_ENDIF,
                                       script.OP_CHECKSIG])
        print("htlc redeemscript = {}".format(redeemscript.hex()))
        txout = CTxOut(amount_sat,
                       CScript([script.OP_0, sha256(redeemscript).digest()]))

        # BOLT #3:
        # ## HTLC-Timeout and HTLC-Success Transactions
        # ...
        # * version: 2
        # * locktime: `0` for HTLC-success, `cltv_expiry` for HTLC-timeout
        return CMutableTransaction(vin=[txin],
                                   vout=[txout],
                                   nVersion=2,
                                   nLockTime=locktime)

    def local_unsigned_tx(self) -> CMutableTransaction:
        return self._unsigned_tx(Side.local)[0]

    def remote_unsigned_tx(self) -> CMutableTransaction:
        return self._unsigned_tx(Side.remote)[0]

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

    def htlc_sigs(self, signer: Side, side: Side) -> List[Sig]:
        """Produce the signer's signatures for the dest's HTLC transactions"""
        # BOLT #2:
        # - MUST include one `htlc_signature` for every HTLC transaction
        #   corresponding to the ordering of the commitment transaction (see
        #   [BOLT
        #   #3](03-transactions.md#transaction-input-and-output-ordering)).

        # So we need the HTLCs in output order, which is why we had _unsigned_tx
        # return them.
        commit_tx, htlcs = self._unsigned_tx(side)

        sigs: List[Sig] = []
        for outnum, htlc in enumerate(htlcs):
            # to_local or to_remote output?
            if htlc is None:
                continue
            if htlc.owner == side:
                redeemscript, sats = self._offered_htlc_output(htlc, side)
                fee = htlc.htlc_timeout_fee(self.feerate)
                # BOLT #3:
                # * locktime: `0` for HTLC-success, `cltv_expiry` for HTLC-timeout
                locktime = htlc.cltv_expiry
            else:
                redeemscript, sats = self._received_htlc_output(htlc, side)
                fee = htlc.htlc_success_fee(self.feerate)
                locktime = 0

            htlc_tx = self.htlc_tx(commit_tx, outnum, side,
                                   (htlc.amount_msat - msat(fee)) // 1000,
                                   locktime)
            print("htlc_tx = {}".format(htlc_tx.serialize().hex()))
            sighash = script.SignatureHash(redeemscript, htlc_tx, inIdx=0,
                                           hashtype=script.SIGHASH_ALL,
                                           amount=htlc.amount_msat // 1000,
                                           sigversion=script.SIGVERSION_WITNESS_V0)
            privkey = self._basepoint_tweak(self.keyset[signer].htlc_base_secret, side)
            sigs.append(Sig(privkey.secret.hex(), sighash.hex()))

        return sigs

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
                 local_features: ResolvableStr,
                 remote_features: ResolvableStr):
        """Stashes a commitment transaction as 'Commit'.

Note that local_to_self_delay is dictated by the remote side, and
remote_to_self_delay is dicated by the local side!

        """
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
        self.static_remotekey = negotiated(local_features, remote_features, [12])

    def action(self, runner: Runner) -> bool:
        super().action(runner)

        # BOLT #9:
        # | 12/13 | `option_static_remotekey`        | Static key for remote output
        commit = Commitment(local_keyset=self.local_keyset,
                            remote_keyset=runner.get_keyset(),
                            option_static_remotekey=self.resolve_arg('option_static_remotekey',
                                                                     runner, self.static_remotekey),
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
        return True


class UpdateCommit(Event):
    def __init__(self,
                 new_htlcs: List[Tuple[HTLC, int]] = [],
                 resolved_htlcs: List[HTLC] = [],
                 failed_htlcs: List[HTLC] = [],
                 new_feerate: Optional[ResolvableInt] = None):
        super().__init__()
        self.new_htlcs = new_htlcs
        self.resolved_htlcs = resolved_htlcs
        self.failed_htlcs = failed_htlcs
        self.new_feerate = new_feerate

    def action(self, runner: Runner) -> bool:
        super().action(runner)

        commit: Commitment = runner.get_stash(self, 'Commit')
        for htlc, htlc_id in self.new_htlcs:
            if not commit.add_htlc(htlc, htlc_id):
                raise SpecFileError(self, "Already have htlc id {}".format(htlc_id))
        for htlc in self.resolved_htlcs:
            if not commit.del_htlc(htlc, xfer_funds=True):
                raise SpecFileError(self, "Cannot resolve missing htlc {}".format(htlc))
        for htlc in self.failed_htlcs:
            if not commit.del_htlc(htlc, xfer_funds=False):
                raise SpecFileError(self, "Cannot resolve missing htlc {}".format(htlc))

        if self.new_feerate is not None:
            commit.feerate = self.resolve_arg('feerate', runner, self.new_feerate)

        commit.inc_commitnum()
        return True


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
