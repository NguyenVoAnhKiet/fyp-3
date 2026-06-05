from __future__ import annotations

# NOTE: bootstrap.py does not call load_dotenv().
# This module is invoked as a standalone CLI script via 'attendance-storage-init',
# which reads configuration from CLI arguments (--database-path) rather than .env.
# See AGENTS.md "Gotchas" for details.
#
# The config resolution is shared with ``main.py`` via
# :class:`attendance_system.core.config.SettingsResolver` in ``"init"`` mode.
# Init mode skips env seeding (because no .env is loaded) and only resolves
# the database path — other tunables default-fill.  See plan 0005.

import argparse
from pathlib import Path

from .config import SettingsResolver
from .db import Database, DatabaseConfig
from .storage_manager import StorageManager


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


def initialize_storage(database_path: Path) -> None:
    storage_manager = StorageManager(Database(DatabaseConfig(path=database_path)))
    storage_manager.initialize()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Shared resolver in init mode — does not load dotenv, does not seed DB.
    # Pass ``env={}`` explicitly so the resolver does not consult
    # ``os.environ`` either — bootstrap must be hermetic.
    resolver = SettingsResolver(mode="init")
    config = resolver.resolve(cli=args, env={}, db_reader=None)
    initialize_storage(config.database_path)
    print(f"Initialized storage at {config.database_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
