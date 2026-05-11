# CipherFrame Vault

CipherFrame Vault is a professional command-line utility that encrypts any binary file,
adds Reed-Solomon redundancy, and stores the resulting bitstream as black-and-white
macro-blocks inside an MP4 video container.

It is designed for resilient archival experiments where the video may pass through
lossy H.264 compression. The payload is protected with AES-256-GCM and encoded with
Reed-Solomon parity before visualization.

## Features

- AES-256-GCM encryption with PBKDF2 key derivation.
- Reed-Solomon error correction with configurable parity.
- 1920x1080 black/white frame generation using NumPy.
- FFmpeg rawvideo piping through `stdin` and `stdout`.
- Robust macro-block decoding by averaging the center region of each block.
- Typed OOP architecture with `VideoEncoder` and `VideoDecoder`.
- CLI logging, progress bars, and explicit FFmpeg availability checks.

## Requirements

- Python 3.10+
- FFmpeg available in `PATH`

Install Python dependencies:

```powershell
python -m pip install -e .
```

## Usage

Encode a file into MP4:

```powershell
cipherframe encode input.bin vault.mp4
```

Decode it back:

```powershell
cipherframe decode vault.mp4 restored.bin
```

Useful options:

```powershell
cipherframe encode input.bin vault.mp4 --block-size 8 --crf 18 --ecc-symbols 64
cipherframe decode vault.mp4 restored.bin --password "test-password"
```

For interactive use, omit `--password`; the CLI will prompt securely.

## Notes

The default Reed-Solomon setting uses 64 parity symbols per 255-byte codeword
(`191` data bytes + `64` parity bytes), giving roughly 33% redundancy and recovery
from up to 32 corrupted bytes per codeword.

Lower CRF values preserve block edges better and increase the output file size.
CRF 18 is a practical default. If the video is transcoded aggressively, use larger
macro-blocks and more parity.

## Repository

Suggested GitHub repository name: `cipherframe-vault`

Suggested description: `Encrypt and encode arbitrary binary files into resilient MP4 video frames.`

