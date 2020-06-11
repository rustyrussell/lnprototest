import pytest
import lnprototest
import pyln.proto.message


def _setter(newns: pyln.proto.message.MessageNamespace):
    lnprototest.event_namespace = newns


@pytest.fixture()
def namespaceoverride(pytestconfig):
    """Use this if you want to override the event_namespace"""
    yield _setter
    # Restore it
    lnprototest.event_namespace = lnprototest.peer_message_namespace()
