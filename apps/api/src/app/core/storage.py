"""Object storage for IDP source files (04 §3 step 0; 07 §Storage).

The pipeline streams uploaded files to a private object store, keeping only a `storage_key`
on `ENT-SourceDocument`. Demo/dev use a local filesystem store under `IDP_STORAGE_DIR`; prod
swaps in MinIO/S3 behind the same `ObjectStore` interface (CLAUDE.md §5.6 — no new dependency
added for the demo store). INFECTED files are moved to the `quarantine` bucket (DEC-138).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import shutil
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from app.core.config import get_config

DEFAULT_BUCKET = "documents"
QUARANTINE_BUCKET = "quarantine"
_CHUNK = 1024 * 1024  # 1 MB (04 §15.1 — never read the whole file into RAM)


class ObjectStore(Protocol):
    def put_stream(self, chunks: Iterator[bytes], *, bucket: str = DEFAULT_BUCKET) -> str: ...
    def open(self, storage_key: str) -> Path: ...
    def read(self, storage_key: str) -> bytes: ...
    def move(self, storage_key: str, *, to_bucket: str) -> str: ...
    def exists(self, storage_key: str) -> bool: ...


class LocalObjectStore:
    """Filesystem-backed store. `storage_key` = ``<bucket>/<uuid4>`` (opaque, no PII)."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or get_config().idp_storage_dir

    def _path(self, storage_key: str) -> Path:
        # storage_key is app-generated (bucket/uuid); reject traversal defensively.
        parts = storage_key.split("/")
        if len(parts) != 2 or any(p in ("", ".", "..") for p in parts) or "\\" in storage_key:
            raise ValueError(f"invalid storage_key: {storage_key!r}")
        return self.root / parts[0] / parts[1]

    def put_stream(self, chunks: Iterator[bytes], *, bucket: str = DEFAULT_BUCKET) -> str:
        key = f"{bucket}/{uuid.uuid4()}"
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as fh:
            for chunk in chunks:
                fh.write(chunk)
        return key

    def open(self, storage_key: str) -> Path:
        path = self._path(storage_key)
        if not path.is_file():
            raise FileNotFoundError(storage_key)
        return path

    def read(self, storage_key: str) -> bytes:
        return self.open(storage_key).read_bytes()

    def move(self, storage_key: str, *, to_bucket: str) -> str:
        src = self.open(storage_key)
        new_key = f"{to_bucket}/{storage_key.split('/', 1)[1]}"
        dest = self._path(new_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        return new_key

    def exists(self, storage_key: str) -> bool:
        try:
            return self._path(storage_key).is_file()
        except ValueError:
            return False


def iter_file_chunks(path: Path, chunk_size: int = _CHUNK) -> Iterator[bytes]:
    with path.open("rb") as fh:
        while True:
            data = fh.read(chunk_size)
            if not data:
                return
            yield data


_store: ObjectStore | None = None


def get_object_store() -> ObjectStore:
    global _store
    if _store is None:
        _store = LocalObjectStore()
    return _store


# ---- presigned GET (EP-DC-14 "Xem tài liệu gốc", 5 min) ------------------------------------
# The local demo store has no S3 presigner: the URL is HMAC-SHA256 signed over
# (storage_key, expiry) with a key derived from `DB_ENCRYPTION_KEY` (no new dependency). A
# MinIO/S3 store presigns natively behind the same call. Serving route: pending DEC (STATE debt).
PRESIGN_TTL_SECONDS = 300
_PRESIGN_LABEL = b"aureon.idp.presign.v1"
_EPHEMERAL = secrets.token_bytes(32)


def _presign_key() -> bytes:
    key = get_config().db_encryption_key
    base = key.get_secret_value().encode() if key is not None else _EPHEMERAL
    return hmac.new(base, _PRESIGN_LABEL, hashlib.sha256).digest()


def _signature(storage_key: str, expires: int) -> str:
    msg = f"{storage_key}\n{expires}".encode()
    return hmac.new(_presign_key(), msg, hashlib.sha256).hexdigest()


def presign_get(
    storage_key: str, *, ttl: int = PRESIGN_TTL_SECONDS, now: float | None = None
) -> str:
    """Signed, expiring GET URL of a stored object (opaque key, no PII in the URL)."""
    expires = int((now if now is not None else time.time()) + ttl)
    return f"/files/{storage_key}?expires={expires}&signature={_signature(storage_key, expires)}"


def verify_presigned(
    storage_key: str, expires: int, signature: str, *, now: float | None = None
) -> bool:
    if (now if now is not None else time.time()) > expires:
        return False
    return hmac.compare_digest(_signature(storage_key, expires), signature)
