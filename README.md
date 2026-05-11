# Bit2Vid 🎬🔐

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![GitHub Actions](https://github.com/bit2vid/bit2vid/actions/workflows/ci.yml/badge.svg)](https://github.com/bit2vid/bit2vid/actions)

**Encrypt arbitrary binary files into resilient, authenticated MP4 video containers.**

Bit2Vid is a command-line tool that converts any binary file into a high-contrast MP4 video, protecting it with:
- 🔒 **AES-256-GCM encryption** (authenticated)
- ✓ **Reed-Solomon error correction** (32+ errors per frame)
- 📺 **H.264 video encoding** (compatible with all modern players)
- 🎯 **Binary-precise recovery** (byte-for-byte restoration)

Perfect for archival, steganography experiments, and transporting sensitive data through video pipelines.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Commands](#commands)
4. [Options](#options)
5. [Cryptography](#cryptography)
6. [Error Correction](#error-correction)
7. [Advanced Usage](#advanced-usage)
8. [Architecture](#architecture)
9. [Performance](#performance)
10. [Development](#development)
11. [Security](#security)

---

## Quick Start

### Encode a file

```bash
bit2vid encode secret.bin output.mp4 --password "strong-password"
```

### Decode a file

```bash
bit2vid decode output.mp4 restored.bin --password "strong-password"
```

### Estimate video size before encoding

```bash
bit2vid estimate secret.bin
```

---

## Installation

### Requirements

- **Python 3.10** or higher
- **FFmpeg** (with libx264 encoder)

### Install from source

```bash
# Clone the repository
git clone https://github.com/bit2vid/bit2vid.git
cd bit2Vid

# Install in development mode
python -m pip install -e ".[dev]"

# Or install production version
python -m pip install .
```

### Verify installation

```bash
bit2vid --help
bit2vid --version  # Show version
```

---

## Commands

### `encode` - Encrypt and encode binary file to MP4

**Signature:**
```bash
bit2vid encode INPUT OUTPUT [OPTIONS]
```

**Basic example:**
```bash
bit2vid encode data.bin video.mp4
```

**With custom settings:**
```bash
bit2vid encode data.bin video.mp4 \
  --password "my-secret" \
  --width 1920 --height 1080 \
  --block-size 8 \
  --fps 30 \
  --crf 18 \
  --ecc-symbols 64 \
  --pbkdf2-iterations 600000
```

**Interactive password prompt** (if --password omitted):
```bash
bit2vid encode data.bin video.mp4
# You will be prompted to enter and confirm password
```

**Custom FFmpeg path:**
```bash
bit2vid encode data.bin video.mp4 --ffmpeg /custom/path/ffmpeg
```

**Options for `encode`:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--password` | string | (prompt) | Encryption password. If omitted, prompts securely. |
| `--width` | int | 1920 | Frame width in pixels (must be divisible by block-size) |
| `--height` | int | 1080 | Frame height in pixels (must be divisible by block-size) |
| `--block-size` | {8,10,12,16,20} | 8 | Macro-block size in pixels. Larger blocks = more robust to corruption but fewer data bits per frame |
| `--fps` | int | 30 | Frames per second in output video |
| `--crf` | int | 18 | Constant Rate Factor (0-51, lower = higher quality, larger file) |
| `--preset` | string | "slow" | FFmpeg encoding preset: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow |
| `--ecc-symbols` | int | 64 | Reed-Solomon parity symbols (1-127). Higher = more error tolerance but larger file |
| `--pbkdf2-iterations` | int | 600000 | PBKDF2 iterations for key derivation. Higher = slower but more secure |
| `--ffmpeg` | path | (auto-detect) | Path to FFmpeg executable |
| `--verbose` | flag | False | Enable debug logging |

---

### `decode` - Extract and decrypt MP4 back to binary file

**Signature:**
```bash
bit2vid decode INPUT OUTPUT [OPTIONS]
```

**Basic example:**
```bash
bit2vid decode video.mp4 restored.bin
```

**With custom settings:**
```bash
bit2vid decode video.mp4 restored.bin \
  --password "my-secret" \
  --width 1920 \
  --height 1080 \
  --ffmpeg /custom/path/ffmpeg
```

**Options for `decode`:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--password` | string | (prompt) | Decryption password. If omitted, prompts securely. |
| `--width` | int | 1920 | Frame width (must match encoding) |
| `--height` | int | 1080 | Frame height (must match encoding) |
| `--ffmpeg` | path | (auto-detect) | Path to FFmpeg executable |
| `--verbose` | flag | False | Enable debug logging |

**Process:**
1. Extract frames from MP4 via FFmpeg
2. Recover transport header by majority voting
3. Apply Reed-Solomon error correction
4. Decrypt AES-256-GCM payload
5. Verify SHA256 hash
6. Write restored file

---

### `estimate` - Calculate video size without encoding

**Signature:**
```bash
bit2vid estimate INPUT [OPTIONS]
```

**Example:**
```bash
bit2vid estimate data.bin
```

**Output example:**
```
=== Bit2Vid Estimate ===
Input file size:           1,048,576 bytes
Crypto overhead:           128 bytes
Encrypted size:            1,048,704 bytes
ECC redundancy:            33.5%
ECC protected size:        1,398,272 bytes
Transport + payload:       1,397,632 bytes
Total bits:                11,181,056 bits
Video resolution:          1920x1080
Bits per frame:            2,073,600
Required frames:           6 frames
Video duration @ 30 FPS:   0.2 seconds
Video bitrate estimate:    ~18 CRF (variable, depends on compression)
```

**Options for `estimate`:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--width` | int | 1920 | Estimated frame width |
| `--height` | int | 1080 | Estimated frame height |
| `--block-size` | {8,10,12,16,20} | 8 | Macro-block size |
| `--fps` | int | 30 | Estimated frames per second |
| `--ecc-symbols` | int | 64 | Reed-Solomon parity symbols |

---

## Options

### Global options (available for all commands)

```bash
bit2vid [--ffmpeg PATH] [--verbose] {encode,decode,estimate} ...
```

| Option | Type | Description |
|--------|------|-------------|
| `--ffmpeg PATH` | path | Path to FFmpeg executable. If not provided, searches in ./bin, system PATH |
| `--verbose` | flag | Enable DEBUG-level logging (default: INFO) |
| `-h, --help` | flag | Show help message |

### FFmpeg path resolution

Bit2Vid searches for FFmpeg in this order:

1. **Custom path** (if `--ffmpeg /path/to/ffmpeg` provided)
2. **./bin/ffmpeg.exe** (Windows) or **./bin/ffmpeg** (Unix)
3. **Package directory bin/ffmpeg**
4. **System PATH** (via `shutil.which("ffmpeg")`)

---

## Cryptography

### Encryption Algorithm

Bit2Vid uses **AES-256-GCM** (Galois/Counter Mode) for authenticated encryption:

- **Key size:** 256 bits (32 bytes)
- **Nonce size:** 96 bits (12 bytes, randomly generated)
- **Authentication tag:** 128 bits (16 bytes)
- **Mode:** GCM (provides both confidentiality and authenticity)

### Key Derivation

Password → PBKDF2 (SHA-256) → 256-bit AES key

```
Key = PBKDF2(
    password,
    salt=16_random_bytes,
    iterations=600_000,  # OWASP 2024 recommendation
    hash_function=SHA256,
    output_length=32_bytes
)
```

### Payload Structure

```
[128-byte header] [encrypted_data]

Header format:
- Magic: "CFVLT001" (8 bytes)
- Version: 1 (1 byte)
- Padding: 3 bytes
- PBKDF2 iterations: uint32 (4 bytes)
- Salt: 16 bytes (randomly generated)
- Nonce: 12 bytes (randomly generated)
- Authentication tag: 16 bytes
- Ciphertext length: uint64 (8 bytes)
- SHA256(plaintext): 32 bytes
[remaining: 40 bytes of padding]
```

### Security Properties

✓ **Confidentiality:** No plaintext leakage through ciphertext  
✓ **Authenticity:** Forgery impossible without knowing password  
✓ **Forward secrecy:** Compromising one file doesn't affect others (random nonce/salt)  
⚠ **Not resistant to side-channel attacks:** Timing, power consumption analysis possible

### Recommendations

- **Strong passwords:** Use 16+ random characters or 5+ word passphrase
- **Unique passwords:** Don't reuse passwords across multiple encoded videos
- **Secure storage:** Store passwords in password managers, never in plain text
- **Environment variables:** In scripts, use `$env:BIT2VID_PASSWORD` instead of hardcoding

---

## Error Correction

### Reed-Solomon Codes

Bit2Vid applies **Reed-Solomon error correction** to protect against video compression artifacts.

**Parameters:**

```
Codeword size: 255 bytes (fixed, standard RS limit)
Data symbols: 255 - ecc_symbols
Parity symbols: ecc_symbols (configurable, 1-127)
```

**Default setting (64 parity symbols):**

```
191 data bytes + 64 parity bytes = 255 codeword
Redundancy: 64/191 ≈ 33.5%
Correction capability: Up to 32 byte errors per codeword
```

**Example: Effect of ECC settings**

| ECC Symbols | Data per Codeword | Redundancy | Max Errors | File Size Growth |
|-------------|-------------------|------------|-----------|-----------------|
| 16 | 239 | 6.7% | 8 | +7% |
| 32 | 223 | 14.3% | 16 | +15% |
| **64** | **191** | **33.5%** | **32** | **+34%** |
| 96 | 159 | 60.4% | 48 | +61% |
| 127 | 128 | 99.2% | 63 | +100% |

**How it works:**

1. **Encoding:** Data split into 191-byte chunks → RS adds 64 parity bytes
2. **Transmission:** Through video codec (lossy, may corrupt bytes)
3. **Decoding:** RS can correct up to 32 arbitrary byte errors per codeword
4. **Validation:** If >32 errors, recovery fails with clear error message

---

## Advanced Usage

### Batch encoding multiple files

```bash
# Encode all .exe files to video
Get-ChildItem *.exe | ForEach-Object {
    bit2vid encode $_.Name "$($_.BaseName).mp4" --password "batch-pwd"
}
```

### Estimate before committing to large file

```bash
# Check size before encoding 100MB file
bit2vid estimate huge_file.bin --ecc-symbols 96

# Then encode with same settings
bit2vid encode huge_file.bin huge_file.mp4 --ecc-symbols 96
```

### Custom video parameters for specific use cases

**For maximum resilience (aggressive compression expected):**
```bash
bit2vid encode data.bin video.mp4 \
  --block-size 16 \
  --ecc-symbols 96 \
  --crf 28 \
  --preset slower
```

**For fastest encoding (local archival, no transmission):**
```bash
bit2vid encode data.bin video.mp4 \
  --block-size 8 \
  --ecc-symbols 32 \
  --crf 18 \
  --preset fast
```

**For minimum file size (bandwidth limited):**
```bash
bit2vid encode data.bin video.mp4 \
  --block-size 20 \
  --ecc-symbols 16 \
  --crf 51 \
  --preset ultrafast
```

### Debug mode with verbose logging

```bash
bit2vid encode data.bin video.mp4 --verbose 2>&1 | Tee-Object debug.log
```

Output includes:
- Frame rendering progress
- ECC encoding/decoding steps
- FFmpeg command and output
- Transport header details

### Using custom FFmpeg build

```bash
# Windows with custom build
bit2vid encode data.bin video.mp4 --ffmpeg "C:\ffmpeg\bin\ffmpeg.exe"

# Linux with custom build
bit2vid encode data.bin video.mp4 --ffmpeg /opt/ffmpeg/bin/ffmpeg
```

---

## Architecture

### Data Flow Diagram

```
ENCODING:
Input file → Encrypt (AES-256-GCM) → ECC encode (Reed-Solomon)
    → Transport header → Bits → Frames → FFmpeg → MP4 output

DECODING:
MP4 input → FFmpeg → Frames → Bits → Transport header (majority vote)
    → ECC decode → Decrypt (AES-256-GCM) → Verify → Output file
```

### Module Structure

```
bit2vid/
├── __init__.py              # Package exports
├── cli.py                   # Command-line interface (argparse)
├── config.py                # Constants & VideoSettings dataclass
├── crypto.py                # AES-256-GCM & PBKDF2 functions
├── ecc.py                   # Reed-Solomon layer (reedsolo wrapper)
├── encoder.py               # VideoEncoder class (high-level)
├── decoder.py               # VideoDecoder class (high-level)
├── ffmpeg.py                # FFmpeg process management
├── transport.py             # Bit/frame conversion & transport header
└── errors.py                # Custom exception classes
```

### Key Classes

**VideoSettings** (dataclass)
```python
@dataclass(frozen=True)
class VideoSettings:
    width: int = 1920
    height: int = 1080
    block_size: int = 8
    fps: int = 30
    crf: int = 18
    preset: str = "slow"
    pix_fmt: str = "gray"
```

**VideoEncoder**
```python
class VideoEncoder:
    def encode_file(
        self,
        input_path: Path,
        output_path: Path,
        password: str,
        ffmpeg_path: str | None = None
    ) -> None
```

**VideoDecoder**
```python
class VideoDecoder:
    def decode_file(
        self,
        input_path: Path,
        output_path: Path,
        password: str,
        ffmpeg_path: str | None = None
    ) -> None
```

---

## Performance

### Benchmarks (typical system: Python 3.10, 6-core CPU)

| File Size | Frames | Encode Time | Video Size | Redundancy |
|-----------|--------|-------------|-----------|-----------|
| 1 KB | 1 | ~2 sec | ~50 KB | ~100x |
| 100 KB | 1-2 | ~3-5 sec | ~2 MB | ~20x |
| 1 MB | 5-10 | ~10-20 sec | ~20 MB | ~20x |
| 10 MB | 50-100 | ~2-5 min | ~200 MB | ~20x |
| 100 MB | 500-1000 | ~20-40 min | ~2 GB | ~20x |

**Decode Time:** ~1-2x slower than encode (RS decoding is computationally expensive)

### Optimization Tips

1. **Use larger block-size** for faster frame generation
2. **Use lower ECC symbols** to reduce frame count
3. **Use FFmpeg preset "fast"** instead of "slow" for production
4. **Increase CRF** (lower quality) to reduce output file size

---

## Development

### Project structure

```
Bit2Vid/
├── src/bit2vid/              # Main package
├── tests/                    # Pytest test suite
├── .github/workflows/        # GitHub Actions CI/CD
│   ├── ci.yml               # pytest, ruff, build checks
│   └── release.yml          # Release & PyPI publish
├── pyproject.toml           # Python project metadata
├── README.md                # This file
├── SECURITY.md              # Security policy
└── LICENSE                  # MIT license
```

### Running tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_core.py::test_crypto_ecc_and_frame_roundtrip -v

# Run with coverage
python -m pytest tests/ --cov=src/bit2vid
```

### Linting and formatting

```bash
# Check code style
python -m ruff check src/ tests/

# Auto-fix issues
python -m ruff check src/ tests/ --fix

# Format code
python -m ruff format src/ tests/
```

### Building release

```bash
# Build wheels and source distribution
python -m build

# Check integrity
python -m twine check dist/*

# Upload to PyPI (requires token)
python -m twine upload dist/*
```

### Adding new features

1. Create feature branch: `git checkout -b feature/my-feature`
2. Implement & test locally
3. Run `ruff format` and `pytest`
4. Submit PR with description
5. GitHub Actions will validate automatically

---

## Security

**See [SECURITY.md](./SECURITY.md) for detailed security policy.**

### Threat Model

✓ **Protected against:**
- Password guessing (PBKDF2 with 600k iterations)
- Ciphertext tampering (AES-GCM authentication tag)
- Accidental corruption (Reed-Solomon error correction)

⚠ **Not protected against:**
- Weak passwords (use 16+ characters)
- Side-channel attacks (timing, power analysis)
- Quantum computers (no post-quantum cryptography)
- Compromised system (malware could steal keys)

### Reporting vulnerabilities

If you find a security issue, please **do not open a public issue**. Instead, email the maintainers with details.

---

## License

MIT License - see [LICENSE](./LICENSE) for details

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Run tests and linting
4. Submit a pull request

---

## Roadmap

- [ ] Argon2 key derivation (GPU-resistant)
- [ ] XChaCha20-Poly1305 cipher option
- [ ] Password strength meter in CLI
- [ ] HSM (Hardware Security Module) support
- [ ] GUI for non-technical users
- [ ] Streaming mode for large files
- [ ] Docker container
- [ ] Official PyPI release

---

## FAQ

**Q: Is my password stored?**  
A: No. The password is used once to derive the encryption key, then discarded. The key is never stored.

**Q: Can the video be played in a player?**  
A: Yes! The output is a standard H.264 MP4 video. You can play it in VLC, Windows Media Player, etc. (though it will be gibberish black-and-white frames).

**Q: Can I edit the video after encoding?**  
A: No. Any edits will corrupt the embedded data beyond Reed-Solomon's ability to recover.

**Q: What if decoding fails?**  
A: You'll get a clear error message (e.g., "wrong password", "Reed-Solomon recovery failed"). The file is never partially written.

**Q: Can I use this commercially?**  
A: Yes, MIT license allows commercial use. See [LICENSE](./LICENSE).

**Q: How large can files be?**  
A: Theoretically unlimited. Limited only by available RAM and disk space. Tested up to 10 GB.

---

## Support

- 📖 [Full Documentation](https://github.com/bit2vid/bit2vid#readme)
- 🐛 [Issue Tracker](https://github.com/bit2vid/bit2vid/issues)
- 💬 [Discussions](https://github.com/bit2vid/bit2vid/discussions)
- 📧 Email: maintainers@bit2vid.dev

---

**Made with ❤️ for digital archivists and security researchers.**
