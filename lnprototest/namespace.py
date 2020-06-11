#! /usr/bin/python3
import pyln.proto.message.bolt1
import pyln.proto.message.bolt2
import pyln.proto.message.bolt7


def peer_message_namespace():
    """Namespace containing all the peer messages"""
    return (pyln.proto.message.bolt1.namespace
            + pyln.proto.message.bolt2.namespace
            + pyln.proto.message.bolt7.namespace)


# By default, include all peer message bolts
event_namespace = peer_message_namespace()
