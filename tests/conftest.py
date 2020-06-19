#! /usr/bin/python3
import pytest
import importlib
import lnprototest
import pyln.proto.message
from typing import Any, Generator, Callable


def pytest_addoption(parser: Any) -> None:
    parser.addoption("--runner", action="store", help="runner to use", default="lnprototest.DummyRunner")
    parser.addoption("--runner-args", action="append", help="parameters for runner to use", default=[])


@pytest.fixture()  # type: ignore
def runner(pytestconfig: Any) -> Any:
    parts = pytestconfig.getoption("runner").rpartition('.')
    return importlib.import_module(parts[0]).__dict__[parts[2]](pytestconfig)


@pytest.fixture()
def namespaceoverride(pytestconfig: Any) -> Generator[Callable[[pyln.proto.message.MessageNamespace], None], None, None]:
    """Use this if you want to override the event_namespace"""
    def _setter(newns: pyln.proto.message.MessageNamespace) -> None:
        lnprototest.event_namespace = newns

    yield _setter
    # Restore it
    lnprototest.event_namespace = lnprototest.peer_message_namespace()
