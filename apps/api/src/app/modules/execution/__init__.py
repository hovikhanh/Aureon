"""Module `execution` (schema `execution`). Registers its onboarding `progress` source."""

from app.core.onboarding import register_progress_source
from app.modules.execution.services.onboarding_progress import execution_progress

register_progress_source("execution", execution_progress)
