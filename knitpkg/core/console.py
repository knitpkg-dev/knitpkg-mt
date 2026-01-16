from typing import Optional, Protocol, Any

class Console(Protocol):
    """Abstract interface for console output."""
    def print(self, *objects: Any) -> None:
        ...

    def log(self, *objects: Any) -> None:
        ...

class ConsoleAware:
    """Base class for classes that need console output functionality."""
    def __init__(self, console: Optional[Console] = None, verbose: bool = False):
        self.console = console
        self.verbose = verbose

    def print(self, msg: str) -> None:
        if self.console:
            self.console.print(msg)

    def log(self, msg: str) -> None:
        if self.console and self.verbose:
            self.console.log(msg)
