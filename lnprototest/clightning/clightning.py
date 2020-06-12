#! /usr/bin/python3
# This script exercises the c-lightning implementation

# Released by Rusty Russell under CC0:
# https://creativecommons.org/publicdomain/zero/1.0/

import hashlib
import pyln.client
import pyln.proto.wire
import os
import shutil
import subprocess
import tempfile
import lnprototest
import bitcoin.core
import struct

from concurrent import futures
from ephemeral_port_reserve import reserve
from pyln.testing.utils import wait_for, SimpleBitcoinProxy
from lnprototest import Event, EventError, SpecFileError, KeySet, Conn, event_namespace, MustNotMsg
from typing import Dict, Any, Callable, List, Optional, cast

TIMEOUT = int(os.getenv("TIMEOUT", "30"))
LIGHTNING_SRC = os.getenv("LIGHTNING_SRC", '../lightning/')


class Bitcoind(object):
    """Starts regtest bitcoind on an ephemeral port, and returns the RPC proxy"""
    def __init__(self, basedir: str):
        self.bitcoin_dir = os.path.join(basedir, "bitcoind")
        if not os.path.exists(self.bitcoin_dir):
            os.makedirs(self.bitcoin_dir)
        self.bitcoin_conf = os.path.join(self.bitcoin_dir, 'bitcoin.conf')
        self.cmd_line = [
            'bitcoind',
            '-datadir={}'.format(self.bitcoin_dir),
            '-server',
            '-regtest',
            '-logtimestamps',
            '-nolisten']
        self.port = reserve()
        print("Port is {}, dir is {}".format(self.port, self.bitcoin_dir))
        # For after 0.16.1 (eg. 3f398d7a17f136cd4a67998406ca41a124ae2966), this
        # needs its own [regtest] section.
        with open(self.bitcoin_conf, 'w') as f:
            f.write("regtest=1\n")
            f.write("rpcuser=rpcuser\n")
            f.write("rpcpassword=rpcpass\n")
            f.write("[regtest]\n")
            f.write("rpcport={}\n".format(self.port))
        self.rpc = SimpleBitcoinProxy(btc_conf_file=self.bitcoin_conf)

    def start(self) -> None:
        self.proc = subprocess.Popen(self.cmd_line, stdout=subprocess.PIPE)

        # Wait for it to startup.
        while b'Done loading' not in self.proc.stdout.readline():
            pass

        # Block #1.
        self.rpc.submitblock('0000002006226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f7b8705087f9bddd2777021d2a1dfefc2f1c5afa833b5c4ab00ccc8a556d04283f5a1095dffff7f200100000001020000000001010000000000000000000000000000000000000000000000000000000000000000ffffffff03510101ffffffff0200f2052a01000000160014751e76e8199196d454941c45d1b3a323f1433bd60000000000000000266a24aa21a9ede2f61c3f71d1defd3fa999dfa36953755c690689799962b48bebd836974e8cf90120000000000000000000000000000000000000000000000000000000000000000000000000')
        self.rpc.generatetoaddress(100, self.rpc.getnewaddress())

    def stop(self) -> None:
        self.proc.kill()

    def restart(self) -> None:
        # Only restart if we have to.
        if self.rpc.getblockcount() != 102 or self.rpc.getrawmempool() == []:
            self.stop()
            shutil.rmtree(os.path.join(self.bitcoin_dir, 'regtest'))
            self.start()


class CLightningConn(lnprototest.Conn):
    def __init__(self, connprivkey: str, port: int):
        super().__init__(connprivkey)
        # FIXME: pyln.proto.wire should just use coincurve PrivateKey!
        self.connection = pyln.proto.wire.connect(pyln.proto.wire.PrivateKey(bytes.fromhex(self.connprivkey.to_hex())),
                                                  # FIXME: Ask node for pubkey
                                                  pyln.proto.wire.PublicKey(bytes.fromhex("0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798")),
                                                  '127.0.0.1',
                                                  port)


