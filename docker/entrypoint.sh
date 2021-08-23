#! /bin/bash

PYTEST_ARGS=''
if [ -z "$CLIGHTNING_ENABLED" ]; then PYTEST_ARGS='--runner=lnprototest.clightning.Runner'; fi

make check PYTEST_ARGS=$PYTEST_ARGS