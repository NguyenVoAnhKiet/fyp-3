from __future__ import annotations

from attendance_system.core.db import Database
from attendance_system.utils.time_utils import utc_now_iso

from .base_repository import BaseRepository


class SystemSettingRepository(BaseRepository):
    def __init__(self, database: Database) -> None:
        super().__init__(database)

    def upsert(self, setting_key: str, setting_value: str, value_type: str | None = None) -> None:
        self.require_non_empty_text(setting_key, "setting_key")
        self.require_non_empty_text(setting_value, "setting_value")
        if value_type is not None:
            self.require_non_empty_text(value_type, "value_type")
        timestamp = utc_now_iso()
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
        self.require_non_empty_text(setting_key, "setting_key")
        return self.fetch_one("SELECT * FROM system_settings WHERE setting_key = ?", (setting_key,))

    def list_all(self):
        return self.fetch_all("SELECT * FROM system_settings ORDER BY setting_key")

    def delete(self, setting_key: str) -> None:
        self.require_non_empty_text(setting_key, "setting_key")
        self.execute("DELETE FROM system_settings WHERE setting_key = ?", (setting_key,))