class Runner(lnprototest.Runner):
    def __init__(self, config: Any):
        super().__init__(config)
        self.cleanup_callbacks: List[Callable[[], None]] = []
        self.fundchannel_future: Optional[Any] = None
        self.is_fundchannel_kill = False

        directory = tempfile.mkdtemp(prefix='lnprototest-clightning-')
        self.bitcoind = Bitcoind(directory)
        self.bitcoind.start()
        self.executor = futures.ThreadPoolExecutor(max_workers=20)

        self.lightning_dir = os.path.join(directory, "lightningd")
        if not os.path.exists(self.lightning_dir):
            os.makedirs(self.lightning_dir)
        self.lightning_port = reserve()

        self.startup_flags = []
        for flag in config.getoption("runner_args"):
            self.startup_flags.append("--{}".format(flag))

        opts = subprocess.run(['{}/lightningd/lightningd'.format(LIGHTNING_SRC),
                               '--list-features-only'],
                              stdout=subprocess.PIPE, check=True).stdout.decode('utf-8').splitlines()
        self.options: Dict[str, str] = {}
        for o in opts:
            k, v = o.split('/')
            self.options[k] = v

    def get_keyset(self) -> KeySet:
        return KeySet(revocation_base_secret='0000000000000000000000000000000000000000000000000000000000000011',
                      payment_base_secret='0000000000000000000000000000000000000000000000000000000000000012',
                      delayed_payment_base_secret='0000000000000000000000000000000000000000000000000000000000000013',
                      htlc_base_secret='0000000000000000000000000000000000000000000000000000000000000014',
                      shachain_seed='FF' * 32)

    def get_node_privkey(self) -> str:
        return '01'

    def get_node_bitcoinkey(self) -> str:
        return '0000000000000000000000000000000000000000000000000000000000000010'

    def start(self) -> None:
        self.proc = subprocess.Popen(['{}/lightningd/lightningd'.format(LIGHTNING_SRC),
                                      '--lightning-dir={}'.format(self.lightning_dir),
                                      '--funding-confirms=3',
                                      '--dev-force-tmp-channel-id=0000000000000000000000000000000000000000000000000000000000000000',
                                      '--dev-force-privkey=0000000000000000000000000000000000000000000000000000000000000001',
                                      '--dev-force-bip32-seed=0000000000000000000000000000000000000000000000000000000000000001',
                                      '--dev-force-channel-secrets=0000000000000000000000000000000000000000000000000000000000000010/0000000000000000000000000000000000000000000000000000000000000011/0000000000000000000000000000000000000000000000000000000000000012/0000000000000000000000000000000000000000000000000000000000000013/0000000000000000000000000000000000000000000000000000000000000014/FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF',
                                      '--dev-bitcoind-poll=1',
                                      '--dev-fast-gossip',
                                      '--dev-no-htlc-timeout',
                                      '--bind-addr=127.0.0.1:{}'.format(self.lightning_port),
                                      '--network=regtest',
                                      '--bitcoin-rpcuser=rpcuser',
                                      '--bitcoin-rpcpassword=rpcpass',
                                      '--bitcoin-rpcport={}'.format(self.bitcoind.port),
                                      '--log-level=debug',
                                      '--log-file=log']
                                     + self.startup_flags)
        self.rpc = pyln.client.LightningRpc(os.path.join(self.lightning_dir, "regtest", "lightning-rpc"))

        def node_ready(rpc: pyln.client.LightningRpc) -> bool:
            try:
                rpc.getinfo()
                return True
            except Exception:
                return False

        wait_for(lambda: node_ready(self.rpc))

        # Make sure that we see any funds that come to our wallet
        for i in range(5):
            self.rpc.newaddr()

    def kill_fundchannel(self) -> None:
        fut = self.fundchannel_future
        self.fundchannel_future = None
        self.is_fundchannel_kill = True
        if fut:
            try:
                fut.result(0)
            except SpecFileError:
                pass

    def shutdown(self) -> None:
        for cb in self.cleanup_callbacks:
            cb()

    def stop(self) -> None:
        for cb in self.cleanup_callbacks:
            cb()
        self.rpc.stop()
        self.bitcoind.stop()
        for c in self.conns.values():
            cast(CLightningConn, c).connection.connection.close()

    def connect(self, event: Event, connprivkey: str) -> None:
        self.add_conn(CLightningConn(connprivkey, self.lightning_port))

    def __enter__(self) -> 'Runner':
        self.start()
        return self

    def __exit__(self, type: Any, value: Any, tb: Any) -> None:
        self.stop()

    def restart(self) -> None:
        if self.config.getoption('verbose'):
            print("[RESTART]")
        for cb in self.cleanup_callbacks:
            cb()
        self.rpc.stop()
        self.bitcoind.restart()
        for c in self.conns.values():
            cast(CLightningConn, c).connection.connection.close()

        # Make a clean start
        os.remove(os.path.join(self.lightning_dir, "regtest", "gossip_store"))
        os.remove(os.path.join(self.lightning_dir, "regtest", "lightningd.sqlite3"))
        os.remove(os.path.join(self.lightning_dir, "regtest", "log"))
        super().restart()
        self.start()

    def getblockheight(self) -> int:
        return self.bitcoind.rpc.getblockcount()

    def trim_blocks(self, newheight: int) -> None:
        h = self.bitcoind.rpc.getblockhash(newheight + 1)
        self.bitcoind.rpc.invalidateblock(h)

    def add_blocks(self, event: Event, txs: List[str], n: int) -> None:
        for tx in txs:
            self.bitcoind.rpc.sendrawtransaction(tx)
        self.bitcoind.rpc.generatetoaddress(n, self.bitcoind.rpc.getnewaddress())

        wait_for(lambda: self.rpc.getinfo()['blockheight'] == self.getblockheight())

    def recv(self, event: Event, conn: Conn, outbuf: bytes) -> None:
        try:
            cast(CLightningConn, conn).connection.send_message(outbuf)
        except BrokenPipeError:
            # This happens when they've sent an error and closed; try
            # reading it to figure out what went wrong.
            fut = self.executor.submit(cast(CLightningConn, conn).connection.read_message)
            try:
                msg = fut.result(1)
            except futures.TimeoutError:
                msg = None
            if msg:
                raise EventError(event, "Connection closed after sending {}".format(msg.hex()))
            else:
                raise EventError(event, "Connection closed")

    def fundchannel(self,
                    event: Event,
                    conn: Conn,
                    amount: int) -> None:
        """
            event   - the event which cause this, for error logging
            conn    - which conn (i.e. peer) to fund.
            amount  - amount to fund the channel with
        """
        # First, check that another fundchannel isn't already running
        if self.fundchannel_future:
            if not self.fundchannel_future.done():
                raise RuntimeError("{} called fundchannel while another fundchannel is still in process".format(event))
            self.fundchannel_future = None

        def _fundchannel(runner: Runner, conn: Conn, amount: int) -> str:
            peer_id = conn.pubkey.format().hex()
            # Need to supply feerate here, since regtest cannot estimate fees
            return runner.rpc.fundchannel(peer_id, amount, feerate='253perkw')

        def _done(fut: Any) -> None:
            exception = fut.exception(0)
            if exception and not self.is_fundchannel_kill:
                raise(exception)
            self.fundchannel_future = None
            self.is_fundchannel_kill = False
            self.cleanup_callbacks.remove(self.kill_fundchannel)

        fut = self.executor.submit(_fundchannel, self, conn, amount)
        fut.add_done_callback(_done)
        self.fundchannel_future = fut
        self.cleanup_callbacks.append(self.kill_fundchannel)

    def invoice(self, event: Event, amount: int, preimage: str) -> None:
        self.rpc.invoice(msatoshi=amount,
                         label=str(event),
                         description='invoice from {}'.format(event),
                         preimage=preimage)

    def addhtlc(self, event: Event, conn: Conn,
                amount: int, preimage: str) -> None:
        payhash = hashlib.sha256(bytes.fromhex(preimage)).hexdigest()
        routestep = {
            'msatoshi': amount,
            'id': conn.pubkey.format().hex(),
            # We internally add one.
            'delay': 4,
            # We actually ignore this.
            'channel': '1x1x1'
        }
        self.rpc.sendpay([routestep], payhash)

    def get_output_message(self, conn: Conn, event: Event, timeout: int = TIMEOUT) -> Optional[bytes]:
        fut = self.executor.submit(cast(CLightningConn, conn).connection.read_message)
        try:
            return fut.result(timeout)
        except (futures.TimeoutError, ValueError):
            return None

    def check_error(self, event: Event, conn: Conn) -> Optional[str]:
        # We get errors in form of err msgs, always.
        super().check_error(event, conn)
        msg = self.get_output_message(conn, event)
        if msg is None:
            return None
        return msg.hex()

    def check_final_error(self, event: Event, conn: Conn, expected: bool, must_not_events: List[MustNotMsg]) -> None:
        if not expected:
            # Inject raw packet to ensure it hangs up *after* processing all previous ones.
            cast(CLightningConn, conn).connection.connection.send(bytes(18))

            while True:
                binmsg = self.get_output_message(conn, event)
                if binmsg is None:
                    break
                for e in must_not_events:
                    if e.matches(binmsg):
                        raise EventError(event, "Got msg banned by {}: {}"
                                         .format(e, binmsg.hex()))

                # Don't assume it's a message type we know!
                msgtype = struct.unpack('>H', binmsg[:2])[0]
                if msgtype == event_namespace.get_msgtype('error').number:
                    raise EventError(event, "Got error msg: {}"
                                     .format(binmsg.hex()))

        cast(CLightningConn, conn).connection.connection.close()

    def expect_tx(self, event: Event, txid: str) -> None:
        # Ah bitcoin endianness...
        revtxid = bitcoin.core.lx(txid).hex()

        # This txid should appear in the mempool.
        try:
            wait_for(lambda: revtxid in self.bitcoind.rpc.getrawmempool())
        except ValueError:
            raise EventError(event, "Did not broadcast the txid {}, just {}"
                             .format(revtxid, [(txid, self.bitcoind.rpc.getrawtransaction(txid)) for txid in self.bitcoind.rpc.getrawmempool()]))

    def has_option(self, optname: str) -> Optional[str]:
        """Returns None if it doesn't support, otherwise 'even' or 'odd' (required or supported)"""
        if optname in self.options:
            return self.options[optname]
        return None
