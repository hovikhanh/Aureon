"""Module `auth` (schema `auth`). Registers its onboarding `progress` source (EP-ADM-13)."""

from app.core.onboarding import register_progress_source
from app.modules.auth.services.onboarding_progress import auth_progress

register_progress_source("auth", auth_progress)
