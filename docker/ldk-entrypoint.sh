#! /bin/bash
cd lnprototest || exit

for i in range{0..5};
do
  if poetry run make check PYTEST_ARGS="--runner=ldk_lnprototest.Runner -n8 --dist=loadfile --log-cli-level=DEBUG"; then
    echo "iteration $i succeeded"
  else
    echo "iteration $i failed"
    exit 1
  fi
done
