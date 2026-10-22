"""T-309 — AI PII filter + classification routing (prompt_guard, 5.5, FR-AI-10, 07 §6.5).

TC-AI-017. Level-4 PII never reaches any LLM; level-3 contacts become stable EMP-/CLI- codes;
a salary term forces SECRET (no LLM); other PII forces CONFIDENTIAL (local model only).
"""

import pytest

from app.modules.ai.services.prompt_guard import (
    classify_prompt,
    redact_for_log,
    scrub_for_model,
)

pytestmark = pytest.mark.integration


# ---------- classification routing ----------
def test_salary_term_forces_secret() -> None:
    c = classify_prompt("Cho tôi xem bảng lương của phòng kinh doanh")
    assert c.classification == "SECRET" and c.has_salary is True


def test_contact_pii_forces_confidential() -> None:
    c = classify_prompt("Gọi cho nhân viên qua 0912345678")
    assert c.classification == "CONFIDENTIAL"
    assert any(h.type == "PHONE" for h in c.pii_hits)


def test_clean_prompt_is_internal() -> None:
    c = classify_prompt("Doanh thu quý 3 là bao nhiêu?")
    assert c.classification == "INTERNAL" and c.pii_hits == ()


# ---------- scrub for model ----------
def test_scrub_drops_level4_pii_entirely() -> None:
    scrubbed = scrub_for_model("CCCD 012345678901 và số tài khoản 1234567890123456")
    assert "012345678901" not in scrubbed
    assert "1234567890123456" not in scrubbed
    assert "[REDACTED]" in scrubbed


def test_scrub_tokenises_level3_contacts_stably() -> None:
    a = scrub_for_model("email an@abc.vn")
    b = scrub_for_model("email an@abc.vn")
    assert a == b  # deterministic pseudonym
    assert "an@abc.vn" not in a
    assert "EMP-" in a


def test_scrub_uses_client_prefix_near_client_context() -> None:
    scrubbed = scrub_for_model("Khách hàng liên hệ client@partner.com")
    assert "CLI-" in scrubbed and "client@partner.com" not in scrubbed


def test_scrub_keeps_non_pii_numbers() -> None:
    text = "Doanh thu 1.500.000 đ, tăng 12,5%"
    assert scrub_for_model(text) == text


def test_redact_for_log_masks_pii() -> None:
    masked = redact_for_log("liên hệ 0912345678")
    assert "0912345678" not in masked


# ---------- end-to-end: the scrubbed message is what the gateway receives ----------
async def test_chat_sends_scrubbed_message_to_gateway(db_session) -> None:
    import uuid

    from app.core.deps import Principal
    from app.core.model_gateway.types import ChatRequest, ChatResponse, Usage
    from app.modules.ai.services.chat_service import ChatService
    from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

    seen: list[ChatRequest] = []

    class CaptureGateway:
        async def chat(self, req: ChatRequest) -> ChatResponse:
            seen.append(req)
            return ChatResponse(
                content="ok", provider="fixture", model="x", usage=Usage(5, 5),
            )  # fmt: skip

    user = Principal(
        user_id=uuid.uuid4(), role="CEO", permissions=frozenset(ROLE_PERMISSIONS["CEO"])
    )
    svc = ChatService(db_session, CaptureGateway())
    await svc.chat(user, "Gọi nhân viên qua 0912345678 giúp tôi")
    prompt = next(m.content for m in seen[0].messages if m.role == "user")
    assert "0912345678" not in prompt
    assert "EMP-" in prompt
    # phone PII elevated the routing to CONFIDENTIAL (local model only)
    assert seen[0].classification == "CONFIDENTIAL"
