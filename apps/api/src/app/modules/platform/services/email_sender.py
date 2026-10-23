"""E-mail channel for notifications (T-616b, R-DEC-20/33) — stdlib `smtplib`, no dependency.

Content = fixed template per `kind` + locale + absolute link. `title` / `body` are **never**
copied into the e-mail (they may carry level 3–4 data), so the message cannot leak PII
(R-DEC-20); `render` also refuses any text matching a `core.pii` pattern as defence in depth.

`dispatch` is idempotent per `notification.id`: a row is claimed with `FOR UPDATE SKIP LOCKED`
and only `PENDING` rows are sent; after success → `SENT`, after 3 failed attempts → `FAILED`.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import make_msgid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ConfigService, get_config
from app.core.pii import detect_content_pii
from app.modules.auth.services.auth_service import AuthService
from app.modules.platform.repositories import NotificationRepository

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS: tuple[int, ...] = (5, 30, 120)  # 05 §2.4: 5 s / 30 s / 120 s

# kind → (subject vi, subject en). Bodies are generic: the user opens the link in Aureon.
SUBJECTS: dict[str, tuple[str, str]] = {
    "alert": ("Cảnh báo chỉ số mới", "New metric alert"),
    "review_assigned": ("Bạn được giao review tài liệu", "A document review is assigned to you"),
    "review_escalated": ("Review tài liệu đã quá hạn", "A document review is overdue"),
    "task_assigned": ("Bạn được giao việc mới", "A new task was assigned to you"),
    "approval_requested": ("Có yêu cầu chờ bạn phê duyệt", "An approval is waiting for you"),
    "approval_decided": ("Yêu cầu phê duyệt đã có kết quả", "An approval request was decided"),
    "report_ready": ("Báo cáo đã sẵn sàng", "Your report is ready"),
    "ai_action": ("AI có đề xuất hành động mới", "AI proposed a new action"),
    "document_ready": ("Tài liệu đã xử lý xong", "Your document has been processed"),
    "reminder": ("Nhắc việc từ Aureon", "Reminder from Aureon"),
    "system": ("Thông báo hệ thống Aureon", "Aureon system notice"),
}  # fmt: skip
BODY = {
    "vi": "{subject}.\n\nMở Aureon để xem chi tiết: {link}\n\n"
    "Bạn có thể tắt email cho loại thông báo này trong phần Cài đặt thông báo.\n",
    "en": "{subject}.\n\nOpen Aureon for details: {link}\n\n"
    "You can turn off e-mails for this kind in Notification settings.\n",
}


class EmailNotConfiguredError(RuntimeError):
    """`SMTP_HOST` missing — the task fails loudly instead of silently dropping mail."""


class UnsafeEmailContentError(ValueError):
    """Rendered text matched a PII pattern — never sent."""


@dataclass(frozen=True)
class Rendered:
    subject: str
    text: str


def safe_link(cfg: ConfigService, link: str | None) -> str:
    base = cfg.web_base_url.rstrip("/")
    if not link or not link.startswith("/") or link.startswith("//"):
        return base + "/"  # only in-app relative paths are linked (no open redirect)
    return base + link


def render(kind: str, locale: str, link: str) -> Rendered:
    vi, en = SUBJECTS.get(kind, SUBJECTS["system"])
    lang = "en" if locale == "en" else "vi"
    subject = en if lang == "en" else vi
    text = BODY[lang].format(subject=subject, link=link)
    if detect_content_pii(subject + "\n" + text):
        raise UnsafeEmailContentError("rendered e-mail matched a PII pattern")
    return Rendered(subject=f"[Aureon] {subject}", text=text)


def send_smtp(cfg: ConfigService, to: str, msg: Rendered, message_key: uuid.UUID) -> None:
    if not cfg.smtp_host:
        raise EmailNotConfiguredError("SMTP_HOST is not configured")
    em = EmailMessage()
    em["From"], em["To"], em["Subject"] = cfg.smtp_from, to, msg.subject
    em["Message-ID"] = make_msgid(idstring=str(message_key), domain="aureon.local")
    em.set_content(msg.text)
    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=cfg.smtp_timeout_seconds) as smtp:
        if cfg.smtp_starttls:
            smtp.starttls(context=ssl.create_default_context())
        if cfg.smtp_username and cfg.smtp_password is not None:
            smtp.login(cfg.smtp_username, cfg.smtp_password.get_secret_value())
        smtp.send_message(em)


@dataclass(frozen=True)
class DispatchResult:
    status: str  # SENT / FAILED / RETRY / SKIPPED
    retry_in: int | None = None


async def dispatch(db: AsyncSession, notification_id: uuid.UUID) -> DispatchResult:
    """Send one notification e-mail (caller commits). Re-runs never send twice."""
    cfg = get_config()
    repo = NotificationRepository(db)
    n = await repo.claim_email(notification_id)
    if n is None or n.email_status != "PENDING":
        return DispatchResult("SKIPPED")  # already SENT/FAILED, or another worker holds it
    contact = await AuthService(db).email_contact(n.recipient_id)
    if contact is None:  # user gone / deactivated → nothing to deliver
        n.email_status = "FAILED"
        return DispatchResult("FAILED")
    to, locale = contact
    n.email_attempts = (n.email_attempts or 0) + 1
    try:
        send_smtp(cfg, to, render(n.kind, locale, safe_link(cfg, n.link)), n.id)
    except UnsafeEmailContentError:
        n.email_status = "FAILED"
        return DispatchResult("FAILED")
    except (OSError, smtplib.SMTPException, EmailNotConfiguredError) as exc:
        # never log the address or credentials — only the notification id and error class
        log.warning("notification e-mail %s failed: %s", n.id, type(exc).__name__)
        if n.email_attempts >= MAX_ATTEMPTS:
            n.email_status = "FAILED"
            return DispatchResult("FAILED")
        return DispatchResult("RETRY", RETRY_BACKOFF_SECONDS[n.email_attempts - 1])
    n.email_status, n.email_sent_at = "SENT", datetime.now(UTC)
    return DispatchResult("SENT")


STALE_RETRY_SECONDS = 600  # a retried row idle this long is swept again (lost countdown)


async def pending_ids(db: AsyncSession) -> list[uuid.UUID]:
    """Beat sweep: PENDING rows of the current tenant (oldest first, bounded batch)."""
    stale = datetime.now(UTC) - timedelta(seconds=STALE_RETRY_SECONDS)
    return await NotificationRepository(db).pending_email(stale, limit=200)
