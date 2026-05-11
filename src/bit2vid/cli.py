"""Command-line interface for Bit2Vid."""

from __future__ import annotations

import argparse
import getpass
import logging
import sys
from pathlib import Path

from bit2vid.config import (
    DEFAULT_BLOCK_SIZE,
    DEFAULT_CRF,
    DEFAULT_ECC_SYMBOLS,
    DEFAULT_FPS,
    DEFAULT_HEIGHT,
    DEFAULT_PBKDF2_ITERATIONS,
    DEFAULT_WIDTH,
    TRANSPORT_HEADER_REPEATS,
    TRANSPORT_HEADER_SIZE,
    VideoSettings,
)
from bit2vid.ecc import ReedSolomonLayer, _ECC_HEADER_STRUCT
from bit2vid.decoder import VideoDecoder
from bit2vid.encoder import VideoEncoder
from bit2vid.errors import Bit2VidError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bit2vid",
        description="Encrypt binary files into resilient MP4 video frames and recover them.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
    parser.add_argument(
        "--ffmpeg", help="Path to FFmpeg executable (optional, searches PATH if omitted)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    encode = subparsers.add_parser("encode", help="Pack a binary file into an MP4 video.")
    encode.add_argument("input", type=Path, help="Input binary file.")
    encode.add_argument("output", type=Path, help="Output MP4 file.")
    encode.add_argument("--password", help="Password. Omit to prompt securely.")
    encode.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    encode.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    encode.add_argument(
        "--block-size", type=int, default=DEFAULT_BLOCK_SIZE, choices=[8, 10, 12, 16, 20]
    )
    encode.add_argument("--fps", type=int, default=DEFAULT_FPS)
    encode.add_argument("--crf", type=int, default=DEFAULT_CRF)
    encode.add_argument("--preset", default="slow")
    encode.add_argument("--ecc-symbols", type=int, default=DEFAULT_ECC_SYMBOLS)
    encode.add_argument("--pbkdf2-iterations", type=int, default=DEFAULT_PBKDF2_ITERATIONS)

    decode = subparsers.add_parser("decode", help="Extract and decrypt a file from an MP4 video.")
    decode.add_argument("input", type=Path, help="Input MP4 file.")
    decode.add_argument("output", type=Path, help="Output binary file.")
    decode.add_argument("--password", help="Password. Omit to prompt securely.")
    decode.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    decode.add_argument("--height", type=int, default=DEFAULT_HEIGHT)

    estimate = subparsers.add_parser(
        "estimate", help="Estimate video size for a given binary file."
    )
    estimate.add_argument("input", type=Path, help="Input binary file.")
    estimate.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    estimate.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    estimate.add_argument(
        "--block-size", type=int, default=DEFAULT_BLOCK_SIZE, choices=[8, 10, 12, 16, 20]
    )
    estimate.add_argument("--fps", type=int, default=DEFAULT_FPS)
    estimate.add_argument("--ecc-symbols", type=int, default=DEFAULT_ECC_SYMBOLS)

    return parser


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _password(value: str | None, confirm: bool) -> str:
    if value is not None:
        return value
    password = getpass.getpass("Password: ")
    if confirm:
        repeated = getpass.getpass("Confirm password: ")
        if password != repeated:
            raise ValueError("Passwords do not match.")
    return password


def _estimate_payload_size(input_path: Path, ecc_symbols: int) -> int:
    """Estimate total payload size after ECC."""
    file_size = input_path.stat().st_size
    # Rough estimate: crypto header (128 bytes) + ciphertext (file_size) + ECC overhead
    ecc = ReedSolomonLayer(ecc_symbols)
    estimated_encrypted = 128 + file_size
    return ecc._ECC_HEADER_STRUCT.size + (
        (estimated_encrypted + ecc.data_symbols - 1) // ecc.data_symbols
    ) * (ecc.data_symbols + ecc.ecc_symbols)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    try:
        if args.command == "encode":
            settings = VideoSettings(
                width=args.width,
                height=args.height,
                block_size=args.block_size,
                fps=args.fps,
                crf=args.crf,
                preset=args.preset,
            )
            encoder = VideoEncoder(
                settings=settings,
                ecc_symbols=args.ecc_symbols,
                pbkdf2_iterations=args.pbkdf2_iterations,
            )
            encoder.encode_file(
                args.input,
                args.output,
                _password(args.password, confirm=True),
                ffmpeg_path=args.ffmpeg,
            )
        elif args.command == "decode":
            decoder = VideoDecoder(width=args.width, height=args.height)
            decoder.decode_file(
                args.input,
                args.output,
                _password(args.password, confirm=False),
                ffmpeg_path=args.ffmpeg,
            )
        elif args.command == "estimate":
            settings = VideoSettings(
                width=args.width,
                height=args.height,
                block_size=args.block_size,
                fps=args.fps,
            )
            settings.validate()

            file_size = args.input.stat().st_size
            ecc = ReedSolomonLayer(args.ecc_symbols)

            # Estimate encrypted payload size (includes crypto header + ciphertext)
            crypto_header_size = 128
            estimated_encrypted = crypto_header_size + file_size

            # Calculate ECC protected size
            num_chunks = (estimated_encrypted + ecc.data_symbols - 1) // ecc.data_symbols
            codeword_size = ecc.data_symbols + ecc.ecc_symbols
            ecc_protected_size = _ECC_HEADER_STRUCT.size + num_chunks * codeword_size

            # Calculate transport header + payload size
            transport_header_size = TRANSPORT_HEADER_REPEATS * TRANSPORT_HEADER_SIZE
            total_bits = (transport_header_size + ecc_protected_size) * 8

            # Calculate frame requirements
            bits_per_frame = settings.blocks_x * settings.blocks_y
            frame_count = (total_bits + bits_per_frame - 1) // bits_per_frame

            # Estimate video duration and size
            duration_seconds = frame_count / settings.fps

            print(f"\n=== Bit2Vid Estimate ===")
            print(f"Input file size:           {file_size:,} bytes")
            print(f"Crypto overhead:           {crypto_header_size} bytes")
            print(f"Encrypted size:            {estimated_encrypted:,} bytes")
            print(f"ECC redundancy:            {ecc.redundancy_ratio:.1%}")
            print(f"ECC protected size:        {ecc_protected_size:,} bytes")
            print(
                f"Transport + payload:       {transport_header_size + ecc_protected_size:,} bytes"
            )
            print(f"Total bits:                {total_bits:,} bits")
            print(f"Video resolution:          {settings.width}x{settings.height}")
            print(f"Bits per frame:            {bits_per_frame}")
            print(f"Required frames:           {frame_count:,}")
            print(f"Video duration @ {settings.fps} FPS:   {duration_seconds:.1f} seconds")
            print(
                f"Video bitrate estimate:    ~{settings.crf} CRF (variable, depends on compression)"
            )
            print()

        else:
            parser.error("Unknown command.")
    except (Bit2VidError, OSError, RuntimeError, ValueError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
