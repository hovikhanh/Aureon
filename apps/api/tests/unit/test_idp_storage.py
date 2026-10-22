"""Unit tests for the IDP object store (core/storage.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.storage import (
    LocalObjectStore,
    get_object_store,
    iter_file_chunks,
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
