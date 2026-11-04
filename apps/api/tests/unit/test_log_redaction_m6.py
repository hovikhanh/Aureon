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


def test_uvicorn_access_lines_keep_their_args(capsys: pytest.CaptureFixture[str]) -> None:
    """Regression (seen on the stack): args=None broke uvicorn's AccessFormatter on every
    request. Clean lines are untouched; a line with URL credentials is masked arg by arg."""
    from uvicorn.logging import AccessFormatter

    log_redaction.install()
    log = logging.getLogger("uvicorn.access")
    handler = logging.StreamHandler()
    handler.setFormatter(AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s'))
    log.addHandler(handler)
    level, log.level = log.level, logging.INFO
    try:
        log.info('%s - "%s %s HTTP/%s" %d', "172.18.0.1:5000", "GET", "/api/v1/health", "1.1", 200)
        log.info('%s - "%s %s HTTP/%s" %d', "172.18.0.1:5000", "GET",
                 f"/x?u=postgresql://aureon:{SAMPLE}@db/x", "1.1", 200)  # fmt: skip
    finally:
        log.removeHandler(handler)
        log.setLevel(level)
    err = capsys.readouterr().err
    assert "Logging error" not in err
    assert '"GET /api/v1/health HTTP/1.1" 200' in err
    assert SAMPLE not in err
