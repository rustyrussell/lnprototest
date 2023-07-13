#! /usr/bin/python3
# This script exercises the c-lightning implementation

# Released by Rusty Russell under CC0:
# https://creativecommons.org/publicdomain/zero/1.0/

import hashlib
import pyln.client
import pyln.proto.wire
import os
import subprocess
import lnprototest
import bitcoin.core
import struct
import shutil
import logging
import signal
import time

from datetime import datetime
from concurrent import futures
from ephemeral_port_reserve import reserve
from lnprototest.backend import Bitcoind
from lnprototest import (
    Event,
    EventError,
    SpecFileError,
    KeySet,
    Conn,
    namespace,
    MustNotMsg,
    bitfield,
)
from lnprototest import wait_for
from typing import Dict, Any, Callable, List, Optional, cast

TIMEOUT = int(os.getenv("TIMEOUT", "60"))
LDK_SRC = os.path.join(os.getcwd(), os.getenv("LDK_SRC", "../ldk-sample"))


class LDKConn(lnprototest.Conn):
    def __init__(self, connprivkey: str, port: int, node_id: str):
        super().__init__(connprivkey)
        self.connection = pyln.proto.wire.connect(
            pyln.proto.wire.PrivateKey(bytes.fromhex(self.connprivkey.to_hex())),
            pyln.proto.wire.PublicKey(bytes.fromhex(node_id)),
            "127.0.0.1",
            port,
        )


