"""HTTP routes for `hr` — endpoints added by their T-xxx tasks (10-API-SPECIFICATION)."""

from app.core.routing import EnvelopeRouter

router = EnvelopeRouter(tags=["hr"])
