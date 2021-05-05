#! /usr/bin/python3
from .errors import SpecFileError
from .structure import Sequence
from .event import Event, MustNotMsg, ExpectMsg
from .utils import privkey_expand
from .keyset import KeySet
import coincurve
import functools
from typing import Dict, Optional, List, Union, Any, Callable


class Conn(object):
    """Class for connections.  Details filled in by the particular runner."""
    def __init__(self, connprivkey: str):
        """Create a connection from a node with the given hex privkey: we use
trivial values for private keys, so we simply left-pad with zeroes"""
        self.name = connprivkey
        self.connprivkey = privkey_expand(connprivkey)
        self.pubkey = coincurve.PublicKey.from_secret(self.connprivkey.secret)
        self.expected_error = False
        self.must_not_events: List[MustNotMsg] = []

    def __str__(self) -> str:
        return self.name


class Runner(object):
    """Abstract base class for runners.

Most of the runner parameters can be extracted at runtime, but we do
require that minimum_depth be 3, just for test simplicity.

    """
    def __init__(self, config: Any):
        self.config = config
        # key == connprivkey, value == Conn
        self.conns: Dict[str, Conn] = {}
        self.last_conn: Optional[Conn] = None
        self.stash: Dict[str, Dict[str, Any]] = {}

    def _is_dummy(self) -> bool:
        """The DummyRunner returns True here, as it can't do some things"""
        return False

    def find_conn(self, connprivkey: Optional[str]) -> Optional[Conn]:
        # Default is whatever we specified last.
        if connprivkey is None:
            return self.last_conn
        if connprivkey in self.conns:
            self.last_conn = self.conns[connprivkey]
            return self.last_conn
        return None

    def add_conn(self, conn: Conn) -> None:
        self.conns[conn.name] = conn
        self.last_conn = conn

    def disconnect(self, event: Event, conn: Conn) -> None:
        if conn is None:
            raise SpecFileError(event, "Unknown conn")
        del self.conns[conn.name]
        self.check_final_error(event, conn, conn.expected_error, conn.must_not_events)

    def check_error(self, event: Event, conn: Conn) -> Optional[str]:
        conn.expected_error = True
        return None

    def post_check(self, sequence: Sequence) -> None:
        # Make sure no connection had an error.
        while len(self.conns) != 0:
            self.disconnect(sequence, next(iter(self.conns.values())))

    def restart(self) -> None:
        self.conns = {}
        self.last_conn = None
        self.stash = {}

    # FIXME: Why can't we use SequenceUnion here?
    def run(self, events: Union[Sequence, List[Event], Event]) -> None:
        sequence = Sequence(events)
        self.start()
        while True:
            all_done = sequence.action(self)
            self.post_check(sequence)
            if all_done:
                self.stop()
                return
            self.restart()

    def add_stash(self, stashname: str, vals: Any) -> None:
        """Add a dict to the stash."""
        self.stash[stashname] = vals

    def get_stash(self, event: Event, stashname: str, default: Any = None) -> Any:
        """Get an entry from the stash."""
        if stashname not in self.stash:
            if default is not None:
                return default
            raise SpecFileError(event, "Unknown stash name {}".format(stashname))
        return self.stash[stashname]

    # You need to implement these!
    def connect(self, event: Event, connprivkey: str) -> None:
        raise NotImplementedError()

    def check_final_error(self, event: Event, conn: Conn, expected: bool, must_not_events: List[MustNotMsg]) -> None:
        raise NotImplementedError()

    def start(self) -> None:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()

    def recv(self, event: Event, conn: Conn, outbuf: bytes) -> None:
        raise NotImplementedError()

    def get_output_message(self, conn: Conn, event: ExpectMsg) -> Optional[bytes]:
        raise NotImplementedError()

    def getblockheight(self) -> int:
        raise NotImplementedError()

    def trim_blocks(self, newheight: int) -> None:
        raise NotImplementedError()

    def add_blocks(self, event: Event, txs: List[str], n: int) -> None:
        raise NotImplementedError()

    def expect_tx(self, event: Event, txid: str) -> None:
        raise NotImplementedError()

    def invoice(self, event: Event, amount: int, preimage: str) -> None:
        raise NotImplementedError()

    def accept_add_fund(self, event: Event) -> None:
        raise NotImplementedError()

    def fundchannel(self,
                    event: Event,
                    conn: Conn,
                    amount: int,
                    feerate: int = 0,
                    expect_fail: bool = False) -> None:
        raise NotImplementedError()

    def init_rbf(self,
                 event: Event,
                 conn: Conn,
                 channel_id: str,
                 amount: int,
                 utxo_txid: str,
                 utxo_outnum: int,
                 feerate: int) -> None:
        raise NotImplementedError()

    def addhtlc(self, event: Event, conn: Conn,
                amount: int, preimage: str) -> None:
        raise NotImplementedError()

    def get_keyset(self) -> KeySet:
        raise NotImplementedError()

    def get_node_privkey(self) -> str:
        raise NotImplementedError()

    def get_node_bitcoinkey(self) -> str:
        raise NotImplementedError()

    def has_option(self, optname: str) -> Optional[str]:
        raise NotImplementedError()

    def add_startup_flag(self, flag: str) -> None:
        raise NotImplementedError()


