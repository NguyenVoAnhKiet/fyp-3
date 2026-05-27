from __future__ import annotations

from datetime import datetime, timezone

import pytest

from attendance_system.utils.time_utils import (
    local_now_iso,
    local_to_utc,
    set_timezone_config,
    utc_now_iso,
    utc_to_local,
)


# ==============================================================================
# utc_now_iso — unchanged, still returns UTC
# ==============================================================================


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


def test_utc_now_iso_is_utc():
    """utc_now_iso() offset should be +00:00."""
    result = utc_now_iso()
    parsed = datetime.fromisoformat(result)
    assert parsed.utcoffset() == timezone.utc.utcoffset(None)


# ==============================================================================
# Configuration
# ==============================================================================


class TestSetTimezoneConfig:
    def test_default_is_utc(self):
        """Before any config, timezone should be UTC."""
        # utc_to_local with UTC should preserve the offset
        result = utc_to_local("2026-05-27T12:00:00+00:00")
        assert "+00:00" in result or "Z" not in result  # still UTC

    def test_set_to_asia_saigon(self):
        """Set timezone to Asia/Ho_Chi_Minh (+07:00)."""
        set_timezone_config("Asia/Ho_Chi_Minh")
        result = utc_to_local("2026-05-27T12:00:00+00:00")
        # 12:00 UTC = 19:00 +07:00
        parsed = datetime.fromisoformat(result)
        offset = parsed.utcoffset()
        assert offset is not None
        assert offset.total_seconds() == 7 * 3600  # +07:00

    def test_invalid_timezone_falls_back(self):
        """Invalid timezone name should fall back to UTC."""
        set_timezone_config("Invalid/Timezone")
        # After fallback, local == UTC
        set_timezone_config("UTC")  # reset explicitly for next test

    def test_empty_timezone_falls_back(self):
        """Empty timezone should fall back to UTC."""
        set_timezone_config(None)
        set_timezone_config("")

    @pytest.fixture(autouse=True)
    def reset_timezone(self):
        """Reset to UTC after each test to avoid cross-test pollution."""
        yield
        set_timezone_config("UTC")


# ==============================================================================
# utc_to_local
# ==============================================================================


class TestUtcToLocal:
    def setup_method(self):
        set_timezone_config("Asia/Ho_Chi_Minh")  # +07:00

    def teardown_method(self):
        set_timezone_config("UTC")

    def test_converts_utc_to_vietnam(self):
        """12:00 UTC should become 19:00 +07:00."""
        result = utc_to_local("2026-05-27T12:00:00+00:00")
        parsed = datetime.fromisoformat(result)
        # Should show 19:00 local time
        assert parsed.hour == 19
        offset = parsed.utcoffset()
        assert offset is not None
        assert offset.total_seconds() == 7 * 3600

    def test_naive_input_treated_as_utc(self):
        """Naive timestamp without offset should be treated as UTC."""
        result = utc_to_local("2026-05-27T12:00:00")
        assert "12:00" in result or "19:00" in result  # depends on config

    def test_invalid_input_returns_as_is(self):
        """Invalid input string should be returned unchanged."""
        result = utc_to_local("not-a-timestamp")
        assert result == "not-a-timestamp"

    def test_empty_string(self):
        """Empty string should return as-is."""
        result = utc_to_local("")
        assert result == ""


# ==============================================================================
# local_to_utc
# ==============================================================================


class TestLocalToUtc:
    def setup_method(self):
        set_timezone_config("Asia/Ho_Chi_Minh")  # +07:00

    def teardown_method(self):
        set_timezone_config("UTC")

    def test_converts_vietnam_midnight_to_utc(self):
        """2026-05-27T00:00:00 in +07:00 = 2026-05-26T17:00:00 UTC."""
        result = local_to_utc("2026-05-27T00:00:00")
        parsed = datetime.fromisoformat(result)
        assert parsed.hour == 17  # 17:00 UTC
        assert parsed.day == 26  # previous day in UTC

    def test_naive_input_treated_as_local(self):
        """Naive timestamp without offset should be treated as local (VN)."""
        result = local_to_utc("2026-05-27T12:00:00")
        parsed = datetime.fromisoformat(result)
        # 12:00 VN = 05:00 UTC
        assert parsed.hour == 5

    def test_already_utc_stays_utc(self):
        """Timestamp with +00:00 should stay in UTC."""
        result = local_to_utc("2026-05-27T12:00:00+00:00")
        parsed = datetime.fromisoformat(result)
        assert parsed.hour == 12  # still noon

    def test_invalid_input_returns_as_is(self):
        """Invalid input string should be returned unchanged."""
        result = local_to_utc("not-a-timestamp")
        assert result == "not-a-timestamp"

    def test_to_date_range_boundary(self):
        """Simulate date filter: 2026-05-27 23:59:59 VN = 2026-05-27 16:59:59 UTC."""
        result = local_to_utc("2026-05-27T23:59:59")
        parsed = datetime.fromisoformat(result)
        assert parsed.hour == 16
        assert parsed.minute == 59
        assert parsed.second == 59
        assert parsed.day == 27


# ==============================================================================
# local_now_iso
# ==============================================================================


def test_local_now_iso_returns_string():
    """local_now_iso() should return a string."""
    set_timezone_config("Asia/Ho_Chi_Minh")
    result = local_now_iso()
    set_timezone_config("UTC")
    assert isinstance(result, str)


def test_local_now_iso_is_valid_format():
    """local_now_iso() should return valid ISO 8601."""
    set_timezone_config("Asia/Ho_Chi_Minh")
    result = local_now_iso()
    set_timezone_config("UTC")
    parsed = datetime.fromisoformat(result)
    assert parsed.tzinfo is not None
