"""
Utils module that implement common function used across lnprototest library.
"""
import string
import coincurve
import time
import typing
import logging
import traceback

from typing import Union, Sequence, List
from enum import IntEnum

from lnprototest.keyset import KeySet


class Side(IntEnum):
    local = 0
    remote = 1

    def __not__(self) -> "Side":
        if self == Side.local:
            return Side.remote
        return Side.local


def check_hex(val: str, digits: int) -> str:
    if not all(c in string.hexdigits for c in val):
        raise ValueError("{} is not valid hex".format(val))
    if len(val) != digits:
        raise ValueError("{} not {} characters long".format(val, digits))
    return val


def privkey_expand(secret: str) -> coincurve.PrivateKey:
    # Privkey can be truncated, since we use tiny values a lot.
    return coincurve.PrivateKey(bytes.fromhex(secret).rjust(32, bytes(1)))


def pubkey_of(privkey: str) -> str:
    """Return the public key corresponding to this privkey"""
    return (
        coincurve.PublicKey.from_secret(privkey_expand(privkey).secret).format().hex()
    )


def privkey_for_index(index: int = 0) -> str:
    from lnprototest.utils.bitcoin_utils import utxo

    _, _, _, privkey, _ = utxo(index)
    return privkey


def gen_random_keyset(counter: int = 20) -> KeySet:
    """Helper function to generate a random keyset."""

    from lnprototest import privkey_expand

    return KeySet(
        revocation_base_secret=f"{counter + 1}",
        payment_base_secret=f"{counter + 2}",
        htlc_base_secret=f"{counter + 3}",
        delayed_payment_base_secret=f"{counter + 4}",
        shachain_seed="00" * 32,
    )


def wait_for(success: typing.Callable, timeout: int = 180) -> None:
    start_time = time.time()
    interval = 0.25
    while not success():
        time_left = start_time + timeout - time.time()
        if time_left <= 0:
            raise ValueError("Timeout while waiting for {}", success)
        time.sleep(min(interval, time_left))
        interval *= 2
        if interval > 5:
            interval = 5


def get_traceback(e: Exception) -> str:
    lines = traceback.format_exception(type(e), e, e.__traceback__)
    return "".join(lines)


def run_runner(runner: "Runner", test: Union[Sequence, List["Event"], "Event"]) -> None:
    """
    The pytest using the assertion as safe failure, and the exception it is only
    an event that must not happen.

    From design, lnprototest fails with an exception, and for this reason, if the
    lnprototest throws an exception, we catch it, and we fail with an assent.
    """
    try:
        runner.run(test)
    except Exception as ex:
        runner.stop(print_logs=True)
        logging.error(get_traceback(ex))
        assert False, ex


def merge_events_sequences(
    pre: Union[Sequence, List["Event"], "Event"],
    post: Union[Sequence, List["Event"], "Event"],
) -> Union[Sequence, List["Event"], "Event"]:
    """Merge the two list in the pre-post order"""
    pre.extend(post)
    return pre
