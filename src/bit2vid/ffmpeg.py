"""FFmpeg process helpers."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import BinaryIO

from bit2vid.config import VideoSettings
from bit2vid.errors import FFmpegNotFoundError

LOGGER = logging.getLogger(__name__)


def _bundled_ffmpeg_candidates(ffmpeg_path: str | None = None) -> list[Path]:
    """Return FFmpeg candidates, with optional custom path first."""
    candidates: list[Path] = []

    if ffmpeg_path:
        candidates.append(Path(ffmpeg_path))

    package_root = Path(__file__).resolve().parents[2]
    executable_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    candidates.extend(
        [
            Path.cwd() / "bin" / executable_name,
            package_root / "bin" / executable_name,
            package_root.parent / "bin" / executable_name,
        ]
    )
    return candidates


def require_ffmpeg(ffmpeg_path: str | None = None) -> str:
    """Return the FFmpeg executable path or raise a clear error."""

    for candidate in _bundled_ffmpeg_candidates(ffmpeg_path):
        if candidate.is_file():
            LOGGER.debug("Using FFmpeg: %s", candidate)
            return str(candidate)

    executable = shutil.which("ffmpeg")
    if executable is None:
        raise FFmpegNotFoundError("FFmpeg was not found in the specified path, ./bin, or PATH.")
    LOGGER.debug("Using FFmpeg from PATH: %s", executable)
    return executable


def start_encoder(
    output_path: Path, settings: VideoSettings, ffmpeg_path: str | None = None
) -> subprocess.Popen[bytes]:
    """Start FFmpeg for raw grayscale frame input."""

    executable = require_ffmpeg(ffmpeg_path)
    command = [
        executable,
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        settings.pix_fmt,
        "-s:v",
        f"{settings.width}x{settings.height}",
        "-r",
        str(settings.fps),
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        settings.preset,
        "-crf",
        str(settings.crf),
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    LOGGER.debug("Starting FFmpeg encoder: %s", " ".join(command))
    return subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def start_decoder(input_path: Path, ffmpeg_path: str | None = None) -> subprocess.Popen[bytes]:
    """Start FFmpeg for raw grayscale frame output."""

    executable = require_ffmpeg(ffmpeg_path)
    command = [
        executable,
        "-i",
        str(input_path),
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "pipe:1",
    ]
    LOGGER.debug("Starting FFmpeg decoder: %s", " ".join(command))
    return subprocess.Popen(
        command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def finish_process(process: subprocess.Popen[bytes], stream: BinaryIO | None = None) -> None:
    """Close a pipe and raise when FFmpeg exits with an error."""

    if stream is not None:
        stream.close()
    stderr = b""
    if process.stderr is not None:
        stderr = process.stderr.read()

    rc = process.wait()
    if rc != 0:
        raise RuntimeError(f"FFmpeg exited with code {rc}: {stderr.decode()}")
