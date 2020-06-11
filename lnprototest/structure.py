#! /usr/bin/python3
import math
from .event import Event, ExpectMsg
from .errors import SpecFileError, EventError
from pyln.proto.message import Message
from typing import Union, List, Optional, TYPE_CHECKING, cast
if TYPE_CHECKING:
    # Otherwise a circular dependency
    from .runner import Runner, Conn

# These can all be fed to a Sequence() initializer.
SequenceUnion = Union['Sequence', List[Event], Event]


class Sequence(Event):
    """A sequence of ordered events"""
    def __init__(self,
                 events: Union['Sequence', List[Event], Event],
                 enable: bool = True):
        """Events can be a Sequence, a single Event, or a list of Events.  If
enable is False, this turns into a noop (e.g. if runner doesn't support
it)."""
        super().__init__()
        self.enable = enable
        if type(events) is Sequence:
            # mypy gets upset because Sequence isn't defined yet.
            self.events = events.events  # type: ignore
            self.enable = events.enable  # type: ignore
            self.name = events.name      # type: ignore
        elif isinstance(events, Event):
            self.events = [events]
        else:
            # Filter out any events which are not enabled
            self.events = [e for e in events if (not isinstance(e, Sequence)) or e.enable]

    def num_undone(self) -> int:
        return sum([e.num_undone() for e in self.events])

    def action(self, runner: 'Runner', skip_first: bool = False) -> None:
        super().action(runner)
        for e in self.events:
            if skip_first:
                skip_first = False
            else:
                e.action(runner)

    @staticmethod
    def match_which_sequence(runner: 'Runner', msg: Message, sequences: List['Sequence']) -> Optional['Sequence']:
        """Return which sequence expects this msg, or None"""
        # For DummyRunner, we always match
        if runner._is_dummy():
            return sequences[0]

        for s in sequences:
            failreason = cast(ExpectMsg, s.events[0]).message_match(msg)
        if failreason is None:
            return s

        return None


class OneOf(Event):
    """Event representing multiple possible sequences, one of which should happen"""
    def __init__(self, sequences: List[SequenceUnion]):
        super().__init__()
        self.sequences = []
        for s in sequences:
            seq = Sequence(s)
            if len(seq.events) == 0:
                raise ValueError("{} is an empty sequence".format(s))
            if seq.enable:
                self.sequences.append(seq)

    def num_undone(self) -> int:
        # Use mean, unless we're done.
        if self.done:
            return 0
        return math.ceil(sum([s.num_undone() for s in self.sequences]) / len(self.sequences))

    def action(self, runner: 'Runner') -> None:
        super().action(runner)

        # Check they all use the same conn!
        conn: Optional[Conn] = None
        for s in self.sequences:
            c = cast(ExpectMsg, s.events[0]).find_conn(runner)
            if conn is None:
                conn = c
            elif c != conn:
                raise SpecFileError(self, "sequences do not all use the same conn?")
        assert conn

        binmsg = runner.get_output_message(conn)
        if binmsg is None:
            # Dummyrunner never returns output, so pretend it worked.
            if runner._is_dummy():
                return self.sequences[0].action(runner, skip_first=True)
            raise EventError(self, "Did not receive a message from runner")

        seq = Sequence.match_which_sequence(runner, binmsg, self.sequences)
        if seq is not None:
            # We found the sequence, run it
            return seq.action(runner, skip_first=True)

        raise EventError(self,
                         "None of the sequences matched {}".format(binmsg.hex()))


class AnyOrder(Event):
    """Event representing multiple sequences, all of which should happen, but not defined which order they would happen"""
    def __init__(self, sequences: List[SequenceUnion]):
        super().__init__()
        self.sequences = []
        for s in sequences:
            seq = Sequence(s)
            if len(seq.events) == 0:
                raise ValueError("{} is an empty sequence".format(s))
            if seq.enable:
                self.sequences.append(seq)

    def num_undone(self) -> int:
        # Use total, unless we're done.
        if self.done:
            return 0
        return sum([s.num_undone() for s in self.sequences])

    def action(self, runner: 'Runner') -> None:
        super().action(runner)

        # Check they all use the same conn!
        conn = None
        for s in self.sequences:
            c = cast(ExpectMsg, s.events[0]).find_conn(runner)
            if conn is None:
                conn = c
            elif c != conn:
                raise SpecFileError(self, "sequences do not all use the same conn?")
        assert conn

        # Get message, but leave it in the queue for real sequence.
        binmsg = runner.get_output_message(conn)
        if binmsg is None:
            # Dummyrunner never returns output, so pretend it worked.
            if runner._is_dummy():
                binmsg = bytes()
            raise EventError(self, "Did not receive a message from runner")

        sequences = self.sequences[:]
        while sequences != []:
            seq = Sequence.match_which_sequence(runner, binmsg, self.sequences)
            if seq is not None:
                sequences.remove(seq)
                seq.action(runner, skip_first=True)
            else:
                raise EventError(self,
                                 "None of the sequences matched {}"
                                 .format(binmsg.hex()))


class TryAll(Event):
    """Event representing multiple sequences, each of which should be tested"""
    def __init__(self, sequences: List[SequenceUnion]):
        super().__init__()
        self.sequences = []
        for s in sequences:
            seq = Sequence(s)
            if seq.enable:
                self.sequences.append(seq)

    def num_undone(self) -> int:
        return sum([s.num_undone() for s in self.sequences])

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        # Use least-done one, or first if all done.
        best = self.sequences[0]
        for s in self.sequences[1:]:
            if s.num_undone() > best.num_undone():
                best = s

        best.action(runner)
