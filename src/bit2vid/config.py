"""Shared encoding constants and configuration."""

from __future__ import annotations

from dataclasses import dataclass


MAGIC = b"CFVLT001"
TRANSPORT_MAGIC = b"CFVID001"
VERSION = 1
TRANSPORT_HEADER_SIZE = 64
TRANSPORT_HEADER_REPEATS = 7
PAYLOAD_HEADER_SIZE = 128
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_BLOCK_SIZE = 8
DEFAULT_FPS = 30
DEFAULT_CRF = 18
DEFAULT_ECC_SYMBOLS = 64
DEFAULT_PBKDF2_ITERATIONS = 600_000


@dataclass(frozen=True)
class VideoSettings:
    """Video layout and compression settings."""

    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    block_size: int = DEFAULT_BLOCK_SIZE
    fps: int = DEFAULT_FPS
    crf: int = DEFAULT_CRF
    preset: str = "slow"
    pix_fmt: str = "gray"

    @property
    def blocks_x(self) -> int:
        return self.width // self.block_size

    @property
    def blocks_y(self) -> int:
        return self.height // self.block_size

    @property
    def bits_per_frame(self) -> int:
        return self.blocks_x * self.blocks_y

    @property
    def frame_bytes(self) -> int:
        return self.width * self.height

    def validate(self) -> None:
        """Validate configuration constraints."""
        if self.width % self.block_size != 0:
            raise ValueError(f"width ({self.width}) must be divisible by block_size ({self.block_size})")
        if self.height % self.block_size != 0:
            raise ValueError(f"height ({self.height}) must be divisible by block_size ({self.block_size})")
        if not 1 <= self.fps <= 60:
            raise ValueError(f"fps must be between 1 and 60, got {self.fps}")
