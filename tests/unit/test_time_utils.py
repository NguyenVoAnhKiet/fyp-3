from __future__ import annotations

from datetime import datetime, timezone
import pytest
from attendance_system.utils.time_utils import utc_now_iso


def test_utc_now_iso_returns_string():
    """utc_now_iso() should return a string."""
    result = utc_now_iso()
    assert isinstance(result, str)


def test_utc_now_iso_is_valid_format():
    """utc_now_iso() should return a valid ISO 8601 format string."""
    result = utc_now_iso()
    # datetime.fromisoformat will raise ValueError if invalid
    parsed = datetime.fromisoformat(result)
    # It should have UTC offset
    assert parsed.tzinfo is not None


def test_utc_now_iso_is_recent():
    """utc_now_iso() should be close to current UTC time."""
    result = utc_now_iso()
    parsed = datetime.fromisoformat(result)
    now = datetime.now(timezone.utc)
    
    # Difference should be less than 2 seconds
    diff = abs((now - parsed).total_seconds())
    assert diff < 2.0
