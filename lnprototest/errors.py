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

    @staticmethod
    def decode_hex_data(hex_data: str) -> str:
        """Decode hex data into readable text if possible"""
        try:
            # Try to decode as ASCII/UTF-8
            decoded = bytes.fromhex(hex_data).decode('utf-8', errors='replace')
            # If the decoded text is mostly readable, return it
            if all(ord(c) < 128 for c in decoded):
                return f" (decoded: {decoded})"
        except (ValueError, UnicodeDecodeError):
            pass
        return ""

    def __str__(self) -> str:
        # Look for hex data in the message and try to decode it
        parts = self.message.split('data=')
        if len(parts) > 1:
            hex_data = parts[1].split()[0]  # Get the hex data before any spaces
            decoded = self.decode_hex_data(hex_data)
            if decoded:
                self.message = self.message.replace(hex_data, f"{hex_data}{decoded}")
        
        return f"`{self.message}` on event {self.path_to_str()}"


class SpecFileError(Exception):
    """Error thrown when the specification file has an error"""

    def __init__(self, event: "Event", message: str):
        self.event = event
        self.message = message
