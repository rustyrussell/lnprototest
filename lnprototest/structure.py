#! /usr/bin/python3
from .event import Event
from .errors import SpecFileError, EventError


class Sequence(Event):
    """A sequence of ordered events"""
    def __init__(self, events):
        """Events can be a Sequence, a single Event, or a list of Events"""
        super().__init__()
        if type(events) is Sequence:
            self.events = events.events
        elif isinstance(events, Event):
            self.events = [events]
        else:
            self.events = events

    def num_undone(self):
        return sum([e.num_undone() for e in self.events])

    def action(self, runner):
        super().action(runner)
        for e in self.events:
            e.action(runner)

    @staticmethod
    def match_which_sequence(runner, msg, sequences):
        """Return which sequence expects this msg, or None"""
        # For DummyRunner, we always match
        if runner._is_dummy():
            return sequences[0]

        for s in sequences:
            failreason = s.events[0].message_match(msg)
        if failreason is None:
            return s

        return None


class OneOf(Event):
    """Event representing multiple possible sequences, one of which should happen"""
    def __init__(self, sequences=[]):
        super().__init__()
        self.sequences = []
        for s in sequences:
            seq = Sequence(s)
            if len(seq.events) == 0:
                raise ValueError("{} is an empty sequence".format(s))
            self.sequences.append(seq)

    def num_undone(self):
        # Use mean, unless we're done.
        if self.done:
            return 0
        return sum([s.num_undone() for s in self.sequences]) / len(self.sequences)

    def action(self, runner):
        super().action(runner)

        # Check they all use the same conn!
        conn = None
        for s in self.sequences:
            c = s.events[0].find_conn()
            if conn is None:
                c = conn
            elif c != conn:
                raise SpecFileError(self, "sequences do not all use the same conn?")

        # Get message, but leave it in the queue for real sequence.
        msg = runner.peek_output_msg(self, conn)

        s = Sequence.match_which_sequence(runner, msg, self.sequences)
        if s is not None:
            # We found the sequence, run it
            return s.action(runner)

        raise EventError(self,
                         "None of the sequences matched {}".format(msg.hex()))


class AnyOrder(Event):
    """Event representing multiple sequences, all of which should happen, but not defined which order they would happen"""
    def __init__(self, sequences=[]):
        super().__init__()
        self.sequences = []
        for s in sequences:
            seq = Sequence(s)
            if len(seq.events) == 0:
                raise ValueError("{} is an empty sequence".format(s))
            self.sequences.append(seq)

    def num_undone(self):
        # Use total, unless we're done.
        if self.done:
            return 0
        return sum([s.num_undone() for s in self.sequences])

    def action(self, runner):
        super().action(runner)
        if runner.args.verbose:
            print("# running {}".format(self))

        # Check they all use the same conn!
        conn = None
        for s in self.sequences:
            c = s.events[0].find_conn()
            if conn is None:
                c = conn
            elif c != conn:
                raise SpecFileError(self, "sequences do not all use the same conn?")

        # Get message, but leave it in the queue for real sequence.
        msg = runner.peek_output_msg(self, conn)

        sequences = self.sequences[:]
        while sequences != []:
            s = Sequence.match_which_sequence(runner, msg, self.sequences)
            if s is not None:
                sequences.remove(s)
                s.action(runner)
            else:
                raise EventError(self,
                                 "None of the sequences matched {}"
                                 .format(msg.hex()))


class TryAll(Event):
    """Event representing multiple sequences, each of which should be tested"""
    def __init__(self, sequences=[]):
        super().__init__()
        self.sequences = []
        for s in sequences:
            self.sequences.append(Sequence(s))

    def num_undone(self):
        return sum([s.num_undone() for s in self.sequences])

    def action(self, runner):
        super().action(runner)
        # Use least-done one, or first if all done.
        best = self.sequences[0]
        for s in self.sequences[1:]:
            if s.num_undone() > best.num_undone():
                best = s

        best.action(runner)
