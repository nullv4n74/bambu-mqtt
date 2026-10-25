"""Define typed data models for Bambu Lab printer telemetry.

This module provides nested dataclasses representing printer status,
temperature readings, connectivity, and Automatic Material System (AMS)
information. These models provide a structured representation of telemetry
for downstream processing, monitoring, and time-series storage.
"""

from dataclasses import dataclass, field
from typing import Any


def _as_float(value: Any) -> float | None:
    """Convert a value to float, returning None if invalid."""
    try:
        return float(value) if value is not None else None
    except TypeError, ValueError:
        return None


def _as_int(value: Any) -> int | None:
    """Convert a value to int, returning None if invalid."""
    try:
        return int(value) if value is not None else None
    except TypeError, ValueError:
        return None


def _as_str(value: Any) -> str | None:
    """Return a string value, or None if unavailable."""
    return value if isinstance(value, str) else None


@dataclass
class Temperature:
    """Represents a temperature reading from the printer."""

    nozzle: float | None = None
    nozzle_target: float | None = None
    bed: float | None = None
    bed_target: float | None = None
    chamber: float | None = None
    chamber_target: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Temperature":
        """Create a Temperature instance from a dictionary."""
        return cls(
            nozzle=_as_float(data.get("nozzle_temper")),
            nozzle_target=_as_float(data.get("nozzle_target_temper")),
            bed=_as_float(data.get("bed_temper")),
            bed_target=_as_float(data.get("bed_target_temper")),
        )


@dataclass
class PrinterStatus:
    """Represents the overall status of the printer."""

    state: str | None = None
    progress: float | None = None
    current_layer: int | None = None
    total_layers: int | None = None
    remaining_minutes: int | None = None
    job_name: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PrinterStatus":
        """Create a PrinterStatus instance from a dictionary."""
        return cls(
            state=_as_str(data.get("state")),
            progress=_as_float(data.get("progress")),
            current_layer=_as_int(data.get("current_layer")),
            total_layers=_as_int(data.get("total_layers")),
            remaining_minutes=_as_int(data.get("remaining_minutes")),
            job_name=_as_str(data.get("job_name")),
        )


@dataclass
class Connectivity:
    """Represents the connectivity status of the printer."""

    wifi_signal: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Connectivity":
        """Create a Connectivity instance from a dictionary."""
        return cls(
            wifi_signal=_as_str(data.get("wifi_signal")),
        )


@dataclass
class AMSTray:
    """Represents a single tray in the Automatic Material System (AMS)."""

    id: int | None = None
    filament_type: str | None = None
    color: str | None = None
    remaining: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AMSTray":
        """Create an AMSTray instance from a dictionary."""
        return cls(
            id=_as_int(data.get("id")),
            filament_type=_as_str(data.get("filament_type")),
            color=_as_str(data.get("color")),
            remaining=_as_int(data.get("remaining")),
        )


@dataclass
class AMSStatus:
    """Represents the status of the Automatic Material System (AMS)."""

    temperature: float | None = None
    humidity: float | None = None
    trays: list[AMSTray] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AMSStatus":
        """Create an AMSStatus instance from a dictionary."""
        trays_data = data.get("trays", [])
        trays = [AMSTray.from_dict(tray) for tray in trays_data] if trays_data else None
        return cls(
            temperature=_as_float(data.get("ams_temper")),
            humidity=_as_float(data.get("ams_humidity")),
            trays=trays,
        )


@dataclass
class Telemetry:
    """Represents the complete telemetry data from the printer."""

    printer: PrinterStatus = field(default_factory=PrinterStatus)
    temperatures: Temperature = field(default_factory=Temperature)
    connectivity: Connectivity = field(default_factory=Connectivity)
    ams: AMSStatus = field(default_factory=AMSStatus)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Telemetry":
        """Create telemetry from a parsed MQTT payload."""
        print_data = data.get("print", data)

        if not isinstance(print_data, dict):
            print_data = {}

        return cls(
            printer=PrinterStatus.from_dict(print_data),
            temperatures=Temperature.from_dict(print_data),
            connectivity=Connectivity.from_dict(print_data),
            ams=AMSStatus.from_dict(
                print_data.get("ams", {})
                if isinstance(print_data.get("ams"), dict)
                else {}
            ),
        )
