from __future__ import annotations

from datetime import datetime, timezone

from core.db import Database

from .base_repository import BaseRepository


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SystemSettingRepository(BaseRepository):
    def __init__(self, database: Database) -> None:
        super().__init__(database)

    def upsert(self, setting_key: str, setting_value: str, value_type: str | None = None) -> None:
        timestamp = _utc_now()
        self.execute(
            """
            INSERT INTO system_settings(setting_key, setting_value, value_type, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                value_type = excluded.value_type,
                updated_at = excluded.updated_at
            """,
            (setting_key, setting_value, value_type, timestamp),
        )

    def get(self, setting_key: str):
        return self.fetch_one("SELECT * FROM system_settings WHERE setting_key = ?", (setting_key,))

    def list_all(self):
        return self.fetch_all("SELECT * FROM system_settings ORDER BY setting_key")

    def delete(self, setting_key: str) -> None:
        self.execute("DELETE FROM system_settings WHERE setting_key = ?", (setting_key,))

