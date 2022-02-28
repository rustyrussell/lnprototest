#! /usr/bin/env python3
# Integration testing on closing a channel

from lnprototest import (
    Runner,
)

# +-------+                              +-------+
# |       |--(1)-----  shutdown  ------->|       |
# |       |<-(2)-----  shutdown  --------|       |
# |       |                              |       |
# |       | <complete all pending HTLCs> |       |
# |   A   |                 ...          |   B   |
# |       |                              |       |
# |       |--(3)-- closing_signed  F1--->|       |
# |       |<-(4)-- closing_signed  F2----|       |
# |       |              ...             |       |
# |       |--(?)-- closing_signed  Fn--->|       |
# |       |<-(?)-- closing_signed  Fn----|       |
# +-------+                              +-------+


def test_init_shoutdown(runner: Runner) -> None:
    pass
