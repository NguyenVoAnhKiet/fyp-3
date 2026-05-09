from __future__ import annotations

import pytest
from attendance_system.repositories.recognition_event_repository import RecognitionEventRepository
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.repositories.session_repository import SessionRepository


@pytest.fixture
def user_id(database):
    repo = UserRepository(database)
    return repo.create("S001", "John Doe")


@pytest.fixture
def session_id(database):
    repo = SessionRepository(database)
    return repo.create("CS101", "A1", 0.5, 0.6)


@pytest.fixture
def repo(database):
    return RecognitionEventRepository(database)


def test_create_success(repo, session_id, user_id):
    """create() should store a valid event and return its ID."""
    event_id = repo.create(
        session_id=session_id,
        user_id=user_id,
        event_time="2024-01-01T12:00:00Z",
        result="success",
        liveness_score=0.9,
        similarity_score=0.95,
        details="Match found"
    )
    assert event_id > 0
    
    events = repo.list_by_session(session_id)
    assert len(events) == 1
    assert events[0]["id"] == event_id
    assert events[0]["result"] == "success"
    assert events[0]["liveness_score"] == 0.9
    assert events[0]["similarity_score"] == 0.95


def test_create_with_none_user(repo, session_id):
    """create() should accept None for user_id (e.g. for spoof/unrecognized)."""
    event_id = repo.create(
        session_id=session_id,
        user_id=None,
        event_time="2024-01-01T12:00:01Z",
        result="spoof_warning"
    )
    assert event_id > 0
    
    events = repo.list_by_session(session_id)
    assert events[0]["user_id"] is None
    assert events[0]["result"] == "spoof_warning"


def test_create_validation_errors(repo):
    """create() should validate inputs using base repository helpers."""
    # Invalid session_id
    with pytest.raises(ValueError, match="session_id must be a positive integer"):
        repo.create(0, 1, "2024-01-01T12:00:00Z", "success")
        
    # Invalid user_id
    with pytest.raises(ValueError, match="user_id must be a positive integer"):
        repo.create(1, -1, "2024-01-01T12:00:00Z", "success")
        
    # Empty event_time
    with pytest.raises(ValueError, match="event_time must be a non-empty string"):
        repo.create(1, 1, "", "success")
        
    # Empty result
    with pytest.raises(ValueError, match="result must be a non-empty string"):
        repo.create(1, 1, "2024-01-01T12:00:00Z", "")


def test_list_by_session_ordering(repo, session_id, user_id):
    """list_by_session() should return events ordered by ID."""
    repo.create(session_id, user_id, "2024-01-01T12:00:00Z", "success")
    repo.create(session_id, user_id, "2024-01-01T12:00:05Z", "success")
    
    events = repo.list_by_session(session_id)
    assert len(events) == 2
    assert events[0]["id"] < events[1]["id"]


def test_list_by_session_empty(repo):
    """list_by_session() should return an empty list if no events found."""
    events = repo.list_by_session(999)
    assert events == []


def test_list_by_session_invalid_id(repo):
    """list_by_session() should reject non-positive session IDs."""
    with pytest.raises(ValueError, match="session_id must be a positive integer"):
        repo.list_by_session(-1)