class Runner(lnprototest.Runner):
    def __init__(self, config: Any):
        super().__init__(config)
        self.running = False
        self.bitcoind = None
        self.proc = None
        self.cleanup_callbacks: List[Callable[[], None]] = []
        self.fundchannel_future: Optional[Any] = None
        self.is_fundchannel_kill = False
        self.executor = futures.ThreadPoolExecutor(max_workers=20)
        self.ldk_port = reserve()
        self.node_id = None

        opts = "DataLossProtect: supported, InitialRoutingSync: not supported, UpfrontShutdownScript: supported, GossipQueries: not supported, VariableLengthOnion: required, StaticRemoteKey: required, PaymentSecret: required, BasicMPP: supported, Wumbo: supported, AnchorsZeroFeeHtlcTx: not supported, ShutdownAnySegwit: supported, OnionMessages: not supported, ChannelType: supported, SCIDPrivacy: supported, ZeroConf: supported, unknown flags: none".split(
            ", "
        )

        self.options: Dict[str, str] = {}
        val: Dict[str, str] = {}
        val["supported"] = "odd"
        val["required"] = "even"
        val["not supported"] = None

        for o in opts:
            k, v = o.split(": ")
            if k == "DataLossProtect":
                self.options["option_data_loss_protect"] = val[v]
            elif k == "InitialRoutingSync":
                self.options["initial_routing_sync"] = val[v]
            elif k == "UpfrontShutdownScript":
                self.options["option_upfront_shutdown_script"] = val[v]
            elif k == "GossipQueries":
                self.options["option_gossip_queries"] = val[v]
            elif k == "VariableLengthOnion":
                self.options["option_var_onion_optin"] = val[v]
            elif k == "StaticRemoteKey":
                self.options["option_static_remotekey"] = val[v]
            elif k == "PaymentSecret":
                self.options["option_payment_secret"] = val[v]
            elif k == "BasicMPP":
                self.options["option_basic_mpp"] = val[v]
            elif k == "AnchorsZeroFeeHtlcTx":
                self.options["option_anchors_zero_fee_htlc_tx"] = val[v]
            elif k == "ShutdownAnySegwit":
                self.options["option_shutdown_anysegwit"] = val[v]
            elif k == "ChannelType" and val[v] == "odd":
                self.options["supports_open_accept_channel_type"] = "true"
            elif k == "SCIDPrivacy":
                self.options["option_scid_alias"] = val[v]
            elif k == "Keysend":
                self.options["option_keysend"] = val[v]
            else:
                self.options[k] = None

    def __init_sandbox_dir(self) -> None:
        """Create the tmp directory for lnprotest and ldk"""
        self.ldk_dir = os.path.join(self.directory, "ldk")
        if not os.path.exists(self.ldk_dir):
            os.makedirs(self.ldk_dir)

    def get_keyset(self) -> KeySet:
        return KeySet(
            revocation_base_secret="0000000000000000000000000000000000000000000000000000000000000011",
            payment_base_secret="0000000000000000000000000000000000000000000000000000000000000012",
            delayed_payment_base_secret="0000000000000000000000000000000000000000000000000000000000000013",
            htlc_base_secret="0000000000000000000000000000000000000000000000000000000000000014",
            shachain_seed="FF" * 32,
        )

    def get_node_privkey(self) -> str:
        return "0000000000000000000000000000000000000000000000000000000000000001"

    def get_node_bitcoinkey(self) -> str:
        return "0000000000000000000000000000000000000000000000000000000000000010"

    def is_running(self) -> bool:
        return self.running

    def start(self) -> None:
        self.logger.debug("[START]")
        self.__init_sandbox_dir()
        self.bitcoind = Bitcoind(self.directory)
        try:
            self.bitcoind.start()
        except Exception as ex:
            self.logger.debug(f"Exception with message {ex}")

        self.logger.debug("RUN Bitcoind")

        self.proc = subprocess.Popen(
            [
                "{}/target/debug/ldk-sample".format(LDK_SRC),
                "{}:{}@127.0.0.1:{}".format("rpcuser", "rpcpass", self.bitcoind.port),
                "{}/".format(self.ldk_dir),
                "{}".format(self.ldk_port),
                "regtest",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        self.logger.debug("ldk dir {}".format(self.ldk_dir))
        err1 = self.proc.stdout.readline()
        err2 = self.proc.stdout.readline()
        self.node_id = self.proc.stdout.readline().decode("utf-8")[17:83]
        self.running = True
        self.logger.debug("{} gggg {} Node id >>> {}".format(err1, err2, self.node_id))
        self.logger.debug("RUN LDK")

    def shutdown(self) -> None:
        for cb in self.cleanup_callbacks:
            cb()
        self.proc.stdin.write(b"exit")
        self.proc.stdin.flush()
        os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
        self.bitcoind.stop()

    def stop(self, print_logs: bool = True) -> None:
        self.logger.debug("[STOP]")
        self.shutdown()
        self.running = False
        for c in self.conns.values():
            cast(LDKConn, c).connection.connection.close()

        log_path = f"{self.ldk_dir}/.ldk/logs/logs.txt"
        with open(log_path) as log:
            self.logger.info("---------- LDK logging ----------------")
            self.logger.info(log.read())
            shutil.copy(
                log_path,
                f'/tmp/ldk-log_{datetime.now().strftime("%b-%d-%Y_%H:%M:%S")}',
            )
        shutil.rmtree(os.path.join(self.ldk_dir, ".ldk"))

    def restart(self) -> None:
        self.logger.debug("[RESTART]")
        self.stop()
        # Make a clean start
        super().restart()
        self.start()

    def kill_fundchannel(self) -> None:
        fut = self.fundchannel_future
        self.fundchannel_future = None
        self.is_fundchannel_kill = True

        if fut:
            try:
                fut.result(0)
            except (SpecFileError, futures.TimeoutError):
                pass
            except Exception as ex:
                raise ex from None

    def connect(self, event: Event, connprivkey: str) -> None:
        self.add_conn(LDKConn(connprivkey, self.ldk_port, self.node_id))

    def getblockheight(self) -> int:
        return self.bitcoind.rpc.getblockcount()

    def trim_blocks(self, newheight: int) -> None:
        h = self.bitcoind.rpc.getblockhash(newheight + 1)
        self.bitcoind.rpc.invalidateblock(h)

    def add_blocks(self, event: Event, txs: List[str], n: int) -> None:
        for tx in txs:
            self.bitcoind.rpc.sendrawtransaction(tx)
        self.bitcoind.rpc.generatetoaddress(n, self.bitcoind.rpc.getnewaddress())

    def recv(self, event: Event, conn: Conn, outbuf: bytes) -> None:
        self.logger.debug("recv")
        try:
            cast(LDKConn, conn).connection.send_message(outbuf)
            self.logger.debug("recv 2")
        except BrokenPipeError:
            # This happens when they've sent an error and closed; try
            # reading it to figure out what went wrong.
            fut = self.executor.submit(cast(LDKConn, conn).connection.read_message)
            self.logger.debug("recv 3")
            try:
                msg = fut.result(1)
            except futures.TimeoutError:
                msg = None
            if msg:
                raise EventError(
                    event, "Connection closed after sending {}".format(msg.hex())
                )
            else:
                raise EventError(event, "Connection closed")

    def fundchannel(
        self,
        event: Event,
        conn: Conn,
        amount: int,
        feerate: int = 253,
        expect_fail: bool = False,
    ) -> None:
        """
        event       - the event which cause this, for error logging
        conn        - which conn (i.e. peer) to fund.
        amount      - amount to fund the channel with
        feerate     - feerate, in kiloweights
        expect_fail - true if this command is expected to error/fail
        """
        self.logger.debug("fffund")
        time.sleep(5)
        # First, check that another fundchannel isn't already running
        if self.fundchannel_future:
            if not self.fundchannel_future.done():
                raise RuntimeError(
                    "{} called fundchannel while another channel funding (fundchannel/init_rbf) is still in process".format(
                        event
                    )
                )
            self.fundchannel_future = None

        def _fundchannel(
            runner: Runner,
            conn: Conn,
            amount: int,
            feerate: int,
            expect_fail: bool = False,
        ) -> str:

            self.logger.debug("___fund")
            peer_id = conn.pubkey.format().hex()
            st = bytes(
                "openchannel_test {} {} --public\n".format(peer_id, amount), "utf-8"
            )
            self.proc.stdin.write(st)
            self.proc.stdin.flush()
            self.logger.debug("{}".format(self.proc.stdout.readline().decode("utf-8")))
            self.logger.debug("{}".format(self.proc.stdout.readline().decode("utf-8")))

        def _done(fut: Any) -> None:

            self.logger.debug("done")
            exception = fut.exception(0)
            if exception and not self.is_fundchannel_kill and not expect_fail:
                raise exception
            self.fundchannel_future = None
            self.is_fundchannel_kill = False
            self.cleanup_callbacks.remove(self.kill_fundchannel)

        fut = self.executor.submit(
            _fundchannel, self, conn, amount, feerate, expect_fail
        )
        fut.add_done_callback(_done)
        self.fundchannel_future = fut
        self.cleanup_callbacks.append(self.kill_fundchannel)

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
        self.logger.debug("init rbf")

    def invoice(self, event: Event, amount: int, preimage: str) -> None:
        self.logger.debug("invoice")

    def accept_add_fund(self, event: Event) -> None:
        self.logger.debug("aaf")

    def addhtlc(self, event: Event, conn: Conn, amount: int, preimage: str) -> None:
        self.logger.debug("addhtlc")

    def get_output_message(
        self, conn: Conn, event: Event, timeout: int = TIMEOUT
    ) -> Optional[bytes]:
        self.logger.debug("gom")
        fut = self.executor.submit(cast(LDKConn, conn).connection.read_message)
        try:
            return fut.result(timeout)
        except (futures.TimeoutError, ValueError):
            return None

    def check_error(self, event: Event, conn: Conn) -> Optional[str]:
        # We get errors in form of err msgs, always.
        self.logger.debug("check error")
        super().check_error(event, conn)
        msg = self.get_output_message(conn, event)
        if msg is None:
            return None
        return msg.hex()

    def check_final_error(
        self,
        event: Event,
        conn: Conn,
        expected: bool,
        must_not_events: List[MustNotMsg],
    ) -> None:
        self.logger.debug("check final errpr")
        if not expected:
            # Inject raw packet to ensure it hangs up *after* processing all previous ones.
            cast(LDKConn, conn).connection.connection.send(bytes(18))

            while True:
                binmsg = self.get_output_message(conn, event)
                if binmsg is None:
                    break
                for e in must_not_events:
                    if e.matches(binmsg):
                        raise EventError(
                            event, "Got msg banned by {}: {}".format(e, binmsg.hex())
                        )

                # Don't assume it's a message type we know!
                msgtype = struct.unpack(">H", binmsg[:2])[0]
                if msgtype == namespace().get_msgtype("error").number:
                    raise EventError(event, "Got error msg: {}".format(binmsg.hex()))

        cast(LDKConn, conn).connection.connection.close()

    def expect_tx(self, event: Event, txid: str) -> None:
        self.logger.debug("expect tx")
        # Ah bitcoin endianness...
        revtxid = bitcoin.core.lx(txid).hex()

        # This txid should appear in the mempool.
        try:
            wait_for(lambda: revtxid in self.bitcoind.rpc.getrawmempool())
        except ValueError:
            raise EventError(
                event,
                "Did not broadcast the txid {}, just {}".format(
                    revtxid,
                    [
                        (txid, self.bitcoind.rpc.getrawtransaction(txid))
                        for txid in self.bitcoind.rpc.getrawmempool()
                    ],
                ),
            )

    def has_option(self, optname: str) -> Optional[str]:
        """Returns None if it doesn't support, otherwise 'even' or 'odd' (required or supported)"""
        if optname in self.options:
            return self.options[optname]
        return None

    def add_startup_flag(self, flag: str) -> None:
        if self.config.getoption("verbose"):
            print("[ADD STARTUP FLAG '{}']".format(flag))
        self.startup_flags.append("--{}".format(flag))

    def close_channel(self, channel_id: str) -> bool:
        st = bytes("closechannel {}\n".format(channel_id), "utf-8")
        self.proc.stdin.write(st)
        self.proc.stdin.flush()
        self.logger.debug("{}".format(self.proc.stdout.readline().decode("utf-8")))

        self.logger.debug("close")

    def runner_features(
        self, additional_features: Optional[List[int]] = None, globals: bool = False
    ) -> str:
        if additional_features is None:
            if globals:
                return ""
            else:
                return bitfield(8, 12, 14)
        else:
            if globals:
                return bitfield(*(additional_features))
            else:
                return bitfield(*(additional_features + list((8, 12, 14))))
