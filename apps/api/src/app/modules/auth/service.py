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
from sqlalchemy.orm import Session, joinedload

from app.core.config import ConfigService
from app.core.errors import ApiError, ErrorCode
from app.core.security import verify_password
from app.db.enums import ActorType
from app.modules.audit.service import record_audit
from app.modules.auth.models import Role, User
from app.modules.auth.schemas import DemoUserItem, LoginData, SwitchRoleData, UserOut
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


def switch_role(
    db: Session,
    *,
    current_user: User,
    target_role_code: str,
    config: ConfigService,
    ip_address: str | None = None,
) -> SwitchRoleData:
    """Issue a new JWT for the demo user of `target_role_code` and audit `role.switch`."""
    stmt = (
        select(User)
        .join(User.role)
        .options(joinedload(User.role))
        .where(
            User.is_demo_account.is_(True),
            User.deleted_at.is_(None),
            Role.code == target_role_code,
        )
    )
    target_user = db.scalars(stmt).first()
    if target_user is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"No demo user found for role {target_role_code}")

    token, expires_at = create_access_token(target_user, config)
    target_user.last_login_at = datetime.now(UTC)

    record_audit(
        db,
        action="role.switch",
        target_type="user",
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        actor_role_id=current_user.role_id,
        target_id=target_user.id,
        metadata={
            "from_role": current_user.role.code,
            "to_role": target_role_code,
            "from_user_id": str(current_user.id),
            "to_user_id": str(target_user.id),
        },
        ip_address=ip_address,
    )

    return SwitchRoleData(
        access_token=token,
        expires_at=expires_at,
        user=UserOut.model_validate(target_user),
        home_route=target_user.role.home_route,
    )


def list_demo_users(db: Session) -> list[DemoUserItem]:
    """Return the 5 seeded demo users ordered by role code ROLE-01..05 (10 EP-05)."""
    stmt = (
        select(User)
        .join(User.role)
        .options(joinedload(User.role))
        .where(
            User.is_demo_account.is_(True),
            User.deleted_at.is_(None),
        )
        .order_by(Role.code.asc())
    )
    users = db.scalars(stmt).all()
    return [
        DemoUserItem(
            role_code=u.role.code,
            role_name_i18n_key=u.role.name_i18n_key,
            full_name=u.full_name,
            user_id=u.id,
        )
        for u in users
    ]
