# Security Policy

## Overview

**Bit2Vid** encrypts and encodes arbitrary binary data into MP4 video frames. This document explains the security considerations and limitations.

## Encryption

### Algorithm
- **Cipher**: AES-256-GCM (Advanced Encryption Standard with 256-bit key)
- **Key Derivation**: PBKDF2 with SHA-256
- **Default Iterations**: 600,000 (OWASP recommended for 2024)
- **Nonce**: 96-bit random value (secure for GCM mode)
- **Authentication Tag**: 16 bytes (128 bits)

### What This Means
- **AES-256-GCM** is a modern authenticated cipher (AEAD), providing both confidentiality and authenticity.
- **PBKDF2** stretches your password into a full 256-bit encryption key, making dictionary attacks expensive.
- **High iteration count** ensures that even if an attacker knows the algorithm, they cannot feasibly brute-force weak passwords.

### What This Does NOT Guarantee
- **Password strength**: Bit2Vid's security depends entirely on your password strength. A weak password (e.g., "123456") can be guessed quickly, regardless of the crypto algorithm.
- **In-memory safety**: The password and decrypted data are held in RAM during processing. On systems with swap enabled, they may be written to disk.
- **Side-channel resistance**: This implementation is not resistant to timing attacks or other side-channel leaks. Do not use for highly sensitive applications requiring extreme hardening.

## Recommendations

### For Users

1. **Use a strong password**: At least 16 random characters or a passphrase of 5+ words.
2. **Keep your password safe**: Treat it like a credit card PIN. Do not share it or store it in plain text.
3. **Check file integrity**: Bit2Vid includes Reed-Solomon error correction, but it cannot detect intentional tampering if the attacker has access to rewrite the entire video.
4. **Test recovery**: Before relying on an encoded video for critical data, test decoding with your password.

### For Administrators

1. **Disable swap** on production systems if processing sensitive data.
2. **Use secure password storage**: If deploying in scripts, use environment variables or secure vaults, not hardcoded strings.
3. **Audit dependencies**: Bit2Vid depends on `pycryptodome` and `reedsolo`. Keep these updated.

## Error Correction

Bit2Vid uses **Reed-Solomon error correction** (64 parity symbols by default) to recover data from corrupted video frames. This helps resilience against:
- Codec compression artifacts
- Transmission errors
- Localized bit flips

However, it **does not provide cryptographic authentication** for the unencrypted transport layer. Always verify the password when decoding.

## Reported Vulnerabilities

If you discover a security vulnerability, please **do not** open a public issue. Instead, email [security contact - to be added] with:
- Description of the issue
- Steps to reproduce
- Potential impact

We take security seriously and will respond promptly.

## Compliance

- **OWASP**: PBKDF2 iteration count follows [OWASP password storage recommendations](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- **NIST**: AES-256 is approved for U.S. government use under FIPS 197
- **No warranty**: Bit2Vid is provided as-is without warranty. Use at your own risk.

## Future Improvements

Planned security enhancements:
- [ ] Argon2 key derivation (more resistant to GPU attacks)
- [ ] XChaCha20-Poly1305 as an alternative cipher
- [ ] Built-in password strength meter
- [ ] Support for hardware security modules (HSM)

## References

- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [NIST SP 800-132: Password-Based Key Derivation](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-132.pdf)
- [GCM Mode (NIST SP 800-38D)](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf)
- [Reed-Solomon Error Correction](https://en.wikipedia.org/wiki/Reed%E2%80%93Solomon_error_correction)
