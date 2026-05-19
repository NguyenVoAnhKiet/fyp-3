from __future__ import annotations

# NOTE: bootstrap.py does not call load_dotenv().
# This module is invoked as a standalone CLI script via 'attendance-storage-init',
# which reads configuration from CLI arguments (--database-path) rather than .env.
# See AGENTS.md "Gotchas" for details.

import argparse
import os
from pathlib import Path

from .db import Database, DatabaseConfig
from .storage_manager import StorageManager

DEFAULT_DATABASE_PATH = Path("attendance.db")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="attendance-storage-init",
        description="Initialize the local attendance database schema.",
    )
    parser.add_argument(
        "--database-path",
        default=os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE_PATH)),
        help="Path to the SQLite database file.",
    )
    return parser


def initialize_storage(database_path: Path) -> None:
    storage_manager = StorageManager(Database(DatabaseConfig(path=database_path)))
    storage_manager.initialize()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    database_path = Path(args.database_path)
    initialize_storage(database_path)
    print(f"Initialized storage at {database_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
