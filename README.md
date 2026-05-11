# Bit2Vid

Bit2Vid is a command-line utility for converting arbitrary binary files into resilient
MP4 video containers and restoring them back byte-for-byte. It encrypts the payload,
adds Reed-Solomon redundancy, and renders the protected bitstream as high-contrast
black-and-white macro-blocks suitable for H.264 encoding.

The tool is intended for archival and transport experiments where binary data must
survive video compression while remaining confidential. Payloads are encrypted with
AES-256-GCM, authenticated before extraction, and protected with configurable
error-correction parity before being written to video frames.

## Core Capabilities

- AES-256-GCM encryption with PBKDF2-based key derivation.
- Reed-Solomon error correction with configurable parity symbols.
- 1920x1080 black-and-white frame generation using NumPy.
- Direct FFmpeg rawvideo piping through `stdin` and `stdout`.
- H.264 MP4 output through `libx264`, configurable `--crf`, and `slow` preset by default.
- Robust block decoding by averaging the center region of each macro-block.
- Typed OOP implementation with `VideoEncoder` and `VideoDecoder`.
- Structured logging, `tqdm` progress bars, and clear runtime validation.

## Requirements

- Python 3.10+
- FFmpeg bundled in `bin/` or available in `PATH`

Install the package and dependencies:

```powershell
python -m pip install -e .
```

Bit2Vid looks for FFmpeg in this order:

1. `./bin/ffmpeg.exe` from the current project directory.
2. `bin/ffmpeg.exe` next to the installed source package.
3. `ffmpeg` from the system `PATH`.

## Usage

Encode a file into MP4:

```powershell
bit2vid encode input.bin vault.mp4
```

Decode the MP4 back into the original file:

```powershell
bit2vid decode vault.mp4 restored.bin
```

Common options:

```powershell
bit2vid encode input.bin vault.mp4 --block-size 8 --crf 18 --ecc-symbols 64
bit2vid decode vault.mp4 restored.bin --password "test-password"
```

For interactive use, omit `--password`; Bit2Vid will prompt securely.

## Encoding Model

1. The input file is encrypted with AES-256-GCM.
2. The encrypted payload is split into Reed-Solomon codewords.
3. The protected byte stream is converted to bits.
4. Bits are rendered as black or white macro-blocks in 1920x1080 frames.
5. Raw frames are streamed into FFmpeg and encoded as MP4.

During decoding, Bit2Vid extracts grayscale raw frames from FFmpeg, estimates each
bit by averaging the central area of its macro-block, repairs recoverable corruption
with Reed-Solomon, and authenticates/decrypts the original payload.

## Reliability Notes

The default Reed-Solomon setting uses 64 parity symbols per 255-byte codeword:
191 data bytes plus 64 parity bytes. This provides roughly 33% redundancy and can
recover up to 32 corrupted bytes per codeword.

Lower CRF values preserve block boundaries better and increase output size. CRF 18
is a practical default. For aggressive transcoding or noisy pipelines, increase
`--block-size` and `--ecc-symbols`.

## Development

Run tests:

```powershell
python -m pytest -q
```

Run linting:

```powershell
python -m ruff check .
```
