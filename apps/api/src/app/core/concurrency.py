"""Optimistic locking for `PATCH` (C19 `version`, 10 §1.1, T-018).

Client sends the version it read, either as `If-Match: <version>` (also `"3"` / `W/"3"`)
or as body field `version` (10 §1.1). Both present and different → 422; neither → 422
(`version` is required on PATCH — otherwise a lost update is silent). The route passes the
result to `BaseRepository.update(obj, expected_version=…)`, which raises `409 CONFLICT_STATE`.
"""

import re
from typing import Annotated

from fastapi import Header

from app.core.errors import ValidationError

_ETAG = re.compile(r'^\s*(?:W/)?"?(\d{1,18})"?\s*$')


def parse_if_match(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    m = _ETAG.match(value)
    if m is None:
        raise ValidationError(
            "If-Match must be the integer version", details={"fields": [{"field": "If-Match"}]}
        )
    return int(m.group(1))


def expected_version(if_match: str | None, body_version: int | None) -> int:
    header = parse_if_match(if_match)
    if header is not None and body_version is not None and header != body_version:
        raise ValidationError(
            "If-Match and body version disagree",
            details={"fields": [{"field": "version"}, {"field": "If-Match"}]},
        )
    version = header if header is not None else body_version
    if version is None:
        raise ValidationError(
            "PATCH requires the current version (If-Match header or body `version`)",
            details={"fields": [{"field": "version", "reason": "required"}]},
        )
    return version


IfMatch = Annotated[str | None, Header(alias="If-Match")]
