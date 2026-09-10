# Architecture

This is a flat three-file program. No framework, no layers, no dependency
injection. Writing it down so nobody reads more structure into it than exists.

## Pieces

| File | Responsibility |
|------|----------------|
| `app.py` | The Tkinter GUI. Builds the login screen and the chat window, validates input, formats incoming messages, owns the connection lifecycle. |
| `mqtt_client.py` | `MqttClient` — wraps a `paho.mqtt.client.Client`. Subscribes on connect, encrypts before publish, decrypts on message, hands the plaintext to a callback the GUI sets. |
| `encryption.py` | Three functions: build a Fernet instance from a key or a passphrase, encrypt a string, decrypt a string. |

## Message flow

Send:

```
user types text
  -> ChatGUI.send_message()            (app.py)
  -> MqttClient.publish_message(text)  (mqtt_client.py)
  -> encrypt_message(text, fernet)     (encryption.py)  -> ciphertext
  -> client.publish(topic, ciphertext)                  -> broker
```

Receive:

```
broker delivers ciphertext on the subscribed topic
  -> MqttClient._on_message()                (mqtt_client.py)
  -> decrypt_message_with_key(payload, fernet) (encryption.py) -> plaintext
  -> message_callback(plaintext)  == ChatGUI.display_message   (app.py)
  -> Tkinter text widget, tagged by message type
```

If `decrypt_message_with_key` raises `DecryptionError` (a payload published to the
topic with a different key, or plain garbage), `_on_message` sends a single
`FOREIGN_KEY_NOTICE` through the callback the first time it happens and drops
every later one, so the chat window never shows a decryption failure as a line.

The MQTT network loop runs on a background thread (`loop_start`). `display_message`
marshals back onto the Tk main thread with `root.after(0, ...)`.

## Connection lifecycle

1. Login screen collects username, topic, key.
2. `connect_to_chat()` validates, builds an `MqttClient`, starts a worker thread.
3. The worker calls `connect_test()`. On success the GUI swaps to the chat window
   and publishes a "joined" line.
4. Exit publishes a "left" line, calls `disconnect()`, returns to the login
   screen.

## Broker configuration

`mqtt_client.py` reads `MQTT_BROKER` (default `127.0.0.1`) and `MQTT_PORT`
(default `1883`) from the environment at import time. An earlier version had a
public broker hardcoded; that is gone. The app has no fallback to any public
broker — if nothing is listening on the configured host, the connection fails
and the GUI says so.

## Encryption details

Fernet = AES-128-CBC + HMAC-SHA256, IV per message, all from the `cryptography`
package. The key is either supplied directly (a real Fernet key) or derived from
a passphrase with PBKDF2-HMAC-SHA256, 600,000 iterations, and a **static salt**.
The static salt is a deliberate trade-off: peers need to reach the same key from
the same phrase without exchanging a salt first. It also means the derivation is
dictionary-attackable and the same phrase always produces the same key. The
generated-key path has neither problem and is the intended way to use the app.

See the README's "What it does not protect" section for the full list of
limitations.
