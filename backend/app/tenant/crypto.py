"""
API-Key Verschlüsselung / Entschlüsselung — AES-256-GCM (MiroFish)

Identisches Schema wie BettaFish/tenant/crypto.py:
    - Algorithmus:  AES-256-GCM
    - Schlüssel:    32 Bytes, Base64-kodiert in DERFISH_MASTER_KEY
    - Nonce/IV:     12 zufällige Bytes (os.urandom)
    - Tag:          16 Bytes, am Ende von encrypted_value angehängt
    - Legacy-IV:    b"\\x00" * 16  →  Klartext (Phase 1d, Migration)

Entwicklungsmodus: kein DERFISH_MASTER_KEY → Klartext + Null-IV.
"""

import base64
import os

_cached_key: bytes | None = None
_cached_key_b64: str | None = None


def _get_master_key() -> bytes:
    """Liest und cached den Master-Key (32 Bytes) aus DERFISH_MASTER_KEY."""
    global _cached_key, _cached_key_b64

    b64 = os.environ.get("DERFISH_MASTER_KEY", "")
    if not b64:
        raise ValueError(
            "DERFISH_MASTER_KEY ist nicht gesetzt. "
            "Setze ihn oder entferne verschlüsselte Werte aus der DB."
        )
    if b64 == _cached_key_b64 and _cached_key is not None:
        return _cached_key

    try:
        key = base64.b64decode(b64)
    except Exception as exc:
        raise ValueError(f"DERFISH_MASTER_KEY ist kein gültiges Base64: {exc}") from exc

    if len(key) != 32:
        raise ValueError(
            f"DERFISH_MASTER_KEY muss nach Base64-Dekodierung 32 Bytes ergeben "
            f"(ist {len(key)} Bytes)."
        )

    _cached_key = key
    _cached_key_b64 = b64
    return key


def encrypt_value(plaintext: str) -> tuple[bytes, bytes]:
    """
    Verschlüsselt einen API-Key für die Datenbank.

    Returns:
        (encrypted_value_bytes, iv_bytes)
    """
    master_key_b64 = os.environ.get("DERFISH_MASTER_KEY", "")
    if not master_key_b64:
        return plaintext.encode("utf-8"), b"\x00" * 16

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _get_master_key()
    iv = os.urandom(12)
    ciphertext_with_tag = AESGCM(key).encrypt(iv, plaintext.encode("utf-8"), None)
    return ciphertext_with_tag, iv


def decrypt_value(encrypted_value: bytes, iv: bytes) -> str:
    """
    Entschlüsselt einen gespeicherten API-Key.

    iv == b"\\x00" * 16  →  Klartext (Legacy-Phase-1d-Eintrag)
    iv == 12 Bytes       →  AES-256-GCM

    Raises:
        ValueError: MASTER_KEY fehlt oder ungültig
        cryptography.exceptions.InvalidTag: Ciphertext manipuliert
    """
    if iv == bytes(16):
        return encrypted_value.decode("utf-8")

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _get_master_key()
    return AESGCM(key).decrypt(iv, encrypted_value, None).decode("utf-8")


def generate_master_key() -> str:
    """Generiert einen neuen 32-Byte Master-Key als Base64-String."""
    return base64.b64encode(os.urandom(32)).decode("ascii")
