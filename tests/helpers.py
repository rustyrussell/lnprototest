import bitcoin.core
import coincurve
from typing import Tuple
from lnprototest import privkey_expand

# Here are the keys to spend funds, derived from BIP32 seed
# `0000000000000000000000000000000000000000000000000000000000000001`:
#
#    pubkey 0/0/1: 02d6a3c2d0cf7904ab6af54d7c959435a452b24a63194e1c4e7c337d3ebbb3017b
#    privkey 0/0/1: 76edf0c303b9e692da9cb491abedef46ca5b81d32f102eb4648461b239cb0f99
#    WIF 0/0/1: cRZtHFwyrV3CS1Muc9k4sXQRDhqA1Usgi8r7NhdEXLgM5CUEZufg
#    P2WPKH 0/0/1: bcrt1qsdzqt93xsyewdjvagndw9523m27e52er5ca7hm
#    UTXO: d3fb780146954eb42e371c80cbee1725f8ae330848522f105bda24e1fb1fc010/1 (0.01BTC)
#
#    pubkey 0/0/2: 038f1573b4238a986470d250ce87c7a91257b6ba3baf2a0b14380c4e1e532c209d
#    privkey 0/0/2: bc2f48a76a6b8815940accaf01981d3b6347a68fbe844f81c50ecbadf27cd179
#    WIF 0/0/2: cTtWRYC39drNzaANPzDrgoYsMgs5LkfE5USKH9Kr9ySpEEdjYt3E
#    P2WPKH 0/0/2: bcrt1qlkt93775wmf33uacykc49v2j4tayn0yj25msjn
#    UTXO: d3fb780146954eb42e371c80cbee1725f8ae330848522f105bda24e1fb1fc010/0 (0.02BTC)
#
#    pubkey 0/0/3: 02ffef0c295cf7ca3a4ceb8208534e61edf44c606e7990287f389f1ea055a1231c
#    privkey 0/0/3: 16c5027616e940d1e72b4c172557b3b799a93c0582f924441174ea556aadd01c
#    WIF 0/0/3: cNLxnoJSQDRzXnGPr4ihhy2oQqRBTjdUAM23fHLHbZ2pBsNbqMwb
#    P2WPKH 0/0/3: bcrt1q2ng546gs0ylfxrvwx0fauzcvhuz655en4kwe2c
#    UTXO: d3fb780146954eb42e371c80cbee1725f8ae330848522f105bda24e1fb1fc010/3 (0.03BTC)
#
#    pubkey 0/0/4: 026957e53b46df017bd6460681d068e1d23a7b027de398272d0b15f59b78d060a9
#    privkey 0/0/4: 53ac43309b75d9b86bef32c5bbc99c500910b64f9ae089667c870c2cc69e17a4
#    WIF 0/0/4: cQPMJRjxse9i1jDeCo8H3khUMHYfXYomKbwF5zUqdPrFT6AmtTbd
#    P2WPKH 0/0/4: bcrt1qrdpwrlrmrnvn535l5eldt64lxm8r2nwkv0ruxq
#    UTXO: d3fb780146954eb42e371c80cbee1725f8ae330848522f105bda24e1fb1fc010/4 (0.04BTC)
#
#    pubkey 0/0/5: 03a9f795ff2e4c27091f40e8f8277301824d1c3dfa6b0204aa92347314e41b1033
#    privkey 0/0/5: 16be98a5d4156f6f3af99205e9bc1395397bca53db967e50427583c94271d27f
#    WIF 0/0/5: cNLuxyjvR6ga2q6fdmSKxAd1CPQDShKV9yoA7zFKT7GJwZXr9MmT
#    P2WPKH 0/0/5: bcrt1q622lwmdzxxterumd746eu3d3t40pq53p62zhlz
#    UTXO: d3fb780146954eb42e371c80cbee1725f8ae330848522f105bda24e1fb1fc010/2 (48.89994700BTC)
#
#
# We add another UTXO which is solely spendable by the test framework, and not accessible to the
# runner -- needed for dual-funded tests.
#
#    pubkey: 02c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5
#    privkey: 0000000000000000000000000000000000000000000000000000000000000002
#    P2WPKH : bcrt1qq6hag67dl53wl99vzg42z8eyzfz2xlkvwk6f7m
#    UTXO: d3fb780146954eb42e371c80cbee1725f8ae330848522f105bda24e1fb1fc010/5 (0.005BTC)
#
tx_spendable = '0200000000010169d715fba6edece89b2dee71f4fed52c7accd6cd62c328536e6233b72b14c5f50000000000feffffff0680841e0000000000160014fd9658fbd476d318f3b825b152b152aafa49bc9240420f000000000016001483440596268132e6c99d44dae2d151dabd9a2b23aca5652901000000160014d295f76da2319791f36df5759e45b15d5e105221c0c62d000000000016001454d14ae910793e930d8e33d3de0b0cbf05aa533300093d00000000001600141b42e1fc7b1cd93a469fa67ed5eabf36ce354dd620a107000000000016001406afd46bcdfd22ef94ac122aa11f241244a37ecc024730440220628816b5182427d38bfed400d4800e4f7beeb9f659693b5f2a7368d935acc73102200e2e6c340c9dc24171af031a7d00b0ded68797b9e5d39e8a09604038bf5575cd0121020a6db711f4d03b34cde2ad81a3b65b31dc468a98a18827ad8d384c1e9d8383d865000000'


def utxo(index: int = 0) -> Tuple[str, int, int, str, int]:
    """Helper to get a P2WPKH UTXO, amount, privkey and fee from the tx_spendable transaction"""

    amount = (index + 1) * 1000000
    if index == 0:
        txout = 1
        key = '76edf0c303b9e692da9cb491abedef46ca5b81d32f102eb4648461b239cb0f99'
    elif index == 1:
        txout = 0
        key = 'bc2f48a76a6b8815940accaf01981d3b6347a68fbe844f81c50ecbadf27cd179'
    elif index == 2:
        txout = 3
        key = '16c5027616e940d1e72b4c172557b3b799a93c0582f924441174ea556aadd01c'
    elif index == 3:
        txout = 4
        key = '53ac43309b75d9b86bef32c5bbc99c500910b64f9ae089667c870c2cc69e17a4'
    elif index == 4:
        txout = 2
        key = '16be98a5d4156f6f3af99205e9bc1395397bca53db967e50427583c94271d27f'
        amount = 4889994700
    elif index == 5:
        txout = 5
        key = '0000000000000000000000000000000000000000000000000000000000000002'
        amount = 500000
    else:
        raise ValueError('index must be 0-5 inclusive')

    # Reasonable funding fee in sats
    reasonable_funding_fee = 200

    return txid_raw(tx_spendable), txout, amount, key, reasonable_funding_fee


def tx_out_for_index(index: int = 0) -> int:
    _, txout, _, _, _ = utxo(index)
    return txout


def privkey_for_index(index: int = 0) -> str:
    _, _, _, privkey, _ = utxo(index)
    return privkey


def funding_amount_for_utxo(index: int = 0) -> int:
    """How much can we fund a channel for using utxo #index?"""
    _, _, amt, _, fee = utxo(index)
    return amt - fee


def txid_raw(tx: str) -> str:
    """Helper to get the txid of a tx: note this is in wire protocol order, not bitcoin order!"""
    return bitcoin.core.CTransaction.deserialize(bytes.fromhex(tx)).GetTxid().hex()


def pubkey_of(privkey: str) -> str:
    """Return the public key corresponding to this privkey"""
    return coincurve.PublicKey.from_secret(privkey_expand(privkey).secret).format().hex()
