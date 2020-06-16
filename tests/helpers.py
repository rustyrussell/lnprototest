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
#    UTXO: 16835ac8c154b616baac524163f41fb0c4f82c7b972ad35d4d6f18d854f6856b/1 (0.01BTC)
#
#    pubkey 0/0/2: 038f1573b4238a986470d250ce87c7a91257b6ba3baf2a0b14380c4e1e532c209d
#    privkey 0/0/2: bc2f48a76a6b8815940accaf01981d3b6347a68fbe844f81c50ecbadf27cd179
#    WIF 0/0/2: cTtWRYC39drNzaANPzDrgoYsMgs5LkfE5USKH9Kr9ySpEEdjYt3E
#    P2WPKH 0/0/2: bcrt1qlkt93775wmf33uacykc49v2j4tayn0yj25msjn
#    UTXO: 16835ac8c154b616baac524163f41fb0c4f82c7b972ad35d4d6f18d854f6856b/0 (0.02BTC)
#
#    pubkey 0/0/3: 02ffef0c295cf7ca3a4ceb8208534e61edf44c606e7990287f389f1ea055a1231c
#    privkey 0/0/3: 16c5027616e940d1e72b4c172557b3b799a93c0582f924441174ea556aadd01c
#    WIF 0/0/3: cNLxnoJSQDRzXnGPr4ihhy2oQqRBTjdUAM23fHLHbZ2pBsNbqMwb
#    P2WPKH 0/0/3: bcrt1q2ng546gs0ylfxrvwx0fauzcvhuz655en4kwe2c
#    UTXO: 16835ac8c154b616baac524163f41fb0c4f82c7b972ad35d4d6f18d854f6856b/3 (0.03BTC)
#
#    pubkey 0/0/4: 026957e53b46df017bd6460681d068e1d23a7b027de398272d0b15f59b78d060a9
#    privkey 0/0/4: 53ac43309b75d9b86bef32c5bbc99c500910b64f9ae089667c870c2cc69e17a4
#    WIF 0/0/4: cQPMJRjxse9i1jDeCo8H3khUMHYfXYomKbwF5zUqdPrFT6AmtTbd
#    P2WPKH 0/0/4: bcrt1qrdpwrlrmrnvn535l5eldt64lxm8r2nwkv0ruxq
#    UTXO: 16835ac8c154b616baac524163f41fb0c4f82c7b972ad35d4d6f18d854f6856b/4 (0.04BTC)
#
#    pubkey 0/0/5: 03a9f795ff2e4c27091f40e8f8277301824d1c3dfa6b0204aa92347314e41b1033
#    privkey 0/0/5: 16be98a5d4156f6f3af99205e9bc1395397bca53db967e50427583c94271d27f
#    WIF 0/0/5: cNLuxyjvR6ga2q6fdmSKxAd1CPQDShKV9yoA7zFKT7GJwZXr9MmT
#    P2WPKH 0/0/5: bcrt1q622lwmdzxxterumd746eu3d3t40pq53p62zhlz
#    UTXO: 16835ac8c154b616baac524163f41fb0c4f82c7b972ad35d4d6f18d854f6856b/2 (49.89995320BTC)
tx_spendable = '020000000001017b8705087f9bddd2777021d2a1dfefc2f1c5afa833b5c4ab00ccc8a556d042830000000000feffffff0580841e0000000000160014fd9658fbd476d318f3b825b152b152aafa49bc9240420f000000000016001483440596268132e6c99d44dae2d151dabd9a2b2338496d2901000000160014d295f76da2319791f36df5759e45b15d5e105221c0c62d000000000016001454d14ae910793e930d8e33d3de0b0cbf05aa533300093d00000000001600141b42e1fc7b1cd93a469fa67ed5eabf36ce354dd6024730440220782128cb0319a8430a687c51411e34cfaa6641da9a8f881d8898128cb5c46897022056e82d011a95fd6bcb6d0d4f10332b0b0d1227b2c4ced59e540eb708a4b24e4701210279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f8179865000000'


def utxo(index: int = 0) -> Tuple[str, int, int, str, int]:
    """Helper to get a P2WPKH UTXO, amount, privkey and fee from the tx_spendable transaction"""
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
    else:
        raise ValueError('index must be 0-4 inclusive')

    # Reasonable funding fee in sats
    reasonable_funding_fee = 122

    return txid_raw(tx_spendable), txout, (index + 1) * 1000000, key, reasonable_funding_fee


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
