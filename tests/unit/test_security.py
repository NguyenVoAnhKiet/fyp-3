from __future__ import annotations

import pytest

from repositories.user_repository import UserRepository
from services.security import (
    AdminCredentialRateLimiter,
    RateLimitExceededError,
    SecurityService,
    hash_password,
    validate_password_strength,
    verify_password,
)


def test_hash_password_creates_verifiable_hash() -> None:
    hashed = hash_password("Secret123!")

    assert hashed != "Secret123!"
    assert verify_password("Secret123!", hashed)


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("Secret123!")

    assert not verify_password("Wrong123!", hashed)


def test_validate_password_strength_rejects_weak_password() -> None:
    with pytest.raises(ValueError):
        validate_password_strength("weakpass")


def test_security_service_rate_limits_admin_credential_creation(database) -> None:
    users = UserRepository(database)
    limiter = AdminCredentialRateLimiter(max_attempts=1, window_seconds=60)
    service = SecurityService(users, rate_limiter=limiter)

    service.create_admin_credential("admin", "StrongPass1!")

    with pytest.raises(RateLimitExceededError):
        service.create_admin_credential("admin", "StrongPass1!")
