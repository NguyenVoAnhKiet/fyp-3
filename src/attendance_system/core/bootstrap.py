from __future__ import annotations

# NOTE: bootstrap.py now calls load_dotenv() so that ADMIN_USERNAME /
# ADMIN_PASSWORD can be sourced from .env for admin seeding.  The
# SettingsResolver resolves these from os.environ and places them on the
# SystemConfig, so StorageManager no longer reads env vars directly.
#
# This module uses ``env={}`` for path resolution to remain hermetic on
# non-admin tunables, while admin credentials are resolved from the
# real process environment by config.py.
# See plan 0005 for the config architecture.

import argparse
from pathlib import Path

from dotenv import load_dotenv

from .config import SettingsResolver
from .db import Database, DatabaseConfig
from .storage_manager import StorageManager
from ..services.settings_service import SettingsService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="attendance-storage-init",
        description="Initialize the local attendance database schema.",
    )
    parser.add_argument(
        "--database-path",
        default=None,
        help="Path to the SQLite database file (default: attendance.db).",
    )
    return parser


def initialize_storage(
    database_path: Path,
    admin_username: str = "",
    admin_password: str = "",
) -> None:
    storage_manager = StorageManager(Database(DatabaseConfig(path=database_path)))
    storage_manager.initialize(
        admin_username=admin_username, admin_password=admin_password
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Load .env so ADMIN_USERNAME / ADMIN_PASSWORD are available for
    # admin seeding (read via resolver from os.environ).
    load_dotenv()

    resolver = SettingsResolver(mode="init")
    config = resolver.resolve(cli=args, env={}, db_reader=None)
    initialize_storage(
        config.database_path,
        admin_username=config.admin_username,
        admin_password=config.admin_password,
    )

    # Seed DB defaults (system_settings) to match what main.py does at startup.
    db = Database(DatabaseConfig(path=config.database_path))
    settings_service = SettingsService(db)
    resolver.seed_db_from_defaults(settings=settings_service)

    print(f"Initialized storage at {config.database_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
