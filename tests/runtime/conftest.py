"""Shared test configuration.

The runtime suite must never read from or write to the developer's real
data directory. A test that creates an embedding or a database in the
project's ``data/`` directory would overwrite real local state, and the
result would depend on whether the developer happened to have an
embedding enrolled.

Every test therefore gets a temporary directory for the configured
embedding directory and database path.
"""

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def isolate_local_state(tmp_path_factory, monkeypatch):
    """Point the configured paths at a temporary directory.

    The settings are cached, so the cache is cleared before and after the
    test. Any module that captured the embedding directory at import time
    is corrected as well.
    """

    root = tmp_path_factory.mktemp("local-state")

    embedding_dir = root / "face_embeddings"
    embedding_dir.mkdir(parents=True, exist_ok=True)

    database_path = root / "attendance.db"

    monkeypatch.setenv("FACE_EMBEDDING_DIR", str(embedding_dir))
    monkeypatch.setenv("ATTENDANCE_DB_PATH", str(database_path))

    get_settings.cache_clear()

    _correct_imported_defaults(embedding_dir, database_path)

    yield

    get_settings.cache_clear()


def _correct_imported_defaults(embedding_dir, database_path) -> None:
    """Fix modules that captured a path when they were imported.

    A module level constant such as ``DEFAULT_EMBEDDING_DIR`` is bound
    at import time. When the module was imported before the temporary
    paths were in place, it would still point at the real directory.
    """

    import sys

    register_face = sys.modules.get("app.services.register_face")

    if register_face is not None:
        monkeypatched = getattr(register_face, "DEFAULT_EMBEDDING_DIR", None)

        if monkeypatched is not None:
            register_face.DEFAULT_EMBEDDING_DIR = embedding_dir
