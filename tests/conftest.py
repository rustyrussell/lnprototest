#! /usr/bin/python3
import pytest
import importlib
from typing import Any


def pytest_addoption(parser: Any) -> None:
    parser.addoption("--runner", action="store", help="runner to use", default="lnprototest.DummyRunner")
    parser.addoption("--runner-args", action="append", help="parameters for runner to use", default=[])


@pytest.fixture()  # type: ignore
def runner(pytestconfig: Any) -> Any:
    parts = pytestconfig.getoption("runner").rpartition('.')
    return importlib.import_module(parts[0]).__dict__[parts[2]](pytestconfig)
