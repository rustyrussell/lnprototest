#! /usr/bin/python3
import pytest
import importlib
import lnprototest
from pyln.proto.message import MessageNamespace
from typing import Any, Callable, Generator


def pytest_addoption(parser: Any) -> None:
    parser.addoption("--runner", action="store", help="runner to use", default="lnprototest.DummyRunner")
    parser.addoption("--runner-args", action="append", help="parameters for runner to use", default=[])


@pytest.fixture()  # type: ignore
def runner(pytestconfig: Any) -> Any:
    parts = pytestconfig.getoption("runner").rpartition('.')
    return importlib.import_module(parts[0]).__dict__[parts[2]](pytestconfig)


@pytest.fixture()
def namespaceoverride(pytestconfig: Any) -> Generator[Callable[[MessageNamespace], None], None, None]:
    """Use this if you want to override the message namespace"""
    def _setter(newns: MessageNamespace) -> None:
        lnprototest.assign_namespace(newns)

    yield _setter
    # Restore it
    lnprototest.assign_namespace(lnprototest.peer_message_namespace())
