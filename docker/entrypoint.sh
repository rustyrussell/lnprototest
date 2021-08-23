#! /bin/bash
cd lnprototest
make check PYTEST_ARGS='--runner=lnprototest.clightning.Runner'