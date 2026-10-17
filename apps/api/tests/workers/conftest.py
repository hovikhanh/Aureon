"""Fixtures for Celery worker tests (T-007, TC-IDP-035)."""

from collections.abc import Iterator

import pytest

from app.worker import celery_app


@pytest.fixture
def eager() -> Iterator[None]:
    """Run tasks in-process; restore conf afterwards (other tests share celery_app)."""
    prev = (celery_app.conf.task_always_eager, celery_app.conf.task_eager_propagates)
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager, celery_app.conf.task_eager_propagates = prev
