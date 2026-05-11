"""Video transport header and bit/frame conversion helpers."""

from __future__ import annotations

import struct

import numpy as np

from bit2vid.config import (
    TRANSPORT_HEADER_REPEATS,
    TRANSPORT_HEADER_SIZE,
    TRANSPORT_MAGIC,
    VERSION,
    VideoSettings,
)
from bit2vid.errors import PayloadFormatError

_TRANSPORT_HEADER_STRUCT = struct.Struct(">8sB3xHHHHQ")


def build_transport_header(settings: VideoSettings, ecc_symbols: int, encoded_len: int) -> bytes:
    """Build the repeated video transport header."""

    header = _TRANSPORT_HEADER_STRUCT.pack(
        TRANSPORT_MAGIC,
        VERSION,
        settings.width,
        settings.height,
        settings.block_size,
        ecc_symbols,
        encoded_len,
    )
    return header.ljust(TRANSPORT_HEADER_SIZE, b"\0") * TRANSPORT_HEADER_REPEATS


def parse_transport_header(repeated_header: bytes) -> tuple[VideoSettings, int, int]:
    """Recover video settings, ECC symbols, and encoded length by majority vote."""

    expected = TRANSPORT_HEADER_SIZE * TRANSPORT_HEADER_REPEATS
    if len(repeated_header) < expected:
        raise PayloadFormatError("Transport header is truncated.")

    blocks = np.frombuffer(repeated_header[:expected], dtype=np.uint8).reshape(
        TRANSPORT_HEADER_REPEATS, TRANSPORT_HEADER_SIZE
    )
    voted_bits = []
    for bit_index in range(8):
        bits = (blocks >> (7 - bit_index)) & 1
        voted_bits.append((bits.sum(axis=0) >= ((TRANSPORT_HEADER_REPEATS // 2) + 1)).astype(np.uint8))
    voted = np.packbits(np.stack(voted_bits, axis=1), axis=1, bitorder="big").reshape(
        TRANSPORT_HEADER_SIZE
    )

    magic, version, width, height, block_size, ecc_symbols, encoded_len = (
        _TRANSPORT_HEADER_STRUCT.unpack(bytes(voted[: _TRANSPORT_HEADER_STRUCT.size]))
    )
    if magic != TRANSPORT_MAGIC:
        raise PayloadFormatError("Invalid transport magic.")
    if version != VERSION:
        raise PayloadFormatError(f"Unsupported transport version: {version}.")

    settings = VideoSettings(width=width, height=height, block_size=block_size)
    settings.validate()
    return settings, ecc_symbols, encoded_len


def bytes_to_bits(data: bytes) -> np.ndarray:
    """Convert bytes to a big-endian bit vector."""

    return np.unpackbits(np.frombuffer(data, dtype=np.uint8), bitorder="big")


def bits_to_bytes(bits: np.ndarray, byte_count: int | None = None) -> bytes:
    """Convert a bit vector to bytes, trimming to byte_count when supplied."""

    remainder = len(bits) % 8
    if remainder:
        bits = np.pad(bits, (0, 8 - remainder), constant_values=0)
    packed = np.packbits(bits.astype(np.uint8), bitorder="big").tobytes()
    if byte_count is not None:
        return packed[:byte_count]
    return packed


def bits_to_frames(bits: np.ndarray, settings: VideoSettings) -> list[np.ndarray]:
    """Render bits into black/white grayscale video frames with calibration blocks."""

    settings.validate()
    capacity = settings.bits_per_frame
    frame_count = int(np.ceil(len(bits) / capacity))
    padded = np.pad(bits, (0, frame_count * capacity - len(bits)), constant_values=0)
    frames: list[np.ndarray] = []
    
    for frame_idx, frame_bits in enumerate(padded.reshape(frame_count, settings.blocks_y, settings.blocks_x)):
        frame = np.repeat(np.repeat(frame_bits * 255, settings.block_size, axis=0), settings.block_size, axis=1)
        frame = frame.astype(np.uint8, copy=False)
        
        # Add calibration blocks in corners (white = 255, black = 0)
        block_sz = settings.block_size
        # Top-left: white (255)
        frame[:block_sz, :block_sz] = 255
        # Top-right: black (0)
        frame[:block_sz, -block_sz:] = 0
        # Bottom-left: black (0)
        frame[-block_sz:, :block_sz] = 0
        # Bottom-right: white (255)
        frame[-block_sz:, -block_sz:] = 255
        
        # Add frame index in center area (simple binary encoding in 2x2 region)
        frame_idx_bits = format(frame_idx % 256, '08b')
        center_y, center_x = settings.height // 2, settings.width // 2
        for bit_idx, bit in enumerate(frame_idx_bits):
            y_offset = center_y + (bit_idx // 4) * block_sz
            x_offset = center_x + (bit_idx % 4) * block_sz
            if 0 <= y_offset < settings.height and 0 <= x_offset < settings.width:
                frame[y_offset:y_offset + block_sz, x_offset:x_offset + block_sz] = (
                    255 if bit == '1' else 0
                )
        
        frames.append(frame)
    
    return frames


def frame_to_bits(frame: bytes, settings: VideoSettings) -> np.ndarray:
    """Decode one raw grayscale frame by averaging each block center.
    
    Skips calibration blocks in corners and frame index region.
    """

    array = np.frombuffer(frame, dtype=np.uint8).reshape(settings.height, settings.width)
    block = settings.block_size
    quarter = max(1, block // 4)
    
    # Create mask to exclude calibration blocks and frame index area
    mask = np.ones((settings.blocks_y, settings.blocks_x), dtype=bool)
    
    # Exclude corners (calibration blocks)
    mask[0, 0] = False  # Top-left
    mask[0, -1] = False  # Top-right
    mask[-1, 0] = False  # Bottom-left
    mask[-1, -1] = False  # Bottom-right
    
    # Exclude frame index region (center 2x2 in block coordinates)
    center_block_y = settings.blocks_y // 2
    center_block_x = settings.blocks_x // 2
    for dy in range(-1, 3):
        for dx in range(-1, 3):
            by, bx = center_block_y + dy, center_block_x + dx
            if 0 <= by < settings.blocks_y and 0 <= bx < settings.blocks_x:
                mask[by, bx] = False
    
    center = array.reshape(settings.blocks_y, block, settings.blocks_x, block)[
        :, quarter : block - quarter, :, quarter : block - quarter
    ]
    means = center.mean(axis=(1, 3))
    bits = (means >= 128).astype(np.uint8)
    
    # Apply mask: set excluded blocks to 0
    bits = bits * mask
    
    return bits.reshape(-1)
