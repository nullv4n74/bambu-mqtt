"""Parse and normalize Bambu Lab H2S printer telemetry."""

from dataclasses import dataclass, field
from typing import Any


def _as_float(value: Any) -> float | None:
    """Convert a value to float."""
    try:
        return float(value) if value is not None else None
    except TypeError, ValueError:
        return None


def _as_int(value: Any) -> int | None:
    """Convert a value to int."""
    try:
        return int(value) if value is not None else None
    except TypeError, ValueError:
        return None


def _as_str(value: Any) -> str | None:
    """Convert a value to string, if valid."""
    return value if isinstance(value, str) else None


@dataclass
class PrinterStatus:
    """Printer and print-job information."""

    state: str | None = None
    progress: float | None = None
    current_layer: int | None = None
    total_layers: int | None = None
    remaining_minutes: int | None = None
    job_name: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PrinterStatus":
        return cls(
            state=_as_str(data.get("gcode_state")),
            progress=_as_float(data.get("mc_percent")),
            current_layer=_as_int(data.get("layer_num")),
            total_layers=_as_int(data.get("total_layer_num")),
            remaining_minutes=_as_int(data.get("mc_remaining_time")),
            job_name=_as_str(data.get("subtask_name")),
        )


@dataclass
class Temperature:
    """Printer temperature readings."""

    nozzle: float | None = None
    nozzle_target: float | None = None
    bed: float | None = None
    bed_target: float | None = None
    chamber: float | None = None
    chamber_target: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Temperature":
        """Create temperature readings from Bambu MQTT data."""

        device = data.get("device", {})
        ctc = device.get("ctc", {}) if isinstance(device, dict) else {}
        ctc_info = ctc.get("info", {}) if isinstance(ctc, dict) else {}

        return cls(
            nozzle=_as_float(data.get("nozzle_temper")),
            nozzle_target=_as_float(data.get("nozzle_target_temper")),
            bed=_as_float(data.get("bed_temper")),
            bed_target=_as_float(data.get("bed_target_temper")),
            chamber=(
                _as_float(ctc_info.get("temp")) if isinstance(ctc_info, dict) else None
            ),
            chamber_target=None,
        )


@dataclass
class Connectivity:
    """Printer network connectivity."""

    wifi_signal: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Connectivity":
        return cls(
            wifi_signal=_as_str(data.get("wifi_signal")),
        )


@dataclass
class AMSTray:
    """Individual filament tray."""

    id: int | None = None
    filament_type: str | None = None
    color: str | None = None
    remaining: int | None = None
    nozzle_temp_min: float | None = None
    nozzle_temp_max: float | None = None
    tray_diameter: float | None = None
    tray_weight: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AMSTray":
        remaining = _as_int(data.get("remain"))

        return cls(
            id=_as_int(data.get("id")),
            filament_type=_as_str(data.get("tray_type")),
            color=_as_str(data.get("tray_color")),
            remaining=(remaining if remaining is not None and remaining >= 0 else None),
            nozzle_temp_min=_as_float(data.get("nozzle_temp_min")),
            nozzle_temp_max=_as_float(data.get("nozzle_temp_max")),
            tray_diameter=_as_float(data.get("tray_diameter")),
            tray_weight=_as_float(data.get("tray_weight")),
        )


@dataclass
class AMSStatus:
    """One AMS unit and its filament trays."""

    id: str | None = None
    temperature: float | None = None
    humidity: float | None = None
    humidity_raw: float | None = None
    trays: list[AMSTray] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AMSStatus":
        tray_data = data.get("tray", [])

        trays = (
            [AMSTray.from_dict(tray) for tray in tray_data if isinstance(tray, dict)]
            if isinstance(tray_data, list)
            else []
        )

        return cls(
            id=_as_str(data.get("id")),
            temperature=_as_float(data.get("temp")),
            humidity=_as_float(data.get("humidity")),
            humidity_raw=_as_float(data.get("humidity_raw")),
            trays=trays,
        )


@dataclass
class Telemetry:
    """Normalized Bambu Lab printer telemetry."""

    printer: PrinterStatus = field(default_factory=PrinterStatus)
    temperatures: Temperature = field(default_factory=Temperature)
    connectivity: Connectivity = field(default_factory=Connectivity)
    ams: list[AMSStatus] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Telemetry":
        """Parse a complete Bambu MQTT status payload."""

        print_data = payload.get("print", payload)

        if not isinstance(print_data, dict):
            raise ValueError("Invalid MQTT payload: missing print dictionary")

        ams_container = print_data.get("ams", {})
        ams_units = (
            ams_container.get("ams", []) if isinstance(ams_container, dict) else []
        )

        ams = (
            [AMSStatus.from_dict(unit) for unit in ams_units if isinstance(unit, dict)]
            if isinstance(ams_units, list)
            else []
        )

        return cls(
            printer=PrinterStatus.from_dict(print_data),
            temperatures=Temperature.from_dict(print_data),
            connectivity=Connectivity.from_dict(print_data),
            ams=ams,
        )
