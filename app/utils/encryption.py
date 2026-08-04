import base64
import json
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.config import settings


def _get_fernet_key() -> bytes:
    key_str = settings.ENCRYPTION_KEY
    if len(key_str) == 44 and key_str.endswith("="):
        try:
            return key_str.encode()
        except Exception:
            pass
    # Derive a valid 32-byte urlsafe base64 key from any string
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"ashhub_salt_2026",
        iterations=100000,
    )
    derived = kdf.derive(key_str.encode())
    return base64.urlsafe_b64encode(derived)


_fernet = Fernet(_get_fernet_key())


def encrypt_env_vars(env_dict: dict[str, str]) -> str:
    """Encrypt a dictionary of environment variables into a secure string."""
    if not env_dict:
        return ""
    json_str = json.dumps(env_dict)
    encrypted_bytes = _fernet.encrypt(json_str.encode())
    return encrypted_bytes.decode()


def decrypt_env_vars(encrypted_str: str) -> dict[str, str]:
    """Decrypt an encrypted string back into a dictionary of environment variables."""
    if not encrypted_str:
        return {}
    try:
        decrypted_bytes = _fernet.decrypt(encrypted_str.encode())
        return json.loads(decrypted_bytes.decode())
    except Exception:
        return {}


def encrypt_token(token: str | None) -> str | None:
    """Encrypt a plaintext string token."""
    if not token:
        return None
    encrypted_bytes = _fernet.encrypt(token.encode())
    return encrypted_bytes.decode()


def decrypt_token(encrypted_str: str | None) -> str | None:
    """Decrypt an encrypted token string back to plaintext."""
    if not encrypted_str:
        return None
    try:
        decrypted_bytes = _fernet.decrypt(encrypted_str.encode())
        return decrypted_bytes.decode()
    except Exception:
        return encrypted_str
