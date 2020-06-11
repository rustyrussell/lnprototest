#! /usr/bin/python3
from .errors import SpecFileError
from .structure import Sequence
from .event import Event
import coincurve
from typing import Dict, Optional, List, Union, Any


class Conn(object):
    """Class for connections.  Details filled in by the particular runner."""
    def __init__(self, connprivkey: str):
        """Create a connection from a node with the given hex privkey: we use
trivial values for private keys, so we simply left-pad with zeroes"""
        self.name = connprivkey
        self.connprivkey = coincurve.PrivateKey.from_hex(connprivkey.zfill(64))
        self.pubkey = coincurve.PublicKey.from_secret(self.connprivkey.secret)
        self.expected_error = False

    def __str__(self):
        return self.name


class Runner(object):
    """Abstract base class for runners"""
    def __init__(self, config):
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
        self.check_final_error(event, conn, conn.expected_error)

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
        while sequence.num_undone() != 0:
            self.restart()
            sequence.action(self)
            self.post_check(sequence)
        self.stop()

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

    def check_final_error(self, event: Event, conn: Conn, expected: bool) -> None:
        raise NotImplementedError()

    def start(self) -> None:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()

    def recv(self, event: Event, conn: Conn, outbuf: bytes) -> None:
        raise NotImplementedError()

    def get_output_message(self, conn: Conn) -> Optional[bytes]:
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

    def fundchannel(self,
                    event: Event,
                    conn: Conn,
                    amount: int,
                    txid: str,
                    outnum: int,
                    feerate: int) -> None:
        raise NotImplementedError()

    def addhtlc(self, event: Event, conn: Conn,
                amount: int, preimage: str) -> None:
        raise NotImplementedError()
