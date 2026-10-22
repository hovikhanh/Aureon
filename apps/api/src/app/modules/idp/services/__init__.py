"""Public service surface of `idp` (DEC-125). Other modules import only from here."""

from app.modules.idp.services.idp_service import IdpService

__all__ = ["IdpService"]
