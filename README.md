# lnprototest: a Testsuite for the Lightning Network Protocol

lnprototest is a set of test helpers written in Python3, designed to
make it easy to write new tests when you propose changes to the
lightning network protocol, as well as test existing implementations.

The simplest way to run is with the "dummy" runner:

	make check

The more useful way to run is to use an existing implementation, such
as:

	make check PYTEST_ARGS='--runner=lnprototest.clightning.Runner'

or directly:

    pytest --runner=lnprototest.clightning.Runner

Here are some other useful pytest options:

1. `-n8` to run 8-way parallel.
2. `-x` to stop on the first failure.
3. `--pdb` to enter the debugger on first failure.
4. `--trace` to enter the debugger on every test.
5. `-k foo` to only run tests with 'foo' in their name.
6. `tests/test_bolt1-01-init.py` to only run tests in that file.
7. `tests/test_bolt1-01-init.py::test_init` to only run that test.

If you want to write new tests or new backends, see [HACKING.md](HACKING.md).

Let's keep the sats flowing!

Rusty.
