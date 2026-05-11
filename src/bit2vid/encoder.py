"""High-level binary-to-MP4 encoder."""

from __future__ import annotations

import logging
from pathlib import Path

from tqdm import tqdm

from bit2vid.config import DEFAULT_PBKDF2_ITERATIONS, VideoSettings
from bit2vid.crypto import encrypt_payload
from bit2vid.ecc import ReedSolomonLayer
from bit2vid.ffmpeg import finish_process, start_encoder
from bit2vid.transport import bits_to_frames, bytes_to_bits, build_transport_header

LOGGER = logging.getLogger(__name__)


class VideoEncoder:
    """Encode arbitrary binary input into a resilient encrypted MP4 video."""

    def __init__(
        self,
        settings: VideoSettings,
        ecc_symbols: int,
        pbkdf2_iterations: int = DEFAULT_PBKDF2_ITERATIONS,
    ) -> None:
        self.settings = settings
        self.settings.validate()
        self.ecc = ReedSolomonLayer(ecc_symbols)
        self.pbkdf2_iterations = pbkdf2_iterations

    def encode_file(
        self, input_path: Path, output_path: Path, password: str, ffmpeg_path: str | None = None
    ) -> None:
        """Encode an input file to an MP4 container."""

        if not input_path.is_file():
            raise FileNotFoundError(f"Input file does not exist: {input_path}")
        if output_path.exists() and output_path.is_dir():
            raise IsADirectoryError(f"Output path is a directory: {output_path}")

        LOGGER.info("Reading input file: %s", input_path)
        plain = input_path.read_bytes()
        LOGGER.info("Encrypting %d bytes with AES-256-GCM.", len(plain))
        encrypted = encrypt_payload(plain, password, self.pbkdf2_iterations)
        protected = self.ecc.encode(encrypted)
        transport_header = build_transport_header(
            self.settings, self.ecc.ecc_symbols, len(protected)
        )
        bitstream = bytes_to_bits(transport_header + protected)
        frames = bits_to_frames(bitstream, self.settings)

        LOGGER.info(
            "Writing %d frames at %dx%d with %dx%d macro-block grid.",
            len(frames),
            self.settings.width,
            self.settings.height,
            self.settings.blocks_x,
            self.settings.blocks_y,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        process = start_encoder(output_path, self.settings, ffmpeg_path)
        if process.stdin is None:
            raise RuntimeError("FFmpeg encoder stdin pipe was not opened.")

        try:
            for frame in tqdm(frames, desc="Video encode", unit="frame"):
                process.stdin.write(frame.tobytes())
        except BrokenPipeError as exc:
            raise RuntimeError("FFmpeg encoder pipe broke while writing frames.") from exc
        finally:
            finish_process(process, process.stdin)

        LOGGER.info("Encoded video written to: %s", output_path)
