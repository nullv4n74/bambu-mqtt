"""Parse and normalize Bambu Lab printer telemetry.

This module extracts useful printer and AMS metrics from MQTT status
payloads and converts them into a structured dictionary suitable for
logging, monitoring, and time-series storage.
"""

import json
from typing import Any, Dict


class Parser:
    """Parse and normalize Bambu Lab printer telemetry."""

    def __init__(self, payload: str) -> None:
        self._payload: str = payload
        self._data: Dict[str, Any] = self.parse_data()

    def parse_data(self) -> Dict[str, Any]:
        """Parse the MQTT payload and return a structured dictionary."""
        try:
            parsed = json.loads(self._payload)
            # Normalize keys and values as needed
            normalized_data = {k.lower(): v for k, v in parsed.items()}
            return normalized_data
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON payload") from e

    @property
    def data(self) -> Dict[str, Any]:
        """Return the parsed and normalized data."""
        return self._data

    @property
    def payload(self) -> str:
        """Return the original payload."""
        return self._payload

    def __str__(self) -> str:
        """Return a string representation of the parsed data."""
        return json.dumps(self._data, indent=2)
