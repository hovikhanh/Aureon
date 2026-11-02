"""Bootstrap một tài khoản ROLE-ADM thật cho triển khai live (sau khi xóa data demo).

KHÔNG phải seed demo: chỉ (1) seed bảng `auth.roles` chuẩn (cần cho FK `role_id`) và
(2) tạo đúng một user ADMIN từ biến môi trường `ADMIN_BOOTSTRAP_EMAIL` / `ADMIN_BOOTSTRAP_PASSWORD`.
Idempotent: chạy lại chỉ đồng bộ mật khẩu/role, không tạo trùng. Mật khẩu KHÔNG hard-code,
đọc qua os.environ (secret, không ghi log).

Dùng: nạp .env rồi `python -m app.scripts.bootstrap_admin`.
"""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import dotenv_values
from sqlalchemy import select

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.config import REPO_ROOT
from app.core.db import get_sessionmaker
from app.core.security import hash_password, verify_password
from app.core.tenant import tenant_scope
from app.modules.auth.models import Role, User
from app.seed.auth_seed import SeedReport, seed_roles

MIN_PASSWORD_LEN = 12
ADMIN_ROLE_CODE = "ADM"


def _env(name: str) -> str:
    """Process env wins; else parse .env with the same quote-safe parser pydantic-settings uses.

    An unquoted secret containing a quote/space/metacharacter parses differently in bash than in
    dotenv (and breaks `source .env` outright) — `scripts/check_env.sh` now fails on that, so the
    two readers agree; this helper still uses the dotenv parser as the single source."""
    if name in os.environ:
        return os.environ[name] or ""
    return dotenv_values(REPO_ROOT / ".env").get(name) or ""


async def _run() -> int:
    email = _env("ADMIN_BOOTSTRAP_EMAIL").strip()
    password = _env("ADMIN_BOOTSTRAP_PASSWORD")
    if not email or not password:
        print("✗ Thiếu ADMIN_BOOTSTRAP_EMAIL / ADMIN_BOOTSTRAP_PASSWORD trong môi trường.")
        return 2
    if len(password) < MIN_PASSWORD_LEN:
        print(f"✗ Mật khẩu admin phải ≥ {MIN_PASSWORD_LEN} ký tự.")
        return 2

    async with get_sessionmaker()() as session:
        with tenant_scope(DEFAULT_TENANT_ID):  # R-DEC-21: ghi như system tenant
            report = SeedReport()
            roles = await seed_roles(session, report)
            admin_role = (
                roles.get(ADMIN_ROLE_CODE)
                or (
                    await session.execute(select(Role).where(Role.code == ADMIN_ROLE_CODE))
                ).scalar_one()
            )
            await session.flush()

            user = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if user is None:
                session.add(
                    User(
                        email=email,
                        password_hash=hash_password(password),
                        full_name="System Administrator",
                        role_id=admin_role.id,
                        is_active=True,
                        is_service_account=False,
                    )
                )
                action = "created"
            else:
                user.role_id = admin_role.id
                user.is_active = True
                user.deleted_at = None
                if not verify_password(user.password_hash, password):
                    user.password_hash = hash_password(password)
                action = "updated"
            await session.commit()

    print(f"✅ admin bootstrap {action}: {email} (role=ROLE-ADM).")
    print("   Đổi mật khẩu ngay sau lần đăng nhập đầu tiên.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
