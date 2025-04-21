<div align="center">
  <h1>lnprototest</h1>
  <p>
    <strong>a Testsuite for the Lightning Network Protocol</strong>
  </p>
  <h4>
    <a href="https://github.com/rustyrussell/lnprototest">Project Homepage</a>
  </h4>
 
  <a href="https://github.com/rustyrussell/lnprototest/actions">
    <img alt="GitHub Workflow Status (branch)" src="https://img.shields.io/github/workflow/status/rustyrussell/lnprototest/Integration%20testing/master?style=flat-square"/>
  </a>
  
  <a href="https://github.com/vincenzopalazzo/lnprototest/blob/vincenzopalazzo/styles/HACKING.md">
    <img src="https://img.shields.io/badge/doc-hacking-orange?style=flat-square" />
  </a>
</div>

lnprototest is a set of test helpers written in Python3, designed to make it easy to write new tests when you propose changes to the lightning network protocol, as well as test existing implementations.

## Install requirements

To install the necessary dependencies:

```bash
# Create a virtual environment (recommended to avoid system package conflicts)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip3 install poetry
poetry shell
poetry install
```

## Running test

The simplest way to run is with the "dummy" runner:

```bash
make check
```

Here are some other useful pytest options:
1. `-n8` to run 8-way parallel.
2. `-x` to stop on the first failure.
3. `--pdb` to enter the debugger on first failure.
4. `--trace` to enter the debugger on every test.
5. `-k foo` to only run tests with 'foo' in their name.
6. `tests/test_bolt1-01-init.py` to only run tests in that file.
7. `tests/test_bolt1-01-init.py::test_init` to only run that test.
8. `--log-cli-level={LEVEL_NAME}` to enable the logging during the test execution.

## Using Docker (Alternative Setup)

The project supports Docker for an easier setup:

```bash
cd docker
docker-compose up
```

### Running Against A Real Node.

The more useful way to run is to use an existing implementation. So far, core-lightning is supported. You will need:

1. `bitcoind` installed, and in your path.
2. [`lightningd`](https://github.com/ElementsProject/lightning/) compiled with `--enable-debugbuild` (Note: not `--enable-developer` as that flag has been renamed). By default the source directory should be `../lightning` relative to this directory, otherwise use `export LIGHTNING_SRC=dirname`.
3. Install any python requirements by `pip3 install -r lnprototest/clightning/requirements.txt`.

Then you can run:

```bash
make check PYTEST_ARGS='--runner=lnprototest.clightning.Runner'
```

or directly:

```bash
pytest --runner=lnprototest.clightning.Runner
```

## Troubleshooting

If you see an "externally-managed-environment" error, make sure to use a virtual environment as shown in the installation steps.

# Further Work

If you want to write new tests or new backends, see [HACKING.md](HACKING.md).

Let's keep the sats flowing!
Rusty.
