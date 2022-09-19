"""
Bitcoin utils is a collection of methods that helps to
work with bitcoin primitive.
"""
import hashlib
from enum import Enum

from bitcoin.core import Hash160, x
from bitcoin.core.script import OP_0, OP_CHECKSIG, CScript
from bitcoin.wallet import CBitcoinSecret


class ScriptType(Enum):
    """
    Type of Script used in the Runner.

    In particular, during the testing we need to have
    two type of script, the valid one and the invalid one.
    This is useful when is needed to send an invalid script.

    FIXME: naming is too simple.
    """

    VALID_CLOSE_SCRIPT = 1
    INVALID_CLOSE_SCRIPT = 2


class BitcoinUtils:
    """Main implementation class of the lightning networks utils.

    The implementation class contains only static methods that
    apply the rules specified by the BIP."""

    @staticmethod
    def blockchain_hash() -> str:
        """Return the chain transaction hash.
        That in this case is the regtest transaction hash."""
        return "06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f"

    @staticmethod
    def build_valid_script(
        script_type: ScriptType = ScriptType.VALID_CLOSE_SCRIPT,
        word: str = "lnprototest",
    ) -> str:
        """Build a valid bitcoin script and hide the primitive of the library"""
        secret_str = f"correct horse battery staple {word}"
        h = hashlib.sha256(secret_str.encode("ascii")).digest()
        seckey = CBitcoinSecret.from_secret_bytes(h)
        if script_type is ScriptType.VALID_CLOSE_SCRIPT:
            return CScript([OP_0, Hash160(seckey.pub)]).hex()
        elif script_type is ScriptType.INVALID_CLOSE_SCRIPT:
            return CScript([seckey.pub, OP_CHECKSIG]).hex()

    @staticmethod
    def build_script(hex: str) -> CScript:
        return CScript(x(hex))
