import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptography.fernet import Fernet

import mqtt_client
from mqtt_client import MqttClient


def test_default_broker_is_local():
    assert mqtt_client.BROKER == "127.0.0.1"
    assert mqtt_client.PORT == 1883


def test_client_builds_without_connecting():
    c = MqttClient(client_id="t", topic="chat/test",
                   encryption_key=Fernet.generate_key().decode())
    assert c.topic == "chat/test"
    assert c.broker == "127.0.0.1"
    # Sin llamar a connect() no se abre ningún socket.


def test_broker_override_via_argument():
    c = MqttClient(client_id="t", topic="chat/test",
                   encryption_key=Fernet.generate_key().decode(),
                   broker="192.168.1.50", port=8883)
    assert c.broker == "192.168.1.50"
    assert c.port == 8883


def test_no_public_broker_string_in_source():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("mqtt_client.py", "app.py", "encryption.py"):
        text = open(os.path.join(here, name), encoding="utf-8").read().lower()
        for banned in ("hivemq", "mosquitto.org", "test.mosquitto", "broker.emqx"):
            assert banned not in text, f"{banned} found in {name}"
