"""
MQTT client with TLS support to connect to an MQTT broker.

Project: Bambu MQTT
Author: dvanhecke
"""

import ssl
import paho.mqtt.client as mqtt


class MQTTSClient(mqtt.Client):
    """
    MQTT client that supports custom Server Name Indication (SNI) for TLS certificates.

    This is useful when the broker's certificate hostname does not match the connection hostname.
    See: https://github.com/eclipse-paho/paho.mqtt.python/issues/734#issuecomment-2256633060
    """

    def __init__(self, *args, server_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._server_name = server_name

    def _ssl_wrap_socket(self, tcp_sock) -> ssl.SSLSocket:
        """
        Wrap the TCP socket with SSL, overriding the host for custom SNI if specified.
        """
        orig_host = self._host
        if self._server_name:
            self._host = self._server_name
        res = super()._ssl_wrap_socket(tcp_sock)
        self._host = orig_host
        return res
