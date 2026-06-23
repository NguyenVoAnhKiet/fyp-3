from __future__ import annotations
import logging

import bcrypt
from attendance_system.repositories.admin_repository import AdminRepository

logger = logging.getLogger(__name__)

class AuthenticationService:
    """Service for handling administrator authentication."""

    def __init__(self, admin_repo: AdminRepository):
        self._admin_repo = admin_repo

    def authenticate(self, username: str, password: str) -> bool:
        """
        Verify admin credentials.
        
        Args:
            username: The admin username.
            password: The plain-text password.
            
        Returns:
            True if authentication succeeds, False otherwise.
        """
        if not username or not password:
            return False

        record = self._admin_repo.get_by_username(username)
        if not record:
            return False

        # password_hash is stored as TEXT in DB, bcrypt needs bytes
        stored_hash = record["password_hash"]
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode("utf-8")

        provided_password = password.encode("utf-8")

        try:
            return bcrypt.checkpw(provided_password, stored_hash)
        except Exception as e:
            logger.warning("bcrypt check failed: %s", e)
            # Log error in real app, return False for security
            return False

    def hash_password(self, password: str) -> str:
        """Helper to generate a bcrypt hash for a password."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
