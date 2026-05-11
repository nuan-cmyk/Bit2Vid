"""Command-line interface for CipherFrame Vault."""

from __future__ import annotations

import argparse
import getpass
import logging
import sys
from pathlib import Path

from cipherframe.config import (
    DEFAULT_BLOCK_SIZE,
    DEFAULT_CRF,
    DEFAULT_ECC_SYMBOLS,
    DEFAULT_FPS,
    DEFAULT_HEIGHT,
    DEFAULT_PBKDF2_ITERATIONS,
    DEFAULT_WIDTH,
    VideoSettings,
)
from cipherframe.decoder import VideoDecoder
from cipherframe.encoder import VideoEncoder
from cipherframe.errors import CipherFrameError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bit2vid",
        description="Encrypt binary files into resilient MP4 video frames and recover them.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    encode = subparsers.add_parser("encode", help="Pack a binary file into an MP4 video.")
    encode.add_argument("input", type=Path, help="Input binary file.")
    encode.add_argument("output", type=Path, help="Output MP4 file.")
    encode.add_argument("--password", help="Password. Omit to prompt securely.")
    encode.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    encode.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    encode.add_argument("--block-size", type=int, default=DEFAULT_BLOCK_SIZE, choices=[8, 10, 12, 16, 20])
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
            encoder.encode_file(args.input, args.output, _password(args.password, confirm=True))
        elif args.command == "decode":
            decoder = VideoDecoder(width=args.width, height=args.height)
            decoder.decode_file(args.input, args.output, _password(args.password, confirm=False))
        else:
            parser.error("Unknown command.")
    except (CipherFrameError, OSError, RuntimeError, ValueError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
