"""Test fixtures. Use a temp SQLite DB per test and stub the normalizer."""
from __future__ import annotations

import os
import tempfile
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

# Force a clean per-test DB BEFORE importing the app.
_tmpdir = tempfile.mkdtemp(prefix="cortex-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["NORMALIZER_URL"] = "http://normalizer.test"
os.environ["NORMALIZER_TIMEOUT_S"] = "5"
os.environ["NORMALIZER_MAX_RETRIES"] = "1"
os.environ["SAFETY_FAIL_LOUD"] = "true"


@pytest.fixture
def client() -> Iterator[TestClient]:
    # Import inside the fixture so the env vars above are picked up.
    from app.main import app  # noqa: WPS433

    with TestClient(app) as c:
        yield c
