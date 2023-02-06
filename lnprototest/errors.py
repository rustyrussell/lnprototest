from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .event import Event


class EventError(Exception):
    """Error thrown when the runner fails in some way"""

    def __init__(self, event: "Event", message: str):
        self.eventpath = [event]
        self.message = message

    def add_path(self, event: "Event") -> None:
        self.eventpath = [event] + self.eventpath

    def path_to_str(self) -> str:
        result = "["
        for event in self.eventpath:
            result += f"{event},"
        return f"{result}]"

    def __str__(self) -> str:
        return f"`{self.message}` on event {self.path_to_str()}"


class SpecFileError(Exception):
    """Error thrown when the specification file has an error"""

    def __init__(self, event: "Event", message: str):
        self.event = event
        self.message = message