def remote_revocation_basepoint() -> Callable[[Runner, Event, str], str]:
    """Get the remote revocation basepoint"""
    def _remote_revocation_basepoint(runner: Runner, event: Event, field: str) -> str:
        return runner.get_keyset().revocation_basepoint()

    return _remote_revocation_basepoint


def remote_payment_basepoint() -> Callable[[Runner, Event, str], str]:
    """Get the remote payment basepoint"""
    def _remote_payment_basepoint(runner: Runner, event: Event, field: str) -> str:
        return runner.get_keyset().payment_basepoint()
    return _remote_payment_basepoint


def remote_delayed_payment_basepoint() -> Callable[[Runner, Event, str], str]:
    """Get the remote delayed_payment basepoint"""
    def _remote_delayed_payment_basepoint(runner: Runner, event: Event, field: str) -> str:
        return runner.get_keyset().delayed_payment_basepoint()
    return _remote_delayed_payment_basepoint


def remote_htlc_basepoint() -> Callable[[Runner, Event, str], str]:
    """Get the remote htlc basepoint"""
    def _remote_htlc_basepoint(runner: Runner, event: Event, field: str) -> str:
        return runner.get_keyset().htlc_basepoint()
    return _remote_htlc_basepoint


def remote_funding_pubkey() -> Callable[[Runner, Event, str], str]:
    """Get the remote funding pubkey (FIXME: we assume there's only one!)"""
    def _remote_funding_pubkey(runner: Runner, event: Event, field: str) -> str:
        return coincurve.PublicKey.from_secret(privkey_expand(runner.get_node_bitcoinkey()).secret).format().hex()
    return _remote_funding_pubkey


def remote_funding_privkey() -> Callable[[Runner, Event, str], str]:
    """Get the remote funding privkey (FIXME: we assume there's only one!)"""
    def _remote_funding_privkey(runner: Runner, event: Event, field: str) -> str:
        return runner.get_node_bitcoinkey()
    return _remote_funding_privkey


def remote_per_commitment_point(n: int) -> Callable[[Runner, Event, str], str]:
    """Get the n'th remote per-commitment point"""
    def _remote_per_commitment_point(n: int, runner: Runner, event: Event, field: str) -> str:
        return runner.get_keyset().per_commit_point(n)
    return functools.partial(_remote_per_commitment_point, n)


def remote_per_commitment_secret(n: int) -> Callable[[Runner, Event, str], str]:
    """Get the n'th remote per-commitment secret"""
    def _remote_per_commitment_secret(runner: Runner, event: Event, field: str) -> str:
        return runner.get_keyset().per_commit_secret(n)
    return _remote_per_commitment_secret
