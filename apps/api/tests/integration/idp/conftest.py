"""Fixtures for IDP integration tests: a temp object store so uploads never touch the repo."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def idp_store(tmp_path: Path) -> Iterator[None]:
    import app.core.storage as storage

    prev = storage._store
    storage._store = storage.LocalObjectStore(root=tmp_path)
    try:
        yield
    finally:
        storage._store = prev
