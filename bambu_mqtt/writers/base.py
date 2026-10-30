"""Define the abstract interface for telemetry writers."""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from bambu_mqtt.telemetry import Telemetry


class BaseWriter(ABC):
    """Abstract base class for telemetry output backends."""

    @abstractmethod
    def write(self, telemetry: Telemetry) -> None:
        """Write a telemetry snapshot to the configured backend.

        Args:
            telemetry (Telemetry): Telemetry to write.

        Raises:
            NotImplementedError: Not yet implemented.
        """
        raise NotImplementedError

    @abstractmethod
    def connect(self) -> None:
        """Establish a connection.

        Raises:
            NotImplementedError: Not yet implemented.
        """
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection.

        Raises:
            NotImplementedError: Not yet implemented.
        """
        raise NotImplementedError

    def __enter__(self) -> Self:
        """Connect to the backend and enter the runtime context.

        Returns:
            Self: Writer object.
        """
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Disconnect from the backend when leaving the runtime context.

        Args:
            exc_type (type[BaseException] | None): exit type.
            exc_value (BaseException | None): exit value.
            traceback (TracebackType | None): traceback.
        """
        self.disconnect()
