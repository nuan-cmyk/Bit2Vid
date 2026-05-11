"""Reed-Solomon block codec."""

from __future__ import annotations

import logging
import struct

from reedsolo import ReedSolomonError, RSCodec
from tqdm import tqdm

from bit2vid.errors import PayloadFormatError

LOGGER = logging.getLogger(__name__)

_ECC_HEADER_STRUCT = struct.Struct(">8sB3xHIIQ")
_ECC_MAGIC = b"CFECC001"


class ReedSolomonLayer:
    """Chunked Reed-Solomon encoder limited to 255-byte codewords."""

    def __init__(self, ecc_symbols: int) -> None:
        if not 1 <= ecc_symbols < 128:
            raise ValueError("ecc_symbols must be between 1 and 127.")
        self.ecc_symbols = ecc_symbols
        self.data_symbols = 255 - ecc_symbols
        self._codec = RSCodec(ecc_symbols)

    @property
    def redundancy_ratio(self) -> float:
        return self.ecc_symbols / self.data_symbols

    def encode(self, payload: bytes) -> bytes:
        """Add Reed-Solomon parity to a payload."""

        chunks = [
            payload[index : index + self.data_symbols]
            for index in range(0, len(payload), self.data_symbols)
        ]
        header = _ECC_HEADER_STRUCT.pack(
            _ECC_MAGIC,
            1,
            self.ecc_symbols,
            self.data_symbols,
            len(chunks),
            len(payload),
        )
        output = bytearray(header)

        LOGGER.info(
            "Applying Reed-Solomon ECC: %d chunks, %d parity symbols (%.1f%% redundancy).",
            len(chunks),
            self.ecc_symbols,
            self.redundancy_ratio * 100,
        )
        for chunk in tqdm(chunks, desc="ECC encode", unit="chunk"):
            padded = chunk.ljust(self.data_symbols, b"\0")
            output.extend(self._codec.encode(padded))
        return bytes(output)

    def decode(self, encoded: bytes) -> bytes:
        """Recover a payload from Reed-Solomon protected bytes."""

        if len(encoded) < _ECC_HEADER_STRUCT.size:
            raise PayloadFormatError("ECC payload is too short.")
        magic, version, ecc_symbols, data_symbols, chunk_count, payload_len = (
            _ECC_HEADER_STRUCT.unpack(encoded[: _ECC_HEADER_STRUCT.size])
        )
        if magic != _ECC_MAGIC:
            raise PayloadFormatError("Invalid ECC payload magic.")
        if version != 1:
            raise PayloadFormatError(f"Unsupported ECC version: {version}.")
        if ecc_symbols != self.ecc_symbols or data_symbols != self.data_symbols:
            raise PayloadFormatError("ECC settings do not match the transport header.")

        codeword_size = self.data_symbols + self.ecc_symbols
        expected_len = _ECC_HEADER_STRUCT.size + chunk_count * codeword_size
        if len(encoded) < expected_len:
            raise PayloadFormatError("ECC payload is truncated.")

        recovered = bytearray()
        offset = _ECC_HEADER_STRUCT.size
        LOGGER.info("Recovering Reed-Solomon ECC: %d chunks.", chunk_count)
        for _ in tqdm(range(chunk_count), desc="ECC decode", unit="chunk"):
            codeword = encoded[offset : offset + codeword_size]
            offset += codeword_size
            try:
                decoded = self._codec.decode(codeword)[0]
            except ReedSolomonError as exc:
                raise PayloadFormatError("Reed-Solomon recovery failed.") from exc
            recovered.extend(bytes(decoded[: self.data_symbols]))

        return bytes(recovered[:payload_len])
