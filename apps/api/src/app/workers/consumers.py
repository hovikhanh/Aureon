"""Import every module consumer so `@consumer` registrations exist in worker and beat."""

import importlib

CONSUMER_MODULES = ("app.modules.finance.events.consumers",)


def load_consumers() -> None:
    for name in CONSUMER_MODULES:
        importlib.import_module(name)
