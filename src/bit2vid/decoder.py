"""High-level MP4-to-binary decoder."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from tqdm import tqdm

from bit2vid.config import (
    DEFAULT_BLOCK_SIZE,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    TRANSPORT_HEADER_REPEATS,
    TRANSPORT_HEADER_SIZE,
    VideoSettings,
)
from bit2vid.crypto import decrypt_payload
from bit2vid.ecc import ReedSolomonLayer
from bit2vid.errors import PayloadFormatError
from bit2vid.ffmpeg import finish_process, start_decoder
from bit2vid.transport import bits_to_bytes, frame_to_bits, parse_transport_header

LOGGER = logging.getLogger(__name__)


class VideoDecoder:
    """Decode a Bit2Vid MP4 back into the original binary file."""

    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> None:
        self.width = width
        self.height = height

    def decode_file(self, input_path: Path, output_path: Path, password: str, ffmpeg_path: str | None = None) -> None:
        """Decode an MP4 container to the original binary output."""

        if not input_path.is_file():
            raise FileNotFoundError(f"Input video does not exist: {input_path}")
        if output_path.exists() and output_path.is_dir():
            raise IsADirectoryError(f"Output path is a directory: {output_path}")

        LOGGER.info("Reading video frames through FFmpeg: %s", input_path)
        frames = self._read_raw_frames(input_path, ffmpeg_path)
        settings, ecc_symbols, encoded_len, all_bits = self._recover_transport(frames)
        header_len = TRANSPORT_HEADER_REPEATS * TRANSPORT_HEADER_SIZE
        byte_stream = bits_to_bytes(all_bits, header_len + encoded_len)
        protected = byte_stream[header_len : header_len + encoded_len]

        LOGGER.info("Recovered %d Reed-Solomon protected bytes.", len(protected))
        encrypted = ReedSolomonLayer(ecc_symbols).decode(protected)
        plain = decrypt_payload(encrypted, password)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(plain)
        LOGGER.info("Decoded file written to: %s", output_path)

    def _read_raw_frames(self, input_path: Path, ffmpeg_path: str | None = None) -> list[bytes]:
        frame_size = self.width * self.height
        process = start_decoder(input_path, ffmpeg_path)
        if process.stdout is None:
            raise RuntimeError("FFmpeg decoder stdout pipe was not opened.")

        frames: list[bytes] = []
        try:
            with tqdm(desc="Video decode", unit="frame") as progress:
                while True:
                    frame = process.stdout.read(frame_size)
                    if not frame:
                        break
                    if len(frame) != frame_size:
                        raise PayloadFormatError("FFmpeg returned a partial raw frame.")
                    frames.append(frame)
                    progress.update(1)
        finally:
            finish_process(process)

        if not frames:
            raise PayloadFormatError("No frames were decoded from the video.")
        return frames

    def _recover_transport(self, frames: list[bytes]) -> tuple[VideoSettings, int, int, np.ndarray]:
        """Extract transport header from frame data."""
        settings = VideoSettings(width=self.width, height=self.height)
        settings.validate()
        header_bits = np.concatenate([frame_to_bits(frame, settings) for frame in frames])
        header_len = TRANSPORT_HEADER_REPEATS * TRANSPORT_HEADER_SIZE
        header_bytes = bits_to_bytes(header_bits[:header_len * 8], header_len)
        recovered_settings, ecc_symbols, encoded_len = parse_transport_header(header_bytes)
        return recovered_settings, ecc_symbols, encoded_len, header_bits
