from __future__ import annotations

from pathlib import Path
import sys

# MUST import onnxruntime before PyQt5 to avoid DLL conflicts on Windows
try:
    import onnxruntime  # noqa
except ImportError:
    pass

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from attendance_system.core.db import Database, DatabaseConfig
    from attendance_system.core.storage_manager import StorageManager

    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "Admin@1234")

    db = Database(DatabaseConfig(path=tmp_path / "database.db"))
    StorageManager(db).initialize(admin_username="admin", admin_password="Admin@1234")
    return db

