"""Contract-step stubs (09 §6.0bis bước C): route + schema exist, behaviour lands in a later task.

No new error code (10 §1.4 is closed): an HTTP `501` goes through the existing
`StarletteHTTPException` handler → `{ error: { code: "INTERNAL_ERROR", message, details } }`.
"""

from typing import NoReturn

from starlette.exceptions import HTTPException

NOT_IMPLEMENTED = 501


def not_implemented(ep: str, task: str) -> NoReturn:
    """`not_implemented("EP-TASK-06", "T-619")` — raised by a stub route body."""
    raise HTTPException(NOT_IMPLEMENTED, detail=f"{ep} not implemented yet ({task})")
