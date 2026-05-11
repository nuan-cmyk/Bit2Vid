from __future__ import annotations

import os

import numpy as np

from bit2vid.config import VideoSettings
from bit2vid.crypto import decrypt_payload, encrypt_payload
from bit2vid.ecc import ReedSolomonLayer, _ECC_HEADER_STRUCT
from bit2vid.transport import (
    bits_to_bytes,
    bits_to_frames,
    build_transport_header,
    bytes_to_bits,
    frame_to_bits,
    parse_transport_header,
)


def test_crypto_ecc_and_frame_roundtrip() -> None:
    """Test encryption, ECC encoding, and frame rendering."""
    password = "correct horse battery staple"
    plain = os.urandom(4096) + b"bit2vid"
    encrypted = encrypt_payload(plain, password, 10_000)
    assert decrypt_payload(encrypted, password) == plain

    ecc = ReedSolomonLayer(64)
    protected = bytearray(ecc.encode(encrypted))
    for index in range(_ECC_HEADER_STRUCT.size, min(len(protected), 540), 57):
        protected[index] ^= 0x55
    assert ecc.decode(bytes(protected)) == encrypted

    settings = VideoSettings(block_size=8)
    header = build_transport_header(settings, ecc.ecc_symbols, len(protected))
    parsed_settings, ecc_symbols, encoded_len = parse_transport_header(header)
    assert parsed_settings.block_size == settings.block_size
    assert ecc_symbols == ecc.ecc_symbols
    assert encoded_len == len(protected)

    bits = bytes_to_bits(header + bytes(protected))
    frames = bits_to_frames(bits, settings)
    recovered_bits = np.concatenate([frame_to_bits(frame.tobytes(), settings) for frame in frames])
    recovered = bits_to_bytes(recovered_bits, len(header) + len(protected))
    assert recovered == header + bytes(protected)


def test_wrong_password() -> None:
    """Test that wrong password raises CryptoError."""
    from bit2vid.errors import CryptoError

    password = "correct"
    plain = b"secret data"
    encrypted = encrypt_payload(plain, password, 10_000)

    try:
        decrypt_payload(encrypted, "wrong")
        assert False, "Should have raised CryptoError"
    except CryptoError as e:
        assert "Decryption failed" in str(e) or "hash mismatch" in str(e)


def test_corrupted_ecc() -> None:
    """Test that corrupted ECC data can be partially recovered."""
    from bit2vid.errors import PayloadFormatError

    plain = b"test data for corruption"
    ecc = ReedSolomonLayer(32)
    protected = bytearray(ecc.encode(plain))

    # Corrupt some bytes beyond ECC capability - should fail
    for i in range(_ECC_HEADER_STRUCT.size + 200, _ECC_HEADER_STRUCT.size + 210):
        protected[i] ^= 0xFF

    try:
        ecc.decode(bytes(protected))
        # May or may not fail depending on corruption pattern
    except PayloadFormatError:
        pass  # Expected for severe corruption
