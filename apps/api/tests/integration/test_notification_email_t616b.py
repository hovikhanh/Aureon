"""T-616b — notification e-mail via smtplib (TC-M12-15, TC-M12-14 e-mail part; R-DEC-20/33)."""

import smtplib
import uuid
from email.message import EmailMessage
from typing import Any, ClassVar

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.core.pii import detect_content_pii
from app.modules.auth.models import Role, User
from app.modules.platform.models import Notification
from app.modules.platform.services import email_sender
from app.modules.platform.services.email_sender import SUBJECTS, dispatch, pending_ids, render
from app.modules.platform.services.notification_service import NotificationService

pytestmark = pytest.mark.integration
SECRET_TITLE = "Lương tháng 10 của Nguyễn Văn An: 45.000.000 đ, CCCD 079090001234"


class FakeSMTP:
    sent: ClassVar[list[EmailMessage]] = []
    fail: ClassVar[int] = 0
    logins: ClassVar[list[tuple[str, str]]] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host = host

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def starttls(self, **_: Any) -> None:
        return None

    def login(self, user: str, password: str) -> None:
        FakeSMTP.logins.append((user, password))

    def send_message(self, msg: EmailMessage) -> None:
        if FakeSMTP.fail > 0:
            FakeSMTP.fail -= 1
            raise smtplib.SMTPServerDisconnected("down")
        FakeSMTP.sent.append(msg)


@pytest.fixture(autouse=True)
def smtp(monkeypatch: pytest.MonkeyPatch) -> type[FakeSMTP]:
    FakeSMTP.sent, FakeSMTP.fail, FakeSMTP.logins = [], 0, []
    monkeypatch.setattr(email_sender.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(get_config(), "smtp_host", "smtp.test")
    return FakeSMTP


async def make_user(db: AsyncSession, *, locale: str = "vi", active: bool = True) -> User:
    role = (await db.execute(select(Role).where(Role.code == "EMP"))).scalar_one()
    u = User(email=f"n{uuid.uuid4().hex[:8]}@abc.test", password_hash="x", full_name="Người nhận",
             role_id=role.id, locale=locale, is_active=active)  # fmt: skip
    db.add(u)
    await db.flush()
    return u


async def pending(db: AsyncSession, user: User, kind: str = "task_assigned", **kw: Any) -> Any:
    svc = NotificationService(db)
    nid = await svc.create(recipient_id=user.id, kind=kind, title=SECRET_TITLE, body=SECRET_TITLE,
                           **kw)  # fmt: skip
    await db.commit()
    return nid


async def row(db: AsyncSession, nid: uuid.UUID) -> Notification:
    n = (await db.execute(select(Notification).where(Notification.id == nid))).scalar_one()
    await db.refresh(n)
    return n


async def test_send_once_and_idempotent(db_session: AsyncSession) -> None:
    u = await make_user(db_session)
    nid = await pending(db_session, u, link="/vi/tasks/123")
    assert nid in await pending_ids(db_session)
    assert (await dispatch(db_session, nid)).status == "SENT"
    await db_session.commit()
    again = await dispatch(db_session, nid)  # re-run / duplicate task
    assert again.status == "SKIPPED" and len(FakeSMTP.sent) == 1
    n = await row(db_session, nid)
    assert n.email_status == "SENT" and n.email_sent_at and n.email_attempts == 1
    assert nid not in await pending_ids(db_session)
    msg = FakeSMTP.sent[0]
    assert msg["To"] == u.email and msg["Subject"] == "[Aureon] Bạn được giao việc mới"
    text = msg.get_content()
    assert "http://localhost:3000/vi/tasks/123" in text
    assert "Lương" not in text and "079090001234" not in text and SECRET_TITLE not in text
    assert not detect_content_pii(text)


async def test_retry_then_failed(db_session: AsyncSession) -> None:
    u = await make_user(db_session)
    nid = await pending(db_session, u)
    FakeSMTP.fail = 5
    first = await dispatch(db_session, nid)
    assert (first.status, first.retry_in) == ("RETRY", 5)
    await db_session.commit()
    assert (await dispatch(db_session, nid)).retry_in == 30
    await db_session.commit()
    assert (await dispatch(db_session, nid)).status == "FAILED"
    await db_session.commit()
    n = await row(db_session, nid)
    assert n.email_status == "FAILED" and n.email_attempts == 3 and FakeSMTP.sent == []


async def test_retry_recovers(db_session: AsyncSession) -> None:
    u = await make_user(db_session, locale="en")
    nid = await pending(db_session, u, kind="approval_requested", link="https://evil.example/x")
    FakeSMTP.fail = 1
    assert (await dispatch(db_session, nid)).status == "RETRY"
    assert (await dispatch(db_session, nid)).status == "SENT"
    msg = FakeSMTP.sent[0]
    assert msg["Subject"] == "[Aureon] An approval is waiting for you"
    assert "evil.example" not in msg.get_content()  # only in-app relative links


async def test_not_required_and_inactive(db_session: AsyncSession) -> None:
    u = await make_user(db_session)
    off = await pending(db_session, u, kind="alert")  # e-mail off by default for alerts
    assert (await row(db_session, off)).email_status == "NOT_REQUIRED"
    assert (await dispatch(db_session, off)).status == "SKIPPED"
    gone = await make_user(db_session, active=False)
    nid = await pending(db_session, gone)
    assert (await dispatch(db_session, nid)).status == "FAILED" and FakeSMTP.sent == []


async def test_smtp_not_configured(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch,
                                   caplog: pytest.LogCaptureFixture) -> None:  # fmt: skip
    monkeypatch.setattr(get_config(), "smtp_host", "")
    u = await make_user(db_session)
    nid = await pending(db_session, u)
    assert (await dispatch(db_session, nid)).status == "RETRY"
    assert "EmailNotConfiguredError" in caplog.text and u.email not in caplog.text


def test_templates_have_no_pii() -> None:
    for kind in SUBJECTS:
        for locale in ("vi", "en"):
            r = render(kind, locale, "http://localhost:3000/")
            assert not detect_content_pii(r.subject + r.text), (kind, locale)
