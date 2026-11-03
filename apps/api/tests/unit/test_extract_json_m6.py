"""TC-M6-02 (unit) — `ModelGateway.extract()` parses fenced JSON and names a truncated answer.

Live OmniRoute `cc/` ignored `response_format` and wrapped the JSON in ```json … ```; a long
answer hit the 2048-token cap (`finish_reason=length`). Both used to surface as a bare
"not valid JSON" with no reason.
"""

import pytest

from app.core.errors import AIError
from app.core.model_gateway import ChatRequest, ChatResponse, Message, ModelGateway
from app.core.model_gateway.gateway import _unfence

REQ = ChatRequest(task="extract", caller_module="idp", messages=(Message("user", "x"),),
                  json_schema={"type": "object"})  # fmt: skip


class _Gw(ModelGateway):
    def __init__(self, content: str, finish: str = "stop") -> None:
        super().__init__(None)
        self.content, self.finish = content, finish

    async def chat(self, req: ChatRequest) -> ChatResponse:
        return ChatResponse(content=self.content, provider="omniroute", model="claude-sonnet-5",
                            finish_reason=self.finish)  # fmt: skip


@pytest.mark.parametrize(
    "raw", ['{"a": 1}', '```json\n{"a": 1}\n```', '```\n{"a": 1}```', ' ```JSON {"a": 1} ``` ']
)
def test_unfence(raw: str) -> None:
    assert _unfence(raw).strip() == '{"a": 1}'


async def test_fenced_answer_is_parsed() -> None:
    assert (await _Gw('```json\n{"code": "PERIOD_REPORT"}\n```').extract(REQ)).data == {
        "code": "PERIOD_REPORT"
    }


@pytest.mark.parametrize(("finish", "reason"), [("length", "truncated"), ("stop", "invalid_json")])
async def test_unusable_answer_names_the_reason(finish: str, reason: str) -> None:
    with pytest.raises(AIError) as err:
        await _Gw('```json\n{"kpi_code": {"value": null, "confid', finish).extract(REQ)
    assert err.value.code == "AI_FUNCTION_CALL_FAILED" and err.value.details["reason"] == reason
