import os
import time

import paho.mqtt.client as mqtt

from encryption import encrypt_message, decrypt_message_with_key, get_fernet_instance

# El broker por defecto es un Mosquitto local. Se puede apuntar a otro host con
# la variable de entorno MQTT_BROKER (o MQTT_PORT). No hay ningun broker publico
# por defecto: la app espera que ejecutes tu propio Mosquitto (ver README).
BROKER = os.environ.get("MQTT_BROKER", "127.0.0.1")
PORT = int(os.environ.get("MQTT_PORT", "1883"))

DEFAULT_TOPIC = "chat/general"


class MqttClient:
    def __init__(self, client_id="", topic=DEFAULT_TOPIC, encryption_key=None,
                 broker=None, port=None):
        self.broker = broker or BROKER
        self.port = port or PORT
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.message_callback = None
        self.topic = topic
        self.fernet = get_fernet_instance(encryption_key)

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(self.topic)
            print(f"Conectado al broker MQTT. Suscrito a {self.topic}")
        else:
            print(f"Fallo la conexión, código de resultado {reason_code}")

    def _on_message(self, client, userdata, msg):
        try:
            encrypted_payload = msg.payload.decode()
            decrypted_message = decrypt_message_with_key(encrypted_payload, self.fernet)
            if self.message_callback:
                self.message_callback(decrypted_message)
            else:
                print(f"Mensaje recibido: {decrypted_message}")
        except Exception as e:
            print(f"Error al procesar mensaje: {e}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        print(f"Desconectado con código de resultado {reason_code}")

    def connect(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"Error al conectar: {e}")

    def connect_test(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            return True
        except Exception as test:
            print(test)
            return False

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish_message(self, message: str):
        encrypted_msg = encrypt_message(message, self.fernet)
        self.client.publish(self.topic, encrypted_msg)

    def set_message_callback(self, callback):
        self.message_callback = callback

    def loop_forever(self):
        self.client.loop_forever()


# Ejemplo de uso (para pruebas internas). Necesita un Mosquitto local escuchando
# en 127.0.0.1:1883.
if __name__ == "__main__":
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key().decode()
    print(f"Clave de prueba generada: {test_key}")

    sender_client = MqttClient(client_id="python_sender_1", topic="test/chat", encryption_key=test_key)
    sender_client.connect()

    receiver_client = MqttClient(client_id="python_receiver_1", topic="test/chat", encryption_key=test_key)

    def print_received_message(msg):
        print(f"[RECEPTOR] Mensaje desencriptado: {msg}")

    receiver_client.set_message_callback(print_received_message)
    receiver_client.connect()

    time.sleep(2)

    sender_client.publish_message("Hola desde el cliente Python con clave dinámica!")
    sender_client.publish_message("Este es un segundo mensaje con clave dinámica.")

    time.sleep(5)

    sender_client.disconnect()
    receiver_client.disconnect()
    print("Clientes desconectados.")
