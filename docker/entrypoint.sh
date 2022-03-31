#! /bin/bash
cd lnprototest
make check PYTEST_ARGS='--runner=lnprototest.clightning.Runner -n4 --log-cli-level=DEBUG'