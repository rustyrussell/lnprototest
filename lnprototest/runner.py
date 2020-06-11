#! /usr/bin/python3
from .errors import SpecFileError
from .structure import Sequence
import coincurve


class Conn(object):
    """Class for connections.  Details filled in by the particular runner."""
    def __init__(self, connprivkey):
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
        self.conns = {}
        self.last_conn = None

    def _is_dummy(self):
        """The DummyRunner returns True here, as it can't do some things"""
        return False

    def find_conn(self, connprivkey):
        # Default is whatever we specified last.
        if connprivkey is None:
            return self.last_conn
        if connprivkey in self.conns:
            self.last_conn = self.conns[connprivkey]
            return self.last_conn
        return None

    def add_conn(self, conn):
        self.conns[conn.name] = conn
        self.last_conn = conn

    def disconnect(self, event, conn):
        if conn is None:
            raise SpecFileError(event, "Unknown conn")
        del self.conns[conn.name]
        self.check_final_error(event, conn, conn.expected_error)

    def check_error(self, event, conn):
        conn.expected_error = True
        return None

    def post_check(self, sequence):
        # Make sure no connection had an error.
        while len(self.conns) != 0:
            self.disconnect(sequence, next(iter(self.conns.values())))

    def restart(self):
        self.conns = {}
        self.last_conn = None

    def run(self, events):
        sequence = Sequence(events)
        self.start()
        while sequence.num_undone() != 0:
            self.restart()
            sequence.action(self)
            self.post_check(sequence)
        self.stop()
