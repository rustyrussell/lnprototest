#! /usr/bin/python3


class EventError(Exception):
    """Error thrown when the runner fails in some way"""
    def __init__(self, event, message):
        self.eventpath = [event]
        self.message = message

    def add_path(self, event):
        self.eventpath = [event] + self.eventpath


class SpecFileError(Exception):
    """Error thrown when the specification file has an error"""
    def __init__(self, event, message):
        self.event = event
        self.message = message
