"""
Entry point for Bambu MQTT middle layer.

Connects to a local Bambu printer over MQTT using TLS, subscribes to telemetry
topics, parses incoming JSON messages, and logs or processes them for further use
(e.g., Grafana / InfluxDB pipelines).

Usage:
    python -m bambu_mqtt --host 192.168.0.123 --device-id ABC123 --access-code 123456
"""

import argparse
import logging
import signal
from importlib.metadata import version, PackageNotFoundError
import os
from typing import Any
from paho.mqtt.client import Client, MQTTMessage
from bambu_mqtt.telemetry import Telemetry
from bambu_mqtt.utils import connect_local_mqtt, extract_device_id_from_cert
from bambu_mqtt.parser import Parser
from bambu_mqtt.logger import configure_logging
from bambu_mqtt.writers.influxdb import InfluxDBWriter

logger = logging.getLogger("bambu_mqtt")

TOPIC_TEMPLATE: str = "device/{device_id}/{suffix}"


try:
    __version__ = version("bambu-mqtt")
except PackageNotFoundError:
    __version__ = "unknown"
    logger.warning(
        "Package not found. Version information may be unavailable. "
        "Ensure that the package is installed in the current environment."
    )


parser = argparse.ArgumentParser(
    prog="bambu_mqtt",
    description=(
        "Bambu MQTT listener - connect to a local Bambu printer over TLS, "
        "subscribe to telemetry topics, and parse the incoming messages for "
        "logging or further processing (e.g., Grafana / InfluxDB)."
    ),
    epilog=(
        "Note: The device ID is derived from the TLS certificate, so you do not need to "
        "provide it explicitly. The access code is required for MQTT authentication.\n\n"
        "Example usage:\n"
        "  python -m bambu_mqtt --host 192.0.2.10 "
        "--access-code YOUR_PRINTER_ACCESS_CODE --cert ./blcert.pem\n"
        "  python -m bambu_mqtt --host 192.0.2.10 "
        "--access-code YOUR_PRINTER_ACCESS_CODE --cert ./blcert.pem --log-level DEBUG\n\n"
    ),
    formatter_class=argparse.RawTextHelpFormatter,
)

parser.add_argument(
    "-H", "--host", required=True, help="LAN IP or hostname of the printer."
)
parser.add_argument("--access-code", required=True, help="Printer MQTT access code.")
parser.add_argument(
    "-c",
    "--cert",
    required=True,
    help="Path to the TLS certificate (used to derive device ID for MQTT).",
)
parser.add_argument(
    "-l",
    "--log-level",
    default="INFO",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    help="Set the logging level (default: INFO).",
)

parser.add_argument(
    "-v",
    "--version",
    action="version",
    version=f"%(prog)s {__version__}",
    help="Show the version of the Bambu MQTT listener and exit.",
)

parser.add_argument(
    "--influx-url",
    default="http://localhost:8086",
    help="InfluxDB server URL.",
)
parser.add_argument(
    "--influx-token",
    default=os.getenv("INFLUXDB_TOKEN"),
    required=os.getenv("INFLUXDB_TOKEN") is None,
    help="InfluxDB authentication token (or set INFLUXDB_TOKEN).",
)
parser.add_argument("--influx-org", required=True, help="InfluxDB organization.")
parser.add_argument("--influx-bucket", required=True, help="InfluxDB bucket.")

args = parser.parse_args()
configure_logging(args.log_level)

writer = InfluxDBWriter(
    url=args.influx_url,
    token=args.influx_token,
    org=args.influx_org,
    bucket=args.influx_bucket,
)

# Connect to printer via MQTT
try:
    device_id = extract_device_id_from_cert(args.cert)
except (ValueError, FileNotFoundError) as exc:
    logger.error("%s", exc)
    raise SystemExit(2) from exc

client = connect_local_mqtt(args.host, device_id, args.access_code, args.cert)
TOPIC_REPORT = TOPIC_TEMPLATE.format(device_id=device_id, suffix="report")


# Define callback for incoming MQTT messages
def on_message(_client: Client, _userdata: Any, msg: MQTTMessage):
    """On message handler for the MQTT client

    Args:
        _client (_type_): MQTT client session
        _userdata (_type_): MQTT userdata
        msg (_type_): Received message
    """
    logger.info("Received MQTT message on topic %s: parsing now", msg.topic)
    try:
        payload = msg.payload.decode("utf-8")
        data = Parser(payload).data
        telemetry = Telemetry.from_dict(
            data
        )  # TODO use telemetry object for further processing (e.g., logging, Grafana, InfluxDB)
        logger.debug("Received telemetry: %s", data)
        with writer:
            writer.write(telemetry)
        logger.info("Telemetry written to InfluxDB successfully.")
        logger.debug("Telemetry object: %s", telemetry)
    except UnicodeDecodeError as exc:
        logger.warning("Failed to decode MQTT payload: %s", exc)
    except ValueError as exc:
        logger.warning("Failed to parse MQTT payload: %s", exc)
    except Exception:
        logger.exception("Failed to process or store telemetry")


def on_connect(_client: Client, _userdata: Any, _flags: dict, rc: int):
    """On connect handler for the MQTT client

    Args:
        _client (Client): MQTT client session
        _userdata (Any): MQTT userdata
        _flags (dict): MQTT flags
        rc (int): Connection result code
    """
    if rc == 0:
        logger.info("Connected to printer %s at %s", device_id, args.host)
        client.subscribe(TOPIC_REPORT)
        logger.debug("Subscribed to topic %s", TOPIC_REPORT)
    else:
        logger.error("Failed to connect to printer: %s", rc)


def on_disconnect(_client: Client, _userdata: Any, rc: int):
    """On disconnect handler for the MQTT client

    Args:
        _client (_type_): MQTT client session
        _userdata (_type_): MQTT userdata
        rc (_type_): Disconnection result code
    """
    if rc != 0:
        logger.warning("Unexpected disconnection from printer: %s", rc)
    else:
        logger.info("Disconnected from printer %s at %s", device_id, args.host)


def handle_sigterm(_signum: int, _frame: Any):
    """Handle SIGTERM signal for graceful shutdown.

    Args:
        _signum (int): Signal number
        _frame (frame object): Current stack frame
    """
    logger.info("Received SIGTERM signal. Disconnecting from printer...")
    client.disconnect()
    logger.info("Disconnected. Exiting.")
    raise SystemExit(0)


client.on_message = on_message
client.on_connect = on_connect
client.on_disconnect = on_disconnect

client.subscribe(TOPIC_REPORT)

# Start MQTT network loop
signal.signal(signal.SIGTERM, handle_sigterm)
try:
    client.loop_forever()
except KeyboardInterrupt:
    logger.info("Shutdown requested by user (Ctrl+C)")
finally:
    logger.info("Disconnecting from printer")
    client.disconnect()
    logger.info("Bambu MQTT listener stopped")
