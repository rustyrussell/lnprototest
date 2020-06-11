#! /usr/bin/python3


def bitfield_len(msg, field):
    """Return length of this field in bits (assuming it's a bitfield!)"""
    return len(msg.fields[field]) * 8


def has_bit(msg, field, bitnum):
    """Does this field of this message have bitnum set?"""
    bitlen = bitfield_len(msg, field)
    if bitnum >= bitlen:
        return False
    return (msg.fields[field][bitlen // 8 - 1 - bitnum // 8] & (1 << (bitnum % 8)) != 0)


def bitfield(*args):
    """Create a bitfield hex value with these bit numbers set"""
    bytelen = max(args) + 8 // 8
    bfield = bytearray(bytelen)
    for bitnum in args:
        bfield[bytelen - 1 - bitnum // 8] |= (1 << (bitnum % 8))
    return bytes(bfield)
