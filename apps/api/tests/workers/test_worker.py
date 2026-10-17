"""TC-IDP-035 (base part, T-007): Celery config + idempotent base task by task_id (07 §5.1).

Full TC-IDP-035 (`process_document` + no duplicate `extracted_fields`) lands with T-211.
"""

import uuid
from typing import Any

import pytest
import redis

from app.core.config import get_config
from app.worker import (
    QUEUE_DEFAULT,
    QUEUE_IDP,
    RESULT_EXPIRES_S,
    SOFT_TIME_LIMIT_S,
    TIME_LIMIT_S,
    celery_app,
)
from app.workers.base import (
    KEY_PREFIX,
    IdempotentTask,
    InMemoryIdempotencyStore,
    RedisIdempotencyStore,
    retry_countdown,
)
from app.workers.system import ping


def test_config_time_limits_and_result_expires() -> None:
    conf = celery_app.conf
    assert conf.task_soft_time_limit == SOFT_TIME_LIMIT_S == 120
    assert conf.task_time_limit == TIME_LIMIT_S == 150
    assert conf.task_soft_time_limit < conf.task_time_limit
    assert conf.result_expires == RESULT_EXPIRES_S == 24 * 3600
    assert conf.task_serializer == "json"
    assert conf.accept_content == ["json"]
    assert conf.task_acks_late is True
    assert {q.name for q in conf.task_queues} == {QUEUE_DEFAULT, QUEUE_IDP}


def test_broker_from_config_service() -> None:
    cfg = get_config()
    assert celery_app.conf.broker_url == cfg.celery_broker_url.get_secret_value()
    assert celery_app.conf.result_backend == cfg.celery_result_backend.get_secret_value()


def test_all_tasks_use_idempotent_base_and_ping_registered() -> None:
    assert isinstance(ping, IdempotentTask)
    assert "app.workers.system.ping" in celery_app.tasks
    assert ping.max_retries == 3
    assert [retry_countdown(i) for i in range(4)] == [2, 8, 30, 30]


def _make_task(store: InMemoryIdempotencyStore, calls: list[Any], fail_first: bool = False) -> Any:
    @celery_app.task(
        name=f"tests.side_effect.{uuid.uuid4().hex}", idempotency_store=store, shared=False
    )
    def side_effect(doc_id: str) -> str:
        calls.append(doc_id)
        if fail_first and len(calls) == 1:
            raise RuntimeError("boom")
        return f"done:{doc_id}"

    return side_effect


@pytest.mark.usefixtures("eager")
def test_same_task_id_runs_side_effect_once() -> None:
    store, calls = InMemoryIdempotencyStore(), []
    task = _make_task(store, calls)
    task_id = "doc-1:extract:a1"  # 07 §5.1 format {document_id}:{step}:{attempt_key}
    first = task.apply_async(args=["doc-1"], task_id=task_id)
    second = task.apply_async(args=["doc-1"], task_id=task_id)
    assert first.get() == "done:doc-1"
    assert second.state == "IGNORED"  # duplicate skipped, no side effect
    assert calls == ["doc-1"]
    assert store.is_done(f"{task.name}:{task_id}")
    task.apply_async(args=["doc-1"], task_id="doc-1:extract:a2")
    assert calls == ["doc-1", "doc-1"]


@pytest.mark.usefixtures("eager")
def test_failed_run_releases_claim_so_retry_can_run() -> None:
    store, calls = InMemoryIdempotencyStore(), []
    task = _make_task(store, calls, fail_first=True)
    with pytest.raises(RuntimeError):
        task.apply_async(args=["doc-2"], task_id="doc-2:ocr:a1")
    assert task.apply_async(args=["doc-2"], task_id="doc-2:ocr:a1").get() == "done:doc-2"
    assert calls == ["doc-2", "doc-2"]


@pytest.mark.usefixtures("eager")
def test_is_already_processed_hook_skips() -> None:
    calls: list[str] = []

    class DbChecked(IdempotentTask):  # type: ignore[misc]
        idempotency_store = InMemoryIdempotencyStore()

        def is_already_processed(self, key: str) -> bool:
            return True  # e.g. T-211: ExtractionJob already past this step

    @celery_app.task(name=f"tests.hook.{uuid.uuid4().hex}", base=DbChecked, shared=False)
    def hooked() -> None:
        calls.append("x")

    hooked.apply_async(task_id="t-1")
    assert calls == []


def test_in_memory_store_semantics() -> None:
    s = InMemoryIdempotencyStore()
    assert s.acquire("k", 10)
    assert not s.acquire("k", 10)
    s.complete("k", 10)
    s.release("k")  # never erases a done marker
    assert s.is_done("k")
    assert not s.acquire("k", 10)
    assert s.acquire("expired", 0)  # ttl 0 → immediately expired
    assert s.acquire("expired", 10)


@pytest.mark.integration
def test_redis_store_against_live_redis() -> None:
    client = redis.Redis.from_url(get_config().redis_url.get_secret_value(), decode_responses=True)
    store = RedisIdempotencyStore(client)
    key = f"test:{uuid.uuid4().hex}"
    try:
        assert store.acquire(key, 30)
        assert not store.acquire(key, 30)
        assert 0 < client.ttl(KEY_PREFIX + key) <= 30
        store.release(key)
        assert store.acquire(key, 30)
        store.complete(key, 60)
        store.release(key)
        assert store.is_done(key)
        assert not store.acquire(key, 30)
        assert 30 < client.ttl(KEY_PREFIX + key) <= 60
    finally:
        client.delete(KEY_PREFIX + key)
