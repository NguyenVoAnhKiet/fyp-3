from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def database(tmp_path: Path):
    from core.db import Database, DatabaseConfig
    from core.storage_manager import StorageManager

    db = Database(DatabaseConfig(path=tmp_path / "database.db"))
    StorageManager(db).initialize()
    return db

