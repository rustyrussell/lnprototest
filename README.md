# lnprototest: a Testsuite for the Lightning Network Protocol

lnprototest is a set of test helpers written in Python3, designed to
make it easy to write new tests when you propose changes to the
lightning network protocol, as well as test existing implementations.

## Install requirements

To install the necessary dependences

```bash
pip3 install -r requirements.txt 
```

To install lnprototest

```bash
pip3 install -e .
```

Well, now we can run the test

## Running test

The simplest way to run is with the "dummy" runner:

	make check

Here are some other useful pytest options:

1. `-n8` to run 8-way parallel.
2. `-x` to stop on the first failure.
3. `--pdb` to enter the debugger on first failure.
4. `--trace` to enter the debugger on every test.
5. `-k foo` to only run tests with 'foo' in their name.
6. `tests/test_bolt1-01-init.py` to only run tests in that file.
7. `tests/test_bolt1-01-init.py::test_init` to only run that test.

### Running Against A Real Node.

The more useful way to run is to use an existing implementation.  So
far, c-lightning is supported.  You will need:

1. `bitcoind` installed, and in your path.
2. [`lightningd`](https://github.com/ElementsProject/lightning/) compiled with
   `--enable-developer`.  By default the source directory should be
   `../lightning` relative to this directory, otherwise use
   `export LIGHTNING_SRC=dirname`.
3. Install any python requirements by
   `pip3 install lnprototest/clightning/requirements.txt`.

Then you can run

	make check PYTEST_ARGS='--runner=lnprototest.clightning.Runner'

or directly:

    pytest --runner=lnprototest.clightning.Runner

# Further Work

If you want to write new tests or new backends, see [HACKING.md](HACKING.md).

Let's keep the sats flowing!

Rusty.
