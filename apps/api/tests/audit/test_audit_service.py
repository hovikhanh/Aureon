"""Unit coverage of record_audit validation + metadata handling (10 §1.7; T-102).

These don't touch Postgres (no flush): ``record_audit`` only builds and adds the ORM object.
"""

from __future__ import annotations

import ipaddress
import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.request_id import request_id_var
from app.db.enums import ActorType
from app.db.session import SessionLocal
from app.modules.audit.service import record_audit


def _session() -> Session:
    # A real (unflushed) session so db.add works; nothing is committed.
    return SessionLocal()


def test_requires_action_and_target_type() -> None:
    with _session() as db, pytest.raises(ValueError, match="action and target_type"):
        record_audit(db, action="", target_type="x", actor_type=ActorType.SYSTEM)


def test_user_actor_requires_actor_user_id() -> None:
    with _session() as db, pytest.raises(ValueError, match="actor_user_id is required"):
        record_audit(db, action="a", target_type="x", actor_type=ActorType.USER)


def test_non_user_actor_rejects_actor_user_id() -> None:
    with _session() as db, pytest.raises(ValueError, match="must be None"):
        record_audit(
            db,
            action="a",
            target_type="x",
            actor_type=ActorType.AI,
            actor_user_id=uuid.uuid4(),
        )


def test_metadata_request_id_and_idempotency_key_filled() -> None:
    token = request_id_var.set("req-abc")
    try:
        with _session() as db:
            entry = record_audit(
                db,
                action="a",
                target_type="x",
                actor_type=ActorType.SYSTEM,
                idempotency_key="idem-1",
            )
            assert entry.metadata_ is not None
            assert entry.metadata_["request_id"] == "req-abc"
            assert entry.metadata_["idempotency_key"] == "idem-1"
    finally:
        request_id_var.reset(token)


def test_ip_address_string_is_parsed() -> None:
    with _session() as db:
        entry = record_audit(
            db,
            action="a",
            target_type="x",
            actor_type=ActorType.SYSTEM,
            ip_address="10.0.0.5",
        )
        assert entry.ip_address == ipaddress.ip_address("10.0.0.5")


def test_no_metadata_when_empty() -> None:
    # Outside a request and with no idempotency key, metadata stays None.
    with _session() as db:
        entry = record_audit(db, action="a", target_type="x", actor_type=ActorType.SYSTEM)
        assert entry.metadata_ is None
