"""Consumer registry + broker transport.

Routing (07 §5.4): modules declare `event_type → [consumer]` in `modules/<m>/events.py` via
`@consumer(...)`; the relay fans out one message per consumer so each dedupes independently.
Transport is Celery on the Redis broker (queue `events`, DEC-002/126). The `Transport` protocol
lets tests swap in an in-memory bus.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.envelope import EventEnvelope
from app.core.events.registry import is_registered

Handler = Callable[[AsyncSession, EventEnvelope], Awaitable[None]]
EVENTS_QUEUE = "events"
CONSUME_TASK = "app.events.consume"


@dataclass
class ConsumerRegistry:
    handlers: dict[str, Handler] = field(default_factory=dict)
    routes: dict[str, list[str]] = field(default_factory=dict)

    def register(self, name: str, event_types: tuple[str, ...], handler: Handler) -> None:
        if name in self.handlers:
            raise ValueError(f"consumer {name!r} registered twice")
        module, _, fn = name.partition(".")
        if not module or not fn.startswith("on_"):
            raise ValueError(f"consumer name {name!r} must be <module>.on_<event> (E7)")
        for et in event_types:
            if not is_registered(et):
                raise ValueError(f"{name}: event type {et!r} not in registry")
        self.handlers[name] = handler
        for et in event_types:
            self.routes.setdefault(et, []).append(name)

    def consumers_for(self, event_type: str) -> list[str]:
        return list(self.routes.get(event_type, ()))

    def get(self, name: str) -> Handler:
        try:
            return self.handlers[name]
        except KeyError:
            raise LookupError(f"unknown consumer {name!r}") from None


REGISTRY = ConsumerRegistry()


def consumer(name: str, *event_types: str) -> Callable[[Handler], Handler]:
    """`@consumer("risk.on_hiring_plan_delayed", "hr.hiring_plan_delayed")`."""

    def deco(fn: Handler) -> Handler:
        REGISTRY.register(name, event_types, fn)
        return fn

    return deco


class Transport(Protocol):
    def send(self, consumer_name: str, message: dict[str, Any], countdown: int = 0) -> None: ...


class CeleryTransport:
    """Sends `app.events.consume(consumer, message)` to the `events` queue."""

    def send(self, consumer_name: str, message: dict[str, Any], countdown: int = 0) -> None:
        from app.worker import celery_app  # lazy: importing core must not build Celery

        celery_app.send_task(
            CONSUME_TASK,
            args=[consumer_name, message],
            queue=EVENTS_QUEUE,
            countdown=countdown,
        )
