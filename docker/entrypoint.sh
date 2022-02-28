#! /bin/bash
cd lnprototest
poetry shell
make check PYTEST_ARGS='--runner=lnprototest.clightning.Runner'