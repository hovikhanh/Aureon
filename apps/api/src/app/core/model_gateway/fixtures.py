"""Fixture/replay store for `MODEL_GATEWAY_MODE=fixture` (07 §5.2, §9; TC-IDP-036).

Format — one JSON file per recorded completion::

    <fixture_dir>/<task_type>/<key>.json
    {
      "task_type": "classify",
      "key": "<key>",
      "content": "<raw model text>"      # either "content" (string) ...
      "data": {...},                     # ... or "data" (any JSON; serialised as content)
      "model": "recorded-model-name",    # optional, informational
      "note": "DOC-01 invoice"           # optional, informational
    }

`key` is the caller's `fixture_key` when given (07 §9: SHA-256 of the source file, optionally
suffixed by step/chunk, e.g. `"<sha256>.p1"`), otherwise `fixture_hash(...)` — SHA-256 over
the canonical JSON of task_type + messages + json_mode, so replays are deterministic.
"""

import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from app.core.model_gateway.errors import FixtureNotFoundError, ModelGatewayError
from app.core.model_gateway.types import ChatMessage, TaskType

_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")


class FixtureRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: TaskType
    key: str
    content: str | None = None
    data: Any = None
    model: str = "fixture"
    note: str | None = None

    @model_validator(mode="after")
    def _one_payload(self) -> "FixtureRecord":
        # `data` may legitimately be JSON null, so check presence, not value.
        if (self.content is None) == ("data" not in self.model_fields_set):
            raise ValueError("fixture must define exactly one of 'content' or 'data'")
        return self

    def text(self) -> str:
        if self.content is not None:
            return self.content
        return json.dumps(self.data, ensure_ascii=False, sort_keys=True)


def fixture_hash(task_type: str, messages: Sequence[ChatMessage], json_mode: bool) -> str:
    canonical = json.dumps(
        {
            "task_type": task_type,
            "json_mode": json_mode,
            "messages": [m.model_dump() for m in messages],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class FixtureStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def __repr__(self) -> str:
        return f"FixtureStore(root={str(self.root)!r})"

    def path_for(self, task_type: str, key: str) -> Path:
        if not _KEY_PATTERN.match(key):
            raise ModelGatewayError(
                f"invalid fixture key {key!r} (allowed: [A-Za-z0-9._-], max 200 chars)",
                task_type=task_type,
                retryable=False,
            )
        return self.root / task_type / f"{key}.json"

    def load(self, task_type: TaskType, key: str) -> FixtureRecord:
        path = self.path_for(task_type, key)
        if not path.is_file():
            raise FixtureNotFoundError(
                f"no model fixture for task_type={task_type} key={key} (expected file {path}); "
                "MODEL_GATEWAY_MODE=fixture only replays recorded documents (07 §9) — "
                "record it or switch to live mode",
                task_type=task_type,
                key=key,
                path=str(path),
            )
        try:
            record = FixtureRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError as exc:
            raise ModelGatewayError(
                f"malformed model fixture {path}: {exc.error_count()} validation error(s)",
                task_type=task_type,
                retryable=False,
            ) from exc
        if record.task_type != task_type or record.key != key:
            raise ModelGatewayError(
                f"fixture {path} declares task_type={record.task_type} key={record.key}, "
                f"expected task_type={task_type} key={key}",
                task_type=task_type,
                retryable=False,
            )
        return record

    def save(
        self,
        task_type: TaskType,
        key: str,
        *,
        content: str | None = None,
        data: Any = None,
        model: str = "fixture",
        note: str | None = None,
    ) -> Path:
        """Write a fixture (used to record live outputs for the offline demo, T-407)."""
        payload: dict[str, Any] = {"task_type": task_type, "key": key, "model": model}
        if content is not None:
            payload["content"] = content
        else:
            payload["data"] = data
        if note is not None:
            payload["note"] = note
        FixtureRecord.model_validate(payload)
        path = self.path_for(task_type, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path
