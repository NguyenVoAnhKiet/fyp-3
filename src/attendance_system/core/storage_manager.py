from __future__ import annotations
import bcrypt
from dataclasses import dataclass

from .db import Database
from .schema import initialize_schema
from attendance_system.utils.time_utils import utc_now_iso


@dataclass(slots=True)
class StorageManager:
    database: Database

    def initialize(
        self, admin_username: str = "", admin_password: str = ""
    ) -> None:
        with self.database.session() as connection:
            initialize_schema(connection)
            self._seed_admin(connection, admin_username, admin_password)

    def _seed_admin(
        self, connection, admin_username: str, admin_password: str
    ) -> None:
        """Seed initial admin account if none exists.

        Credentials are resolved by ``SettingsResolver`` and passed in from
        the caller (``bootstrap.initialize_storage``).  Raises ``ValueError``
        if both are empty/unset and no admin account exists yet.
        """
        cursor = connection.execute("SELECT COUNT(*) FROM admin_credentials")
        if cursor.fetchone()[0] == 0:
            if not admin_username or not admin_password:
                raise ValueError(
                    "ADMIN_USERNAME and ADMIN_PASSWORD must be set in "
                    "the environment (or .env) when no admin account "
                    f"exists. Got: ADMIN_USERNAME="
                    f"{'<set>' if admin_username else '<missing/empty>'}, "
                    f"ADMIN_PASSWORD="
                    f"{'<set>' if admin_password else '<missing/empty>'}"
                )
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(
                admin_password.encode("utf-8"), salt
            ).decode("utf-8")
            now = utc_now_iso()
            connection.execute(
                "INSERT INTO admin_credentials "
                "(username, password_hash, created_at, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (admin_username, password_hash, now, now),
            )
