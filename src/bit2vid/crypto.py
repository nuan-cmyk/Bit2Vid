"""Encryption and authenticated payload container helpers."""

from __future__ import annotations

import hashlib
import logging
import secrets
import struct

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2

from bit2vid.config import MAGIC, PAYLOAD_HEADER_SIZE, VERSION
from bit2vid.errors import CryptoError, PayloadFormatError

LOGGER = logging.getLogger(__name__)

_PAYLOAD_HEADER_STRUCT = struct.Struct(">8sB3xI16s12s16sQ32s")


def derive_key(password: str, salt: bytes, iterations: int) -> bytes:
    """Derive an AES-256 key from a password."""

    if not password:
        raise CryptoError("Password must not be empty.")
    return PBKDF2(password, salt, dkLen=32, count=iterations, hmac_hash_module=SHA256)


def encrypt_payload(data: bytes, password: str, iterations: int) -> bytes:
    """Encrypt bytes into a self-describing authenticated payload."""

    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    key = derive_key(password, salt, iterations)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    digest = hashlib.sha256(data).digest()

    header = _PAYLOAD_HEADER_STRUCT.pack(
        MAGIC,
        VERSION,
        iterations,
        salt,
        nonce,
        tag,
        len(ciphertext),
        digest,
    )
    header = header.ljust(PAYLOAD_HEADER_SIZE, b"\0")
    LOGGER.debug("Encrypted %d bytes into %d ciphertext bytes.", len(data), len(ciphertext))
    return header + ciphertext


def decrypt_payload(payload: bytes, password: str) -> bytes:
    """Decrypt and authenticate a payload created by :func:`encrypt_payload`."""

    if len(payload) < PAYLOAD_HEADER_SIZE:
        raise PayloadFormatError("Encrypted payload is too short.")

    header = payload[: _PAYLOAD_HEADER_STRUCT.size]
    magic, version, iterations, salt, nonce, tag, ciphertext_len, digest = (
        _PAYLOAD_HEADER_STRUCT.unpack(header)
    )

    if magic != MAGIC:
        raise PayloadFormatError("Invalid encrypted payload magic.")
    if version != VERSION:
        raise PayloadFormatError(f"Unsupported payload version: {version}.")

    start = PAYLOAD_HEADER_SIZE
    end = start + ciphertext_len
    if end > len(payload):
        raise PayloadFormatError("Encrypted payload is truncated.")

    ciphertext = payload[start:end]
    key = derive_key(password, salt, iterations)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    try:
        data = cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError as exc:
        raise CryptoError("Decryption failed. The password or recovered data is invalid.") from exc

    if hashlib.sha256(data).digest() != digest:
        raise CryptoError("Decrypted data hash mismatch.")
    LOGGER.debug("Decrypted %d ciphertext bytes into %d bytes.", len(ciphertext), len(data))
    return data
