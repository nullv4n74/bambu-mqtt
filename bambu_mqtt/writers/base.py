"""Define the abstract interface for telemetry writers."""

from abc import ABC, abstractmethod
from types import TracebackType

from bambu_mqtt.telemetry import Telemetry


class BaseWriter(ABC):
    """Abstract base class for telemetry output backends."""

    @abstractmethod
    def write(self, telemetry: Telemetry) -> None:
        """Write a telemetry snapshot to the configured backend."""
        raise NotImplementedError

    @abstractmethod
    def connect(self) -> None:
        """Establish a connection to the backend."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection to the backend."""
        raise NotImplementedError

    def __enter__(self) -> "BaseWriter":
        """Enter the runtime context related to this object."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the runtime context related to this object."""
        self.disconnect()
