import pytest
from unittest.mock import MagicMock
from attendance_system.services.authentication_service import AuthenticationService
from attendance_system.repositories.admin_repository import AdminRepository

@pytest.fixture
def admin_repo():
    return MagicMock(spec=AdminRepository)

@pytest.fixture
def auth_service(admin_repo):
    return AuthenticationService(admin_repo)

def test_authenticate_success(auth_service, admin_repo):
    # Setup
    username = "admin"
    password = "correct_password"
    hashed = auth_service.hash_password(password)
    
    # Mock return value as a dict-like object
    admin_repo.get_by_username.return_value = {
        "username": username,
        "password_hash": hashed
    }
    
    # Execute
    result = auth_service.authenticate(username, password)
    
    # Verify
    assert result is True
    admin_repo.get_by_username.assert_called_once_with(username)

def test_authenticate_wrong_password(auth_service, admin_repo):
    # Setup
    username = "admin"
    admin_repo.get_by_username.return_value = {
        "username": username,
        "password_hash": auth_service.hash_password("correct_password")
    }
    
    # Execute
    result = auth_service.authenticate(username, "wrong_password")
    
    # Verify
    assert result is False

def test_authenticate_user_not_found(auth_service, admin_repo):
    # Setup
    admin_repo.get_by_username.return_value = None
    
    # Execute
    result = auth_service.authenticate("non_existent", "any_password")
    
    # Verify
    assert result is False

def test_authenticate_empty_inputs(auth_service):
    assert auth_service.authenticate("", "password") is False
    assert auth_service.authenticate("user", "") is False
    assert auth_service.authenticate(None, None) is False

def test_hash_password(auth_service):
    password = "test_password"
    hashed = auth_service.hash_password(password)
    assert hashed != password
    assert len(hashed) > 0
    import bcrypt
    assert bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
