"""Mutable, runtime DB-backed settings.

This module owns the thin CRUD layer over :class:`SystemSettingRepository`.
It is intentionally separate from :class:`attendance_system.core.config`
(``SystemConfig``) which holds *immutable, startup-resolved* configuration.

Why both?  Two different concerns:

* :class:`attendance_system.core.config.SystemConfig` — values that are
  resolved once at startup from CLI > env > DB > default and frozen for
  the lifetime of the process.  Used by services that need config at
  construction time.
* :class:`SettingsService` (this module) — the admin's runtime-mutable
  state in the ``system_settings`` table.  Used by the Admin UI to
  show current values and persist user edits.

The Admin UI writes through this service; startup-resolution of
defaults (env → DB on first run) is handled by
:meth:`attendance_system.core.config.SettingsResolver.seed_db_from_env`.
"""

from __future__ import annotations

from attendance_system.core.db import Database

from attendance_system.repositories.system_setting_repository import SystemSettingRepository


class SettingsService:
    """CRUD wrapper over the ``system_settings`` table.

    Read/write helpers are intentionally minimal — this class is the
    seam between the Admin UI and the database, not a config resolver.
    For startup-resolution with full CLI > env > DB > default
    precedence, use :class:`attendance_system.core.config.SettingsResolver`.
    """

    def __init__(self, database: Database) -> None:
        self.repository = SystemSettingRepository(database)

    def get(self, setting_key: str) -> str | None:
        row = self.repository.get(setting_key)
        return None if row is None else row["setting_value"]

    def set(self, setting_key: str, setting_value: str, value_type: str | None = None) -> None:
        self.repository.upsert(setting_key, setting_value, value_type)
