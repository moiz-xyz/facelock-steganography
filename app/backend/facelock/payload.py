"""Serialisation of the secret before encryption.

Layout (all integers big-endian)::

    kind      1 byte   0 = UTF-8 text, 1 = file
    flags     1 byte   bit0 = zlib-compressed
    name_len  2 bytes  | name  (UTF-8 file name, empty for text)
    mime_len  1 byte   | mime  (ASCII MIME type)
    data_len  4 bytes  | data  (possibly compressed)

Compression is applied only when it actually shrinks the data, so already
compressed files (PDF, PNG, ZIP) are stored as-is.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

KIND_TEXT = 0
KIND_FILE = 1
FLAG_ZLIB = 0x01


@dataclass
class SecretPayload:
    kind: int
    data: bytes
    name: str = ""
    mime: str = "text/plain"

    @property
    def is_text(self) -> bool:
        return self.kind == KIND_TEXT

    @classmethod
    def from_text(cls, text: str) -> "SecretPayload":
        return cls(KIND_TEXT, text.encode("utf-8"), "", "text/plain; charset=utf-8")

    @classmethod
    def from_file(cls, name: str, data: bytes, mime: str | None) -> "SecretPayload":
        return cls(KIND_FILE, data, name[:255], (mime or "application/octet-stream")[:100])

    def text(self) -> str:
        return self.data.decode("utf-8", errors="replace")


def pack(p: SecretPayload, compress: bool = True) -> bytes:
    data, flags = p.data, 0
    if compress and data:
        z = zlib.compress(data, level=9)
        if len(z) < len(data):
            data, flags = z, FLAG_ZLIB
    name = p.name.encode("utf-8")[:65535]
    mime = p.mime.encode("ascii", errors="ignore")[:255]
    return (struct.pack(">BBH", p.kind, flags, len(name)) + name +
            struct.pack(">B", len(mime)) + mime + struct.pack(">I", len(data)) + data)


def unpack(blob: bytes) -> SecretPayload:
    try:
        kind, flags, nlen = struct.unpack_from(">BBH", blob, 0)
        off = 4
        name = blob[off:off + nlen].decode("utf-8"); off += nlen
        (mlen,) = struct.unpack_from(">B", blob, off); off += 1
        mime = blob[off:off + mlen].decode("ascii"); off += mlen
        (dlen,) = struct.unpack_from(">I", blob, off); off += 4
        data = blob[off:off + dlen]
        if len(data) != dlen:
            raise ValueError("truncated payload")
        if flags & FLAG_ZLIB:
            data = zlib.decompress(data)
        return SecretPayload(kind, data, name, mime)
    except (struct.error, UnicodeDecodeError, zlib.error) as exc:
        raise ValueError(f"corrupt payload: {exc}") from exc


def overhead(name: str = "", mime: str = "text/plain; charset=utf-8") -> int:
    """Bytes added by :func:`pack` around the raw data (before compression)."""
    return 4 + len(name.encode("utf-8")) + 1 + len(mime.encode("ascii", errors="ignore")) + 4
