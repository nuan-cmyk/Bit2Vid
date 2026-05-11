"""Application-specific exceptions."""


class Bit2VidError(Exception):
    """Base error for Bit2Vid."""


class FFmpegNotFoundError(Bit2VidError):
    """Raised when FFmpeg is not available."""


class PayloadFormatError(Bit2VidError):
    """Raised when the video payload cannot be parsed."""


class CryptoError(Bit2VidError):
    """Raised when encryption or decryption fails."""
