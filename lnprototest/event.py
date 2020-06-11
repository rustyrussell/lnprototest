#! /usr/bin/python3
import traceback
from pyln.proto.message import SubtypeType, Message
import string
import os.path
import io
from .errors import SpecFileError, EventError


def check_hex(val, digits):
    if not all(c in string.hexdigits for c in val):
        raise ValueError("{} is not valid hex".format(val))
    if len(val) != digits:
        raise ValueError("{} not {} characters long".format(val, digits))
    return val


class Event(object):
    """Abstract base class for events."""
    def __init__(self):
        # From help(traceback.extract_stack):
        #   Each item in the list is a quadruple (filename,
        #   line number, function name, text), and the entries are in order
        #   from oldest to newest stack frame.
        self.name = 'unknown'
        for s in reversed(traceback.extract_stack()):
            # Ignore constructor calls, like this one.
            if s[2] != '__init__':
                self.name = "{}:{}:{}".format(type(self).__name__,
                                              os.path.basename(s[0]), s[1])
                break
        self.done = False

    def action(self, runner):
        if runner.config.getoption('verbose'):
            print("# running {}:".format(self))
        self.done = True

    def num_undone(self):
        """Number of actions to be done in this event; usually 1."""
        if self.done:
            return 0
        return 1

    def find_conn(self, runner):
        """Helper for events which have a connection"""
        conn = runner.find_conn(self.connprivkey)
        if conn is None:
            if self.connprivkey is None:
                # None means "same as last used/created"
                raise SpecFileError(self, "No current connection")
            else:
                raise SpecFileError(self, "Unknown connection {}".format(self.connprivkey))
        return conn

    def __repr__(self):
        return self.name


class Connect(Event):
    """Connect to the runner, as if a node with private key connprivkey"""
    def __init__(self, connprivkey):
        super().__init__()
        self.connprivkey = connprivkey

    def action(self, runner):
        super().action(runner)
        if runner.find_conn(self.connprivkey):
            raise SpecFileError(self, "Already have connection to {}"
                                .format(self.connprivkey))
        runner.connect(self, self.connprivkey)


class Disconnect(Event):
    """Disconnect the runner from the node whose private key is connprivkey: default is last connection specified"""
    def __init__(self, connprivkey=None):
        super().__init__()
        self.connprivkey = connprivkey

    def action(self, runner):
        super().action(runner)
        runner.disconnect(self, self.find_conn(runner))


class Msg(Event):
    """Feed a message to the runner (via optional given connection)"""
    def __init__(self, message, connprivkey=None):
        super().__init__()
        self.message = message
        self.connprivkey = connprivkey

    def action(self, runner):
        super().action(runner)
        binmsg = io.BytesIO()
        self.message.write(binmsg)
        runner.recv(self, self.find_conn(runner), binmsg.getvalue())


class ExpectMsg(Event):
    """Wait for a message from the runner.

partmessage is the (usually incomplete) message which it should match.
if_match is the function to call if it matches: should raise an
exception if it's not satisfied.  if_nomatch is the function to all if
it doesn't match: if this returns the message is ignored and we wait
for a new one.

    """
    def _default_if_match(self, msg):
        pass

    def _default_if_nomatch(self, binmsg, errstr):
        raise EventError(self, "Runner gave bad msg {}: {}".format(binmsg, errstr))

    def __init__(self, namespace, partmessage, if_match=_default_if_match, if_nomatch=_default_if_nomatch, connprivkey=None):
        super().__init__()
        self.namespace = namespace
        self.partmessage = partmessage
        self.if_match = if_match
        self.if_nomatch = if_nomatch
        self.connprivkey = connprivkey

    # FIXME: Put helper in Message?
    @staticmethod
    def _cmp_msg(subtype, fieldsa, fieldsb, prefix=""):
        """a is a subset of b"""
        for f in fieldsa:
            if f not in fieldsb:
                return "Missing field {}".format(prefix + f)
            fieldtype = subtype.find_field(f)
            if isinstance(fieldtype, SubtypeType):
                ret = ExpectMsg._cmp_msg(fieldtype, fieldsa[f], fieldsb[f],
                                         prefix + f + ".")
                if ret:
                    return ret
            else:
                if fieldsa[f] != fieldsb[f]:
                    return "Field {}: {} != {}".format(f,
                                                       fieldtype.fieldtype.val_to_str(fieldsb[f], fieldsb),
                                                       fieldtype.fieldtype.val_to_str(fieldsa[f], fieldsa))
        return None

    def message_match(self, msg):
        """Does this message match what we expect?"""
        if msg.messagetype != self.partmessage.messagetype:
            return "Expected {}, got {}".format(self.partmessage.messagetype,
                                                msg.messagetype)
        return self._cmp_msg(msg.messagetype, self.partmessage.fields, msg.fields)

    def action(self, runner):
        super().action(runner)
        while True:
            binmsg = runner.get_output_message(self.find_conn(runner))
            if binmsg is None:
                # Dummyrunner never returns output, so pretend it worked.
                if runner._is_dummy():
                    return
                raise EventError(self, "Did not receive a message from runner")

            # Might be completely unknown to namespace.
            try:
                msg = Message.read(self.namespace, io.BytesIO(binmsg))
            except ValueError as ve:
                self.if_nomatch(self, binmsg, str(ve))
                continue

            err = self.message_match(msg)
            if err:
                self.if_nomatch(self, binmsg, err)
                # If that returns, it means we try again.
                continue

            self.if_match(self, msg)
            break


