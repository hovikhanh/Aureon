"""`EnvelopeRouter` — wraps every route in the 10 §1.3 success envelope automatically.

Routes declare their *payload* model (`response_model=UserOut`, or `list[X]` for lists) and
return the payload (or a `Page`). The router rewrites the OpenAPI/validation model to
`Envelope[payload]` and wraps the return value, so no route builds `{data, meta}` by hand.
Routes returning a `Response` (e.g. `204`) or declaring no model are left untouched.
"""

import functools
import inspect
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Response
from fastapi.datastructures import DefaultPlaceholder

from app.core.envelope import Envelope, to_envelope


def _wrap_endpoint(endpoint: Callable[..., Any]) -> Callable[..., Any]:
    if not inspect.iscoroutinefunction(endpoint):
        raise TypeError(f"{endpoint.__qualname__}: endpoints must be async (CLAUDE.md §2.2)")

    @functools.wraps(endpoint)  # keeps __wrapped__ → FastAPI reads the original signature
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = await endpoint(*args, **kwargs)
        if isinstance(result, Response):
            return result
        return to_envelope(result)

    return wrapper


class EnvelopeRouter(APIRouter):
    def add_api_route(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        model = kwargs.get("response_model")
        response_class = kwargs.get("response_class")
        raw_response = (
            response_class is not None
            and not isinstance(response_class, DefaultPlaceholder)
            and response_class is Response
        )
        if model is not None and not isinstance(model, DefaultPlaceholder) and not raw_response:
            # Runtime parametrisation (model is a value, not a static type).
            kwargs["response_model"] = Envelope.__class_getitem__(model)
            endpoint = _wrap_endpoint(endpoint)
        super().add_api_route(path, endpoint, **kwargs)
