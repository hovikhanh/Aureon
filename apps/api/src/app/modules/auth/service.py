"""EP-02 login service: authenticate, mint JWT, audit `auth.login` (10 EP-02, §1.7). T-103.

``login`` is the one place that turns a (email, password) pair into either a :class:`LoginData`
payload or an ``INVALID_CREDENTIALS`` error, and it audits **both** outcomes:

- success → ``auth.login`` with the authenticated user as actor, ``metadata.result="success"``;
- failure → ``auth.login`` with ``actor_type=SYSTEM`` (the identity is not trusted) and the
  attempted email only in ``metadata`` (10 §1.7, ActorType rules in audit.service).

The plaintext password is never stored, logged or placed in any audit field. Wrong email and
wrong password raise the SAME :class:`ApiError` so the response cannot be used to enumerate users
(10 EP-02 protection 3). The audit row is added to the caller's session; the router owns the
commit so audit and ``last_login_at`` share one transaction (05 §4.12, §1.7).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import ConfigService
from app.core.errors import ApiError, ErrorCode
from app.core.security import verify_password
from app.db.enums import ActorType
from app.modules.audit.service import record_audit
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginData, UserOut
from app.modules.auth.token import create_access_token

_AUTH_LOGIN_ACTION = "auth.login"
_AUTH_TARGET_TYPE = "auth_session"


def _get_user_by_email(db: Session, email: str) -> User | None:
    # `email` is already normalised lowercase by LoginRequest; the partial unique index guarantees
    # at most one live row (05 §4.1). Soft-deleted users must not be able to log in.
    stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
    return db.scalars(stmt).first()


def login(
    db: Session,
    *,
    email: str,
    password: str,
    config: ConfigService,
    ip_address: str | None = None,
) -> LoginData:
    """Authenticate and return a :class:`LoginData`, or raise ``INVALID_CREDENTIALS``.

    Audits ``auth.login`` on both success and failure. Does NOT commit — the caller does.
    """
    user = _get_user_by_email(db, email)
    # Always run verify_password to keep timing similar whether or not the email exists; when the
    # user is missing we still compare against a throwaway to avoid a short-circuit timing oracle.
    candidate_hash = user.password_hash if user is not None else None
    password_ok = verify_password(password, candidate_hash) if candidate_hash is not None else False

    if user is None or not password_ok:
        # Failure branch: no trusted user identity → SYSTEM actor; attempted email in metadata
        # only (never the password). 10 §1.7 allows auth.login beyond mutations.
        record_audit(
            db,
            action=_AUTH_LOGIN_ACTION,
            target_type=_AUTH_TARGET_TYPE,
            actor_type=ActorType.SYSTEM,
            metadata={"result": "failure", "email": email},
            ip_address=ip_address,
        )
        # Identical error for unknown email and wrong password (no enumeration, 10 EP-02).
        raise ApiError(ErrorCode.INVALID_CREDENTIALS)

    token, expires_at = create_access_token(user, config)
    user.last_login_at = datetime.now(UTC)
    record_audit(
        db,
        action=_AUTH_LOGIN_ACTION,
        target_type=_AUTH_TARGET_TYPE,
        actor_type=ActorType.USER,
        actor_user_id=user.id,
        actor_role_id=user.role_id,
        target_id=user.id,
        metadata={"result": "success", "email": user.email},
        ip_address=ip_address,
    )
    return LoginData(access_token=token, expires_at=expires_at, user=UserOut.model_validate(user))
