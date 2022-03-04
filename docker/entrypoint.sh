#! /bin/bash
cd lnprototest
make check PYTEST_ARGS='--runner=lnprototest.clightning.Runner --log-cli-level=DEBUG'