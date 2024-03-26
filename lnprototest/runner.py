#! /usr/bin/python3
import logging
import shutil
import tempfile
import socket
import subprocess
import json
import time

import coincurve
import functools

from .bitfield import bitfield
from .errors import SpecFileError
from .structure import Sequence
from .event import Event, MustNotMsg, ExpectMsg
from .utils import privkey_expand
from .keyset import KeySet
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Union, Any, Callable


class Conn:
    pass


class Runner(ABC):
    """Abstract base class for runners.

    Most of the runner parameters can be extracted at runtime, but we do
    require that minimum_depth be 3, just for test simplicity.
    """

    def __init__(self, config: Any):
        self.config = config
        self.directory = tempfile.mkdtemp(prefix="lnpt-cl-")
        self.stash: Dict[str, Dict[str, Any]] = {}

        self.logger = logging.getLogger(__name__)
        if self.config.getoption("verbose"):
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        #
        self.run_server()
        self.impl_node_id = None
        self.port = None
        self.last_msg_unreaded = None

    def run_server(self) -> None:
        self.proc = subprocess.Popen(
            [
                "lnprototestd",
                "--data-dir={}".format(self.directory),
            ]
        )
        time.sleep(1)
        self.server.connect(f"{self.directory}/lnprototest.sock")
        self.server.settimeout(10.0)

    def finish_config(self, node_id: str, port: int) -> None:
        self.impl_node_id = node_id
        self.port = port

    def call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"lnprototest calling `{method}` with params `{params}`")
        self.server.sendall(
            json.dumps(
                {
                    "id": "runner/1",
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                }
            ).encode()
        )
        all_data = b""  # Byte string to hold all received data
        while True:
            data = self.server.recv(1024)  # Adjust the buffer size as needed
            if data:
                all_data += data
            else:
                break

            if data.endswith(b"\n"):
                # No more data; the server has closed the connection
                break
            self.logger.info(f"reading {data}")
        response = json.loads(all_data.decode())
        # FIXME: check the error here
        self.logger.info(f"{str(response)}")
        return response

    def _is_dummy(self) -> bool:
        """The DummyRunner returns True here, as it can't do some things"""
        return False

    # FIXME: this should be implemented because we should be albe
    # to disconnect the current connection
    def disconnect(self) -> None:
        pass

    def restart(self) -> None:
        self.disconnect()
        self.connect()
        self.stash = {}

    # FIXME: Why can't we use SequenceUnion here? Because python types sucks
    #
    # FIXME(vincenzo): Semplify in the future the type of events
    def run(self, events: Union[Sequence, List[Event], Event]) -> None:
        sequence = Sequence(events)
        self.start()
        while True:
            all_done = sequence.action(self)
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

    def teardown(self):
        """The Teardown method is called at the end of the test,
        and it is used to clean up the root dir where the tests are run."""
        shutil.rmtree(self.directory)

    def runner_features(
        self,
        additional_features: Optional[List[int]] = None,
        globals: bool = False,
    ) -> str:
        """
        Provide the features required by the node.
        """
        if additional_features is None:
            return ""
        else:
            return bitfield(*additional_features)

    @abstractmethod
    def is_running(self) -> bool:
        """Return a boolean value that tells whether the runner is running
        or not.
        Is leave up to the runner implementation to keep the runner state"""
        pass

    def connect(self, event: Event) -> None:
        msg = self.call("connect", {"NodeId": self.impl_node_id, "Port": self.port})
        if "error" not in msg:
            self.last_msg_unreaded = bytes.fromhex(msg["result"]["Msg"])
            return
        self.logger.error(f"{msg}")

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self, print_logs: bool = False) -> None:
        """
        Stop the runner, and print all the log that the ln
        implementation produced.

        Print the log is useful when we have a failure e we need
        to debug what happens during the tests.
        """
        pass

    def recv(self, event: Event, outbuf: bytes) -> None:
        msg = self.call("send", {"Msg": outbuf.hex()})
        if "error" not in msg:
            self.last_msg_unreaded = bytes.fromhex(msg["result"]["Msg"])
            return
        self.logger.error(f"{msg}")
        return

    def get_output_message(self, event: ExpectMsg) -> Optional[bytes]:
        msg = self.last_msg_unreaded
        if msg is not None:
            self.last_msg_unreaded = None
        return msg

    @abstractmethod
    def getblockheight(self) -> int:
        pass

    @abstractmethod
    def trim_blocks(self, newheight: int) -> None:
        pass

    @abstractmethod
    def add_blocks(self, event: Event, txs: List[str], n: int) -> None:
        pass

    @abstractmethod
    def expect_tx(self, event: Event, txid: str) -> None:
        pass

    @abstractmethod
    def invoice(self, event: Event, amount: int, preimage: str) -> None:
        pass

    @abstractmethod
    def accept_add_fund(self, event: Event) -> None:
        pass

    @abstractmethod
    def fundchannel(
        self,
        event: Event,
        conn: Conn,
        amount: int,
        feerate: int = 0,
        expect_fail: bool = False,
    ) -> None:
        pass

    @abstractmethod
    def init_rbf(
        self,
        event: Event,
        conn: Conn,
        channel_id: str,
        amount: int,
        utxo_txid: str,
        utxo_outnum: int,
        feerate: int,
    ) -> None:
        pass

    @abstractmethod
    def addhtlc(self, event: Event, conn: Conn, amount: int, preimage: str) -> None:
        pass

    @abstractmethod
    def get_keyset(self) -> KeySet:
        pass

    @abstractmethod
    def get_node_privkey(self) -> str:
        pass

    @abstractmethod
    def get_node_bitcoinkey(self) -> str:
        pass

    @abstractmethod
    def has_option(self, optname: str) -> Optional[str]:
        pass

    @abstractmethod
    def add_startup_flag(self, flag: str) -> None:
        pass

    @abstractmethod
    def close_channel(self, channel_id: str) -> None:
        """
        Close the channel with the specified channel id.

        :param channel_id:  the channel id as string value where the
        caller want to close;
        :return No value in case of success is expected,
        but an `RpcError` is expected in case of err.
        """
        pass


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

    def _remote_delayed_payment_basepoint(
        runner: Runner, event: Event, field: str
    ) -> str:
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
        return (
            coincurve.PublicKey.from_secret(
                privkey_expand(runner.get_node_bitcoinkey()).secret
            )
            .format()
            .hex()
        )

    return _remote_funding_pubkey


def remote_funding_privkey() -> Callable[[Runner, Event, str], str]:
    """Get the remote funding privkey (FIXME: we assume there's only one!)"""

    def _remote_funding_privkey(runner: Runner, event: Event, field: str) -> str:
        return runner.get_node_bitcoinkey()

    return _remote_funding_privkey


def remote_per_commitment_point(n: int) -> Callable[[Runner, Event, str], str]:
    """Get the n'th remote per-commitment point"""

    def _remote_per_commitment_point(
        n: int, runner: Runner, event: Event, field: str
    ) -> str:
        return runner.get_keyset().per_commit_point(n)

    return functools.partial(_remote_per_commitment_point, n)


def remote_per_commitment_secret(n: int) -> Callable[[Runner, Event, str], str]:
    """Get the n'th remote per-commitment secret"""

    def _remote_per_commitment_secret(runner: Runner, event: Event, field: str) -> str:
        return runner.get_keyset().per_commit_secret(n)

    return _remote_per_commitment_secret
