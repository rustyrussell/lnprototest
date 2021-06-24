#! /usr/bin/python3
# This script exercises the c-lightning implementation

# Released by Rusty Russell under CC0:
# https://creativecommons.org/publicdomain/zero/1.0/

import os
import shutil
import subprocess
import logging

from ephemeral_port_reserve import reserve
from pyln.testing.utils import SimpleBitcoinProxy
from .backend import Backend


class Bitcoind(Backend):
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
        self.btc_version = None
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

    def version_compatibility(self) -> None:
        """
        This method try to manage the compatibility between
        different version of Bitcoin Core implementation.

        This method could be useful sometimes when is necessary
        run the test with different version of Bitcoin core.
        """
        if self.rpc is None:
            # Sanity check
            raise ValueError("bitcoind not initialized")

        self.btc_version = self.rpc.getnetworkinfo()['version']
        assert self.btc_version is not None
        logging.info("Bitcoin Core version {}".format(self.btc_version))
        if self.btc_version >= 210000:
            # Maintains the compatibility between wallet
            # different ln implementation can use the main wallet (?)
            self.rpc.createwallet("main")  # Automatically loads

    def start(self) -> None:
        self.proc = subprocess.Popen(self.cmd_line, stdout=subprocess.PIPE)
        assert self.proc.stdout

        # Wait for it to startup.
        while b'Done loading' not in self.proc.stdout.readline():
            pass

        self.version_compatibility()
        # Block #1.
        # Privkey the coinbase spends to:
        #    cUB4V7VCk6mX32981TWviQVLkj3pa2zBcXrjMZ9QwaZB5Kojhp59
        self.rpc.submitblock('0000002006226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f84591a56720aabc8023cecf71801c5e0f9d049d0c550ab42412ad12a67d89f3a3dbb6c60ffff7f200400000001020000000001010000000000000000000000000000000000000000000000000000000000000000ffffffff03510101ffffffff0200f2052a0100000016001419f5016f07fe815f611df3a2a0802dbd74e634c40000000000000000266a24aa21a9ede2f61c3f71d1defd3fa999dfa36953755c690689799962b48bebd836974e8cf90120000000000000000000000000000000000000000000000000000000000000000000000000')
        self.rpc.generatetoaddress(100, self.rpc.getnewaddress())

    def stop(self) -> None:
        self.proc.kill()

    def restart(self) -> None:
        # Only restart if we have to.
        if self.rpc.getblockcount() != 102 or self.rpc.getrawmempool() == []:
            self.stop()
            shutil.rmtree(os.path.join(self.bitcoin_dir, 'regtest'))
            self.start()
