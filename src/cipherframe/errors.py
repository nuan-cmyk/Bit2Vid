"""Application-specific exceptions."""


class CipherFrameError(Exception):
    """Base error for CipherFrame Vault."""


class FFmpegNotFoundError(CipherFrameError):
    """Raised when FFmpeg is not available."""


class PayloadFormatError(CipherFrameError):
    """Raised when the video payload cannot be parsed."""


class CryptoError(CipherFrameError):
    """Raised when encryption or decryption fails."""

