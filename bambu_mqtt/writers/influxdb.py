"""Write Bambu Lab printer telemetry to InfluxDB.

This module provides an InfluxDB-backed implementation of the
:class:`BaseWriter` interface for storing printer and AMS telemetry
as time-series data.
"""

import logging
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, WriteApi

from bambu_mqtt.telemetry import Telemetry
from bambu_mqtt.writers.base import BaseWriter

logger = logging.getLogger(__name__)


class InfluxDBWriter(BaseWriter):
    """Write Bambu Lab printer telemetry to InfluxDB.

    This class implements the :class:`BaseWriter` interface for storing
    printer and AMS telemetry as time-series data in an InfluxDB backend.
    """

    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket: str,
    ) -> None:
        """Initialize the InfluxDBWriter.

        Args:
            url (str): InfluxDB server URL.
            token (str): InfluxDB authentication token.
            org (str): InfluxDB organization name.
            bucket (str): InfluxDB bucket name.
        """
        self._url = url
        self._token = token
        self._org = org
        self._bucket = bucket
        self._client: InfluxDBClient | None = None
        self._write_api: WriteApi | None = None

    def write(self, telemetry: Telemetry) -> None:
        """Write printer, AMS, and filament tray telemetry."""

        if self._write_api is None:
            raise RuntimeError("InfluxDB writer is not connected")

        points: list[Point] = []

        # --------------------------------------------------
        # Printer measurement
        # --------------------------------------------------

        printer = telemetry.printer
        temperatures = telemetry.temperatures
        connectivity = telemetry.connectivity

        printer_fields = {
            "state": printer.state,
            "progress": printer.progress,
            "current_layer": printer.current_layer,
            "total_layers": printer.total_layers,
            "remaining_minutes": printer.remaining_minutes,
            "job_name": printer.job_name,
            "nozzle_temperature": temperatures.nozzle,
            "nozzle_target_temperature": temperatures.nozzle_target,
            "bed_temperature": temperatures.bed,
            "bed_target_temperature": temperatures.bed_target,
            "chamber_temperature": temperatures.chamber,
            "chamber_target_temperature": temperatures.chamber_target,
            "wifi_signal": connectivity.wifi_signal,
        }

        printer_point = Point("printer")

        for name, value in printer_fields.items():
            if value is not None:
                printer_point = printer_point.field(name, value)

        if any(value is not None for value in printer_fields.values()):
            points.append(printer_point)

        # --------------------------------------------------
        # AMS measurements
        # --------------------------------------------------

        for ams in telemetry.ams:

            # AMS unit measurement
            ams_fields = {
                "temperature": ams.temperature,
                "humidity": ams.humidity,
                "humidity_raw": ams.humidity_raw,
            }

            ams_point = Point("ams")

            if ams.id is not None:
                ams_point = ams_point.tag("ams_id", ams.id)

            for name, value in ams_fields.items():
                if value is not None:
                    ams_point = ams_point.field(name, value)

            if any(value is not None for value in ams_fields.values()):
                points.append(ams_point)

            # --------------------------------------------------
            # Individual filament tray measurements
            # --------------------------------------------------

            for tray in ams.trays:
                tray_fields = {
                    "filament_type": tray.filament_type,
                    "color": tray.color,
                    "remaining": tray.remaining,
                    "nozzle_temp_min": tray.nozzle_temp_min,
                    "nozzle_temp_max": tray.nozzle_temp_max,
                    "tray_diameter": tray.tray_diameter,
                    "tray_weight": tray.tray_weight,
                }

                tray_point = Point("ams_tray")

                if ams.id is not None:
                    tray_point = tray_point.tag("ams_id", ams.id)

                if tray.id is not None:
                    tray_point = tray_point.tag(
                        "tray_id",
                        str(tray.id),
                    )

                for name, value in tray_fields.items():
                    if value is not None:
                        tray_point = tray_point.field(name, value)

                if any(value is not None for value in tray_fields.values()):
                    points.append(tray_point)

        # --------------------------------------------------
        # Write measurements
        # --------------------------------------------------

        if not points:
            logger.debug("No telemetry data available to write")
            return

        try:
            self._write_api.write(
                bucket=self._bucket,
                org=self._org,
                record=points,
            )
        except Exception:
            logger.exception("Failed to write telemetry to InfluxDB")
            raise

        logger.debug(
            "Successfully wrote %d telemetry points to InfluxDB",
            len(points),
        )

    def connect(self) -> None:
        """Establish an InfluxDB connection."""
        if self._client is not None:
            logger.warning("InfluxDB writer is already connected")
            raise RuntimeError("InfluxDB writer is already connected")

        logger.info("Connecting to InfluxDB at %s", self._url)

        client = InfluxDBClient(
            url=self._url,
            token=self._token,
            org=self._org,
        )

        try:
            write_api = client.write_api(write_options=SYNCHRONOUS)
        except Exception:
            logger.exception("Failed to initialise InfluxDB write API")

            try:
                client.close()
            except Exception:
                logger.exception(
                    "Failed to close InfluxDB client after initialisation failure"
                )

            raise

        self._client = client
        self._write_api = write_api

        logger.info("Successfully connected to InfluxDB")

    def disconnect(self) -> None:
        """Close the InfluxDB connection."""
        logger.info("Disconnecting from InfluxDB")

        write_api = self._write_api
        client = self._client

        # Reset state before attempting cleanup.
        self._write_api = None
        self._client = None

        cleanup_error = None

        if write_api is not None:
            try:
                write_api.close()
                logger.debug("InfluxDB write API closed")
            except Exception as exc:
                logger.exception("Failed to close InfluxDB write API")
                cleanup_error = exc

        if client is not None:
            try:
                client.close()
                logger.debug("InfluxDB client closed")
            except Exception as exc:
                logger.exception("Failed to close InfluxDB client")
                if cleanup_error is None:
                    cleanup_error = exc

        if cleanup_error is not None:
            raise cleanup_error

        logger.info("Successfully disconnected from InfluxDB")
