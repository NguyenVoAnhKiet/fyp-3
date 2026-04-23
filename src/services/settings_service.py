from __future__ import annotations

from core.db import Database

from repositories.system_setting_repository import SystemSettingRepository


class SettingsService:
    def __init__(self, database: Database) -> None:
        self.repository = SystemSettingRepository(database)

    def get(self, setting_key: str) -> str | None:
        row = self.repository.get(setting_key)
        return None if row is None else row["setting_value"]

    def set(self, setting_key: str, setting_value: str, value_type: str | None = None) -> None:
        self.repository.upsert(setting_key, setting_value, value_type)

