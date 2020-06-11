#! /usr/bin/python3
# #### Dummy runner which you should replace with real one. ####
from .runner import Runner, Conn
from .event import Event
from typing import List, Optional
from .keyset import KeySet


class DummyRunner(Runner):
    def __init__(self, config):
        super().__init__(config)
        self._fakerecvstash()

    def _is_dummy(self) -> bool:
        """The DummyRunner returns True here, as it can't do some things"""
        return True

    def _fakerecvstash(self):
        # We don't actually receive packets, so put typical values here
        # to make tests "work".
        self.add_stash('ExpectMsg', [('init', {'temporary_channel_id': "00" * 32,
                                               'features': '',
                                               'globalfeatures': ''})])

    def get_keyset(self) -> KeySet:
        return KeySet(funding_privkey='10',
                      revocation_base_secret='11',
                      payment_base_secret='12',
                      htlc_base_secret='14',
                      delayed_payment_base_secret='13',
                      shachain_seed='FF' * 32)

    def has_option(self, optname: str) -> bool:
        return False

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def restart(self) -> None:
        super().restart()
        self._fakerecvstash()
        if self.config.getoption('verbose'):
            print("[RESTART]")
        self.blockheight = 102

    def connect(self, event: Event, connprivkey: str) -> None:
        if self.config.getoption('verbose'):
            print("[CONNECT {} {}]".format(event, connprivkey))
        self.add_conn(Conn(connprivkey))

    def getblockheight(self) -> int:
        return self.blockheight

    def trim_blocks(self, newheight: int) -> None:
        if self.config.getoption('verbose'):
            print("[TRIMBLOCK TO HEIGHT {}]".format(newheight))
        self.blockheight = newheight

    def add_blocks(self, event: Event, txs: List[str], n: int) -> None:
        if self.config.getoption('verbose'):
            print("[ADDBLOCKS {} WITH {} TXS]".format(n, len(txs)))
        self.blockheight += n

    def disconnect(self, event: Event, conn: Conn) -> None:
        super().disconnect(event, conn)
        if self.config.getoption('verbose'):
            print("[DISCONNECT {}]".format(conn))

    def recv(self, event: Event, conn: Conn, outbuf: bytes) -> None:
        if self.config.getoption('verbose'):
            print("[RECV {} {}]".format(event, outbuf.hex()))

    def fundchannel(self,
                    event: Event,
                    conn: Conn,
                    amount: int) -> None:
        if self.config.getoption('verbose'):
            print("[FUNDCHANNEL TO {} for {}]"
                  .format(conn, amount))

    def invoice(self, event: Event, amount: int, preimage: str) -> None:
        if self.config.getoption('verbose'):
            print("[INVOICE for {} with PREIMAGE {}]"
                  .format(amount, preimage))

    def addhtlc(self, event: Event, conn: Conn,
                amount: int, preimage: str) -> None:
        if self.config.getoption('verbose'):
            print("[ADDHTLC TO {} for {} with PREIMAGE {}]"
                  .format(conn, amount, preimage))

    def get_output_message(self, conn: Conn) -> Optional[bytes]:
        if self.config.getoption('verbose'):
            print("[GET_OUTPUT_MESSAGE {}]".format(conn))
        # return bytes.fromhex(input("{}? ".format(conn)))
        # event.py has a special hack for DummyRunner
        return None

    def expect_tx(self, event: Event, txid: str) -> None:
        if self.config.getoption('verbose'):
            print("[EXPECT-TX {}]".format(txid))

    def check_error(self, event: Event, conn: Conn) -> Optional[str]:
        super().check_error(event, conn)
        if self.config.getoption('verbose'):
            print("[CHECK-ERROR {}]".format(event))
        return None

    def check_final_error(self, event: Event, conn: Conn, expected: bool) -> None:
        pass
