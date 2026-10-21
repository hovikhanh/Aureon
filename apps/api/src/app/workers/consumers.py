"""Import every module consumer / metric provider so registrations exist in worker and beat.

Module lists are app-level wiring (core must not import modules — TC-ARCH-001).
"""

import importlib
import importlib.util
import pkgutil

CONSUMER_MODULES = ("app.modules.finance.events.consumers",)
# Every `modules/<m>/services/metrics.py` that exists is a metric provider (DEC-205).
_MODULES_PKG = "app.modules"


def load_consumers() -> None:
    for name in CONSUMER_MODULES:
        importlib.import_module(name)


def load_metric_providers() -> None:
    pkg = importlib.import_module(_MODULES_PKG)
    for info in pkgutil.iter_modules(pkg.__path__):
        name = f"{_MODULES_PKG}.{info.name}.services.metrics"
        if importlib.util.find_spec(f"{_MODULES_PKG}.{info.name}.services") is None:
            continue
        if importlib.util.find_spec(name) is not None:
            importlib.import_module(name)
