from __future__ import annotations

import bcrypt
import re
import time
from collections import defaultdict, deque

from repositories.user_repository import UserRepository


_PASSWORD_MIN_LENGTH = 8


class RateLimitExceededError(RuntimeError):
    pass


def validate_password_strength(password: str) -> None:
    if not isinstance(password, str) or len(password) < _PASSWORD_MIN_LENGTH:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[^\w\s]", password):
        raise ValueError("Password must contain at least one special character")


class AdminCredentialRateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def check_and_record(self, identifier: str) -> None:
        now = time.monotonic()
        window_start = now - self.window_seconds
        attempts = self._attempts[identifier]
        while attempts and attempts[0] < window_start:
            attempts.popleft()
        if len(attempts) >= self.max_attempts:
            raise RateLimitExceededError("Too many admin credential creation attempts")
        attempts.append(now)


def hash_password(password: str) -> str:
    validate_password_strength(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


class SecurityService:
    def __init__(
        self,
        user_repository: UserRepository,
        rate_limiter: AdminCredentialRateLimiter | None = None,
    ) -> None:
        self.user_repository = user_repository
        self.rate_limiter = rate_limiter or AdminCredentialRateLimiter()

    def create_admin_credential(self, username: str, password: str) -> int:
        if not isinstance(username, str) or not username.strip():
            raise ValueError("username must be a non-empty string")
        self.rate_limiter.check_and_record(username.strip().lower())
        password_hash = hash_password(password)
        return self.user_repository.create_admin_credential(username.strip(), password_hash)
