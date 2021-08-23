#! /bin/bash

make check PYTEST_ARGS=PYTEST_ARGS='--runner=lnprototest.clightning.Runner'