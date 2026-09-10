from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


class DecryptionError(Exception):
    """El payload no se pudo descifrar con la clave actual: normalmente porque
    alguien está publicando en el mismo tópico con otra clave, o porque no es un
    token Fernet."""

def get_fernet_instance(key_string: str) -> Fernet:
    """Retorna una instancia de Fernet a partir de una clave en string."""
    if not key_string:
        raise ValueError("La clave de cifrado no puede estar vacía.")
    try:
        # Intentar decodificar directamente si ya es una clave Fernet válida
        return Fernet(key_string.encode())
    except Exception:
        # Si no es una clave Fernet válida, derivarla de la frase con PBKDF2.
        # El salt es fijo A PROPÓSITO: cada peer escribe la misma frase y tiene
        # que llegar a la misma clave sin intercambiar nada primero. El coste es
        # que la misma frase siempre da la misma clave y que el salt es
        # precomputable. Para algo serio, usa el boton "Generate" (clave Fernet
        # aleatoria) en lugar de una frase. Ver docs/ARCHITECTURE.md.
        salt = b'walkietalkie-static-kdf-salt-v1'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600_000,
            backend=default_backend()
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key_string.encode()))
        return Fernet(derived_key)

def encrypt_message(message: str, fernet_instance: Fernet) -> str:
    """Encripta un mensaje usando una instancia de Fernet."""
    encrypted_bytes = fernet_instance.encrypt(message.encode())
    return encrypted_bytes.decode() # Devuelve la cadena en base64

def decrypt_message_with_key(encrypted_message: str, fernet_instance: Fernet) -> str:
    """Desencripta un mensaje usando una instancia de Fernet.

    Lanza DecryptionError si el token no cuadra con la clave. Antes esto
    devolvía la cadena "Error al desencriptar: ..." y la GUI la pintaba como un
    mensaje más del chat; ahora el llamador decide qué hacer (ver
    MqttClient._on_message)."""
    try:
        decrypted_bytes = fernet_instance.decrypt(encrypted_message.encode())
        return decrypted_bytes.decode()
    except Exception as e:
        raise DecryptionError(str(e)) from e

# Ejemplo de uso (para pruebas internas)
if __name__ == "__main__":
    # Generar una clave de prueba
    test_key = Fernet.generate_key().decode()
    print(f"Clave de prueba generada: {test_key}")
    
    # Obtener instancia de Fernet
    f = get_fernet_instance(test_key)

    original_message = "Hola, este es un mensaje secreto con clave dinámica."
    encrypted = encrypt_message(original_message, f)
    print(f"Mensaje original: {original_message}")
    print(f"Mensaje encriptado: {encrypted}")

    decrypted = decrypt_message_with_key(encrypted, f)
    print(f"Mensaje desencriptado: {decrypted}")

    # Prueba con un mensaje inválido
    invalid_encrypted = "esto_no_es_un_mensaje_valido"
    decrypted_invalid = decrypt_message_with_key(invalid_encrypted, f)
    print(f"Intento desencriptar inválido: {decrypted_invalid}")

    # Prueba con una clave que no es Fernet válida, para ver la derivación
    print("\n--- Probando derivación de clave ---")
    simple_key = "mi_clave_simple_y_secreta"
    f_derived = get_fernet_instance(simple_key)
    encrypted_derived = encrypt_message("Mensaje con clave derivada", f_derived)
    print(f"Mensaje encriptado con clave derivada: {encrypted_derived}")
    decrypted_derived = decrypt_message_with_key(encrypted_derived, f_derived)
    print(f"Mensaje desencriptado con clave derivada: {decrypted_derived}")


