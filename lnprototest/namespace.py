#! /usr/bin/python3
import pyln.spec.bolt1
import pyln.spec.bolt2
import pyln.spec.bolt7
from pyln.proto.message import MessageNamespace
from .signature import SigType


def peer_message_namespace() -> MessageNamespace:
    """Namespace containing all the peer messages"""
    ns = MessageNamespace()
    # We replace the fundamental signature type with our custom type,
    # then we load in all the csv files so they use it.
    ns.fundamentaltypes['signature'] = SigType()

    ns.load_csv(pyln.spec.bolt1.csv
                + pyln.spec.bolt2.csv
                + pyln.spec.bolt7.csv)
    return ns


# By default, include all peer message bolts
event_namespace = peer_message_namespace()
