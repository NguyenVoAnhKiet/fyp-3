from __future__ import annotations

from dataclasses import dataclass

from .db import Database
from .schema import initialize_schema


@dataclass(slots=True)
class StorageManager:
    database: Database

    def initialize(self) -> None:
        with self.database.session() as connection:
            initialize_schema(connection)
