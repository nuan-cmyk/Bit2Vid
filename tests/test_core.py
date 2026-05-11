from __future__ import annotations

import os

import numpy as np

from cipherframe.config import VideoSettings
from cipherframe.crypto import decrypt_payload, encrypt_payload
from cipherframe.ecc import ReedSolomonLayer, _ECC_HEADER_STRUCT
from cipherframe.transport import (
    bits_to_bytes,
    bits_to_frames,
    build_transport_header,
    bytes_to_bits,
    frame_to_bits,
    parse_transport_header,
)


def test_crypto_ecc_and_frame_roundtrip() -> None:
    password = "correct horse battery staple"
    plain = os.urandom(4096) + b"cipherframe"
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
