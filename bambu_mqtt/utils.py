"""
Utility functions for Bambu MQTT connections and TLS setup.

This module provides helpers to:

- Create a TLS/SSL context for secure connections to local Bambu printers,
  automatically referencing the package-local certificate.
- Connect to a local printer over MQTT using TLS, handling authentication
  and server name indication (SNI).

All functions are designed for LAN-only printer setups with developer mode
enabled and can be integrated with Telegraf / InfluxDB pipelines.

Project: Bambu MQTT
Author: dvanhecke
"""

import ssl
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from bambu_mqtt.mqtt_client import MQTTSClient


def extract_device_id_from_cert(cert_path: str | Path) -> str:
    """
    Extracts the Bambu printer device ID from the provided PEM certificate.

    Args:
        cert_path (str | Path): Path to the PEM certificate file.

    Returns:
        str: The device ID embedded in the certificate CN.

    Raises:
        FileNotFoundError: If the certificate file does not exist.
        ValueError: If the device ID cannot be found in the certificate.
    """
    cert_path = Path(cert_path)
    if not cert_path.exists():
        raise FileNotFoundError(f"Certificate file not found: {cert_path}")

    with cert_path.open("rb") as f:
        cert_data = f.read()

    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    subject = cert.subject

    # The device ID is usually in the Common Name (CN)
    cn = subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    if not cn:
        raise ValueError("Device ID not found in certificate CN")

    return cn[0].value


def create_local_ssl_context(ca_cert_path: str) -> ssl.SSLContext:
    """
    Create an SSL context for TLS connections to local Bambu printers.

    This context validates the printer's certificate located in the package's
    `certs/` folder, relaxing strict X.509 verification for LAN-only printer
    certificates. When using the context, you must call:
        context.wrap_socket(sock, servername=printer_serial_number)
    to correctly set the Server Name Indication (SNI) for the printer.

    Returns:
        ssl.SSLContext: Configured SSL context for local printer connections.
    """
    # Locate the certificate in the bambu_mqtt package

    context = ssl.create_default_context(cafile=ca_cert_path)
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


def connect_local_mqtt(
    hostname: str, device_id: str, access_code: str, certfile: str
) -> MQTTSClient:
    """
    Connect to a local Bambu printer over MQTT using TLS.

    Args:
        hostname (str): The LAN IP or hostname of the printer.
        device_id (str): The printer's device ID, used for SNI in TLS.
        access_code (str): Printer-specific password for MQTT authentication.

    Returns:
        MQTTSClient: A connected MQTT client instance ready to subscribe or publish.
    """
    client = MQTTSClient(server_name=device_id)
    client.tls_set_context(create_local_ssl_context(certfile))
    client.username_pw_set("bblp", access_code)
    client.connect(hostname, port=8883, keepalive=60)
    return client
