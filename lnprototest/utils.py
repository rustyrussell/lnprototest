#! /usr/bin/python3
import string
import coincurve

# regtest chain hash (hash of regtest genesis block)
regtest_hash = '06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f'


class Side(int):
    def __init__(self, v: int):
        self.v = int(v)

    def __not__(self) -> 'Side':
        return Side(not self.v)

    def __int__(self) -> int:
        return self.v


LOCAL = Side(0)
REMOTE = Side(1)


def check_hex(val: str, digits: int) -> str:
    if not all(c in string.hexdigits for c in val):
        raise ValueError("{} is not valid hex".format(val))
    if len(val) != digits:
        raise ValueError("{} not {} characters long".format(val, digits))
    return val


def privkey_expand(secret: str) -> coincurve.PrivateKey:
    # Privkey can be truncated, since we use tiny values a lot.
    return coincurve.PrivateKey(bytes.fromhex(secret).rjust(32, bytes(1)))
