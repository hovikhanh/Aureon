"""TC-M6-05 — R-DEC-167 / CLAUDE.md §6.4: log lines and tracebacks never carry secrets.

All values are made-up samples. The record factory is installed once and covers every logger /
handler (a caplog handler here), including a traceback rendered from `logger.exception`.
"""

import logging

import pytest

from app.core import log_redaction
from app.core.log_redaction import redact

SAMPLE = "Sample-Pa55word-not-real"
# assembled at runtime so secret scanners do not read the sample as a real key
PEM_BEGIN, PEM_END = "-----BEGIN " + "PRIVATE KEY-----", "-----END " + "PRIVATE KEY-----"


@pytest.mark.parametrize(
    "line",
    [
        f"input_value={{'database_url': 'postgre...ssword': '{SAMPLE}'}}, input_type=dict]",
        f"'demo_admin_password': '{SAMPLE}'",
        f'"omniroute_api_key": "{SAMPLE}"',
        f"DEMO_ADMIN_PASSWORD={SAMPLE}",
        f"connect postgresql+psycopg://aureon:{SAMPLE}@localhost:5432/aureon",
        f"{PEM_BEGIN}\nMIIE{SAMPLE}\n{PEM_END}",
        f"{PEM_BEGIN}\nMIIE{SAMPLE}",  # cut-off key (as in a truncated dump)
    ],
)
def test_redact(line: str) -> None:
    assert SAMPLE not in redact(line)


def test_ordinary_text_is_kept() -> None:
    line = "status=FAILED reason=EXTRACTION_FAILED doc=74ac18ea tokens_out=2048"
    assert redact(line) == line


def test_installed_factory_masks_messages_args_and_tracebacks(
    caplog: pytest.LogCaptureFixture,
) -> None:
    log_redaction.install()
    log_redaction.install()  # idempotent
    log = logging.getLogger("app.test.redaction")
    with caplog.at_level(logging.INFO, logger="app.test.redaction"):
        log.info("login with password=%s", SAMPLE)
        try:
            raise ValueError(f"bad settings: 'demo_admin_password': '{SAMPLE}'")
        except ValueError:
            log.exception("config failed")
    text = caplog.text + "\n".join(r.exc_text or "" for r in caplog.records)
    assert SAMPLE not in text
    assert "config failed" in text and "ValueError" in text
