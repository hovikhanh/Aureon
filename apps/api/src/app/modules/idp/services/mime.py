"""MIME whitelist + magic-byte sniffing for IDP uploads (04 §2.3, FR-DC-07).

v2.0 accepts PDF, DOC/DOCX, images (JPG/PNG/HEIC/WEBP) and spreadsheets (XLS/XLSX/CSV).
We check both the declared content-type and the leading bytes so a mislabelled file is
rejected with `415 UNSUPPORTED_MEDIA_TYPE`. ZIP containers are not accepted (DEC-051), but
DOCX/XLSX are themselves zip-based — so detection prefers the declared type for OOXML and
falls back to magic bytes for the binary formats.
"""

from __future__ import annotations

# extension → canonical mime (declared type is validated against this set)
EXT_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".heic": "image/heic",
}

ALLOWED_MIME: frozenset[str] = frozenset(EXT_MIME.values())

# magic-byte prefixes for the non-OOXML formats (OOXML + csv are validated by ext/declared type)
_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"RIFF", "image/webp"),  # RIFF....WEBP
    (b"PK\x03\x04", "application/zip"),  # OOXML (docx/xlsx) + legacy zip
    (b"\xd0\xcf\x11\xe0", "application/x-ole"),  # legacy doc/xls (OLE2)
)

_OOXML = {EXT_MIME[".docx"], EXT_MIME[".xlsx"]}
_OLE = {EXT_MIME[".doc"], EXT_MIME[".xls"]}


def ext_of(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[1].lower()


def sniff(prefix: bytes) -> str | None:
    for magic, mime in _MAGIC:
        if magic == b"RIFF":
            if prefix[:4] == b"RIFF" and prefix[8:12] == b"WEBP":
                return "image/webp"
        elif prefix.startswith(magic):
            return mime
    return None


def resolve_mime(filename: str | None, declared: str | None, prefix: bytes) -> str | None:
    """Return the accepted canonical mime, or None if the file is not allowed.

    The extension picks the canonical type; magic bytes must be consistent with it (so a
    `.pdf` carrying a PNG header, or an executable renamed to `.pdf`, is rejected).
    """
    ext = ext_of(filename)
    canonical = EXT_MIME.get(ext)
    if canonical is None:
        # fall back to the declared content-type if it is in the whitelist
        canonical = declared if declared in ALLOWED_MIME else None
    if canonical is None:
        return None

    sniffed = sniff(prefix)
    if canonical in _OOXML:
        return canonical if sniffed in ("application/zip", None) else None
    if canonical in _OLE:
        return canonical if sniffed in ("application/x-ole", None) else None
    if canonical == "text/csv":
        return canonical if sniffed is None else None  # plain text has no magic
    # pdf / images: the sniffed type must match the canonical type
    return canonical if sniffed == canonical else None