class Block(Event):
    """Generate a block, at blockheight, with optional txs.

    """
    def __init__(self, blockheight, number=1, txs=[]):
        super().__init__()
        self.blockheight = blockheight
        self.number = number
        self.txs = txs

    def action(self, runner):
        super().action(runner)
        # Oops, did they ask us to produce a block with no predecessor?
        if runner.getblockheight() + 1 < self.blockheight:
            raise SpecFileError(self, "Cannot generate block #{} at height {}".
                                format(self.blockheight, runner.getblockheight()))

        # Throw away blocks we're replacing.
        if runner.getblockheight() >= self.blockheight:
            runner.trim_blocks(self.blockheight - 1)

        # Add new one
        runner.add_blocks(self, self.txs, self.number)
        assert runner.getblockheight() == self.blockheight - 1 + self.number


class ExpectTx(Event):
    """Expect the runner to broadcast a transaction

    """
    def __init__(self, txid):
        super().__init__()
        self.txid = txid

    def action(self, runner):
        super().action(runner)
        runner.expect_tx(self, self.txid)


class FundChannel(Event):
    """Tell the runner to fund a channel with this peer."""
    def __init__(self, amount, utxo, feerate, connprivkey=None):
        super().__init__()
        self.connprivkey = connprivkey
        self.amount = amount
        parts = utxo.partition('/')
        self.utxo = (check_hex(parts[0], 64), int(parts[2]))
        self.feerate = feerate

    def action(self, runner):
        super().action(runner)
        runner.fundchannel(self,
                           self.find_conn(runner),
                           self.amount, self.utxo[0],
                           self.utxo[1], self.feerate)


class Invoice(Event):
    def __init__(self, amount, preimage):
        super().__init__()
        self.preimage = check_hex(preimage, 64)
        self.amount = amount

    def action(self, runner):
        super().action(runner)
        runner.invoice(self, self.amount, self.preimage)


class AddHtlc(Event):
    def __init__(self, amount, preimage, connprivkey=None):
        super().__init__()
        self.connprivkey = connprivkey
        self.preimage = check_hex(preimage, 64)
        self.amount = amount

    def action(self, runner):
        super().action(runner)
        runner.addhtlc(self, self.find_conn(runner),
                       self.amount, self.preimage)


class SetFeeEvent(Event):
    def __init__(self, feerate, connprivkey=None):
        super().__init__()
        self.connprivkey = connprivkey
        self.feerate = feerate

    def action(self, runner):
        super().action(runner)
        runner.setfee(self, self.find_conn(runner), self.feerate)


class ExpectError(Event):
    def __init__(self, connprivkey=None):
        super().__init__()
        self.connprivkey = connprivkey

    def action(self, runner):
        super().action(runner)
        error = runner.check_error(self, self.find_conn(runner))
        if error is None:
            # We ignore lack of responses from dummyrunner
            if not runner._is_dummy():
                raise EventError(self, "No error found")
