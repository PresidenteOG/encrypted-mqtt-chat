import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from cryptography.fernet import Fernet

from encryption import (
    get_fernet_instance,
    encrypt_message,
    decrypt_message_with_key,
    DecryptionError,
)


def test_roundtrip_with_generated_key():
    key = Fernet.generate_key().decode()
    f = get_fernet_instance(key)
    token = encrypt_message("hola mundo", f)
    assert token != "hola mundo"
    assert decrypt_message_with_key(token, f) == "hola mundo"


def test_passphrase_derivation_is_deterministic():
    a = get_fernet_instance("una frase compartida")
    b = get_fernet_instance("una frase compartida")
    token = encrypt_message("mensaje", a)
    # Otro peer que escribe la misma frase puede leerlo.
    assert decrypt_message_with_key(token, b) == "mensaje"


def test_wrong_key_cannot_decrypt():
    good = get_fernet_instance(Fernet.generate_key().decode())
    bad = get_fernet_instance(Fernet.generate_key().decode())
    token = encrypt_message("secreto", good)
    with pytest.raises(DecryptionError):
        decrypt_message_with_key(token, bad)


def test_garbage_payload_raises():
    f = get_fernet_instance(Fernet.generate_key().decode())
    with pytest.raises(DecryptionError):
        decrypt_message_with_key("esto-no-es-un-token", f)


def test_empty_key_rejected():
    try:
        get_fernet_instance("")
    except ValueError:
        return
    raise AssertionError("una clave vacía debería lanzar ValueError")
