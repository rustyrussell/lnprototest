# Adding New Tests, Testing New Nodes

The most common thing to do is to add a new test for a new feature.

## Adding A New Test

To add a new test, simply add a file starting with `test_` to the
tests/ directory.  Every function in this file starting with `test_`
will be run (the rest, presumably, are helpers you need).

For every test, there is a runner which wraps a particular node
implementation: using the default "DummyRunner" helps debug the tests
themselves.

A test consists of one or more Event (e.g. send a message, receive a
message), in a DAG.  The test runner repeats the test until every
Event has been covered.  The most important event is probably
TryAll(), which gives multiple alternative paths of Events, each of
which should be tried (it will try the "most Events" path first, to
try to get maximum coverage early in testing).

Tests which don't have an ExpectError event have a check at the end to
make sure no errors occurred.

## Using ExpectMsg Events

`ExpectMsg` matches a (perhaps only partially defined) message, then
calls its `if_match` function which can do more fine-grained matching.
For example, it could check that a specific field is not specified, or
a specific bit is set, etc.  There's also `ignore` which is a list
of Message to ignore: it defaults to common gossip queries.

`ExpectMsg` also stores the received fields in the runner's `stash`:
the convenient `rcvd` function can be used to access them for use in
`Msg` fields.


## Creating New Event Types

For various special effects, you might want to create a new Event
subclass.

Events are constructed once, but then their `action` method is called
in multiple orders for multiple traverses: they can store state across
runs in the `runner` using its `add_stash()` and `get_stash()`
methods, as used by `ExpectMsg` and `Msg`.  The entire stash
is emptied upon restart.


## Test Checklist

1. Did you quote the part of the BOLT you are testing?  This is vital
   to make your tests readable, and to ensure they change with the
   spec.  `make check-quotes` will all the quotes (starting with `#
   BOLT #N:`) are correct based on the `../lightning-rfc` directory,
   or run `tools/check_quotes.py testfile`.  If you are creating tests
   for a specific (e.g. non-master) git revision, you can use `#
   BOLT-commitid #N:` and use `--include-commit=commitid` option for
   every commit id it should check.

2. Does your test check failures as well as successes?

3. Did you test something which wasn't clear in the spec?  Consider
   opening a PR or issue to add an explicit requirement.

4. Does it pass `make check-source` a.k.a. flake8 and mypy?

## Adding a New Runner

You can write a new runner for an implementation by inheriting from
the Runner class.  This runner could live in this repository or in
your implementation's repository: you can set it with
`--runner=modname.classname`.

This is harder than writing a new test, but ultimately far more
useful, as it expands the coverage of every new test.
