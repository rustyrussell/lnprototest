import pytest
import lnprototest
import pyln.proto.message
from typing import Any, Generator, Callable


def _setter(newns: pyln.proto.message.MessageNamespace) -> None:
    lnprototest.event_namespace = newns


@pytest.fixture()
def namespaceoverride(pytestconfig: Any) -> Generator[Callable[[pyln.proto.message.MessageNamespace], None], None, None]:
    """Use this if you want to override the event_namespace"""
    yield _setter
    # Restore it
    lnprototest.event_namespace = lnprototest.peer_message_namespace()
