from __future__ import annotations

from services.security import hash_password, verify_password


def test_hash_password_creates_verifiable_hash() -> None:
    hashed = hash_password("secret-password")

    assert hashed != "secret-password"
    assert verify_password("secret-password", hashed)


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("secret-password")

    assert not verify_password("wrong-password", hashed)
