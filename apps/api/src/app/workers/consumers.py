"""Import every module consumer / metric provider so registrations exist in worker and beat.

Module lists are app-level wiring (core must not import modules — TC-ARCH-001).
"""

import importlib
import importlib.util
import pkgutil

CONSUMER_MODULES = (
    "app.modules.finance.events.consumers",
    "app.modules.platform.events.consumers",
)
# `modules/<m>/services/{metrics,metric_provider}.py` hold `@metric_provider`s (DEC-205).
_MODULES_PKG = "app.modules"
PROVIDER_LEAVES = ("metrics", "metric_provider")


def load_consumers() -> None:
    for name in CONSUMER_MODULES:
        importlib.import_module(name)
    load_metric_providers()  # platform consumers recompute metrics


def load_metric_providers() -> None:
    pkg = importlib.import_module(_MODULES_PKG)
    for info in pkgutil.iter_modules(pkg.__path__):
        services = f"{_MODULES_PKG}.{info.name}.services"
        if importlib.util.find_spec(services) is None:
            continue
        for leaf in PROVIDER_LEAVES:
            if importlib.util.find_spec(f"{services}.{leaf}") is not None:
                importlib.import_module(f"{services}.{leaf}")
