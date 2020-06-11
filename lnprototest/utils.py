#! /usr/bin/python3
import string
import coincurve


def check_hex(val: str, digits: int) -> str:
    if not all(c in string.hexdigits for c in val):
        raise ValueError("{} is not valid hex".format(val))
    if len(val) != digits:
        raise ValueError("{} not {} characters long".format(val, digits))
    return val


def privkey_expand(secret: str) -> coincurve.PrivateKey:
    # Privkey can be truncated, since we use tiny values a lot.
    return coincurve.PrivateKey(bytes.fromhex(secret).rjust(32, bytes(1)))
