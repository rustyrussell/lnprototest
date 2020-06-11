#! /usr/bin/python3
# #### Dummy runner which you should replace with real one. ####
from .runner import Runner, Conn


class DummyRunner(Runner):
    def __init__(self, config):
        super().__init__(config)

    def _is_dummy(self):
        """The DummyRunner returns True here, as it can't do some things"""
        return True

    def start(self):
        pass

    def stop(self):
        pass

    def restart(self):
        super().restart()
        if self.config.getoption('verbose'):
            print("[RESTART]")
        self.blockheight = 102

    def connect(self, event, connprivkey):
        if self.config.getoption('verbose'):
            print("[CONNECT {} {}]".format(event, connprivkey))
        self.add_conn(Conn(connprivkey))

    def getblockheight(self):
        return self.blockheight

    def trim_blocks(self, newheight):
        if self.config.getoption('verbose'):
            print("[TRIMBLOCK TO HEIGHT {}]".format(newheight))
        self.blockheight = newheight

    def add_blocks(self, event, txs, n):
        if self.config.getoption('verbose'):
            print("[ADDBLOCKS {} WITH {} TXS]".format(n, len(txs)))
        self.blockheight += n

    def disconnect(self, event, conn):
        super().disconnect(event, conn)
        if self.config.getoption('verbose'):
            print("[DISCONNECT {}]".format(conn))

    def recv(self, event, conn, outbuf):
        if self.config.getoption('verbose'):
            print("[RECV {} {}]".format(event, outbuf.hex()))

    def fundchannel(self, event, conn, amount, txid, outnum, feerate):
        if self.config.getoption('verbose'):
            print("[FUNDCHANNEL TO {} for {} with UTXO {}/{} feerate {}]"
                  .format(conn, amount, txid, outnum, feerate))

    def invoice(self, event, amount, preimage):
        if self.config.getoption('verbose'):
            print("[INVOICE for {} with PREIMAGE {} {}]"
                  .format(amount, preimage))

    def addhtlc(self, event, conn, amount, preimage):
        if self.config.getoption('verbose'):
            print("[ADDHTLC TO {} for {} with PREIMAGE {} {}]"
                  .format(conn, amount, preimage))

    def setfee(self, conn, feerate):
        if self.config.getoption('verbose'):
            print("[SETFEE ON {} to {} {}]"
                  .format(conn, feerate))

    def get_output_message(self, conn):
        if self.config.getoption('verbose'):
            print("[GET_OUTPUT_MESSAGE {}]".format(conn))
        # return bytes.fromhex(input("{}? ".format(conn)))
        # event.py has a special hack for DummyRunner
        return None

    def expect_tx(self, event, txid):
        if self.config.getoption('verbose'):
            print("[EXPECT-TX {} {}]".format(txid.hex()))

    def check_error(self, event, conn):
        super().check_error(event, conn)
        if self.config.getoption('verbose'):
            print("[CHECK-ERROR {}]".format(event))
        return None

    def check_final_error(self, event, conn, expected):
        pass
