#! /usr/bin/python3
import pytest
import importlib
import lnprototest
from pyln.proto.message import MessageNamespace
from typing import Any, Callable, Generator, List


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


@pytest.fixture()
def with_proposal(pytestconfig: Any) -> Generator[Callable[[List[str]], None], None, None]:
    """Use this to add additional messages to the namespace
       Useful for testing proposed (but not yet merged) spec mods"""
    def _setter(proposal_csv: List[str]) -> None:
        lnprototest.assign_namespace(lnprototest.namespace() + MessageNamespace(proposal_csv))

    yield _setter

    # Restore it
    lnprototest.assign_namespace(lnprototest.peer_message_namespace())
