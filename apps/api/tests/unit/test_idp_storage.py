"""Unit tests for the IDP object store (core/storage.py)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.core.storage import (
    PRESIGN_TTL_SECONDS,
    PRESIGN_URL_PREFIX,
    LocalObjectStore,
    get_object_store,
    iter_file_chunks,
    presign_get,
    valid_storage_key,
    verify_presigned,
)


def test_put_read_and_chunks(tmp_path: Path) -> None:
    store = LocalObjectStore(root=tmp_path)
    key = store.put_stream(iter([b"hello ", b"world"]))
    assert store.read(key) == b"hello world"
    assert store.exists(key)
    path = store.open(key)
    assert b"".join(iter_file_chunks(path, chunk_size=4)) == b"hello world"


def test_invalid_key_rejected(tmp_path: Path) -> None:
    store = LocalObjectStore(root=tmp_path)
    with pytest.raises(ValueError):
        store.open("../etc/passwd")
    assert store.exists("../../x") is False
    with pytest.raises(FileNotFoundError):
        store.read("documents/does-not-exist")


def test_get_object_store_singleton() -> None:
    assert get_object_store() is get_object_store()


# ---- EP-DC-14b presign / verify (R-DEC-80) ------------------------------------------------
def test_valid_storage_key() -> None:
    good = f"documents/{uuid.uuid4()}"
    assert valid_storage_key(good)
    assert valid_storage_key(f"quarantine/{uuid.uuid4()}")
    # traversal / extra segments / non-uuid / backslash all rejected
    assert not valid_storage_key("../etc/passwd")
    assert not valid_storage_key("documents/../secret")
    assert not valid_storage_key("a/b/c")
    assert not valid_storage_key("documents/not-a-uuid")
    assert not valid_storage_key("documents")
    assert not valid_storage_key(f"documents\\{uuid.uuid4()}")
    assert not valid_storage_key(f"/documents/{uuid.uuid4()}")


def test_presign_get_prefix_and_roundtrip() -> None:
    key = f"documents/{uuid.uuid4()}"
    url = presign_get(key, now=1000.0)
    assert url.startswith(f"{PRESIGN_URL_PREFIX}/{key}?expires=")
    # the browser-reachable prefix routes through the BFF → FastAPI /api/v1/files/...
    assert url.startswith("/api/backend/files/")
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(url).query)
    expires = int(qs["expires"][0])
    assert expires == int(1000.0 + PRESIGN_TTL_SECONDS)
    assert verify_presigned(key, expires, qs["signature"][0], now=1000.0)


def test_verify_presigned_expiry_and_tamper() -> None:
    key = f"documents/{uuid.uuid4()}"
    expires = 2000
    from app.core.storage import _signature

    good = _signature(key, expires)
    assert verify_presigned(key, expires, good, now=1999)
    # one second past expiry → rejected regardless of a valid signature
    assert not verify_presigned(key, expires, good, now=expires + 1)
    # tampered signature → rejected
    assert not verify_presigned(key, expires, "deadbeef", now=1999)
    # tampered key (different document) → signature no longer matches
    other = f"documents/{uuid.uuid4()}"
    assert not verify_presigned(other, expires, good, now=1999)
    # tampered expiry (extend the window) → signature no longer matches
    assert not verify_presigned(key, expires + 600, good, now=1999)
