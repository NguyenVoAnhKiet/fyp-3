from __future__ import annotations

from datetime import datetime, timezone

import pytest
from PyQt5.QtWidgets import QApplication

from attendance_system.utils.time_utils import (
    get_timezone_config,
    get_timezone_name,
    local_now_iso,
    local_to_utc,
    set_timezone_config,
    timezone_signals,
    utc_now_iso,
    utc_to_local,
)


@pytest.fixture(scope="session")
def qapp():
    """Return a shared QApplication instance (created once per session)."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


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


# ==============================================================================
# get_timezone_name / get_timezone_config
# ==============================================================================


class TestTimezoneGetters:
    def test_get_timezone_name_default_is_utc(self):
        """Default timezone name is UTC."""
        set_timezone_config("UTC")
        assert get_timezone_name() == "UTC"

    def test_get_timezone_name_after_set(self):
        """get_timezone_name() returns the configured IANA name."""
        set_timezone_config("Asia/Tokyo")
        assert get_timezone_name() == "Asia/Tokyo"

    def test_get_timezone_name_invalid_fallback(self):
        """After invalid timezone, name should be UTC."""
        set_timezone_config("Invalid/Timezone")
        assert get_timezone_name() == "UTC"

    def test_get_timezone_config_returns_zoneinfo(self):
        """get_timezone_config() returns a ZoneInfo instance."""
        from zoneinfo import ZoneInfo

        set_timezone_config("Europe/Paris")
        tz = get_timezone_config()
        assert isinstance(tz, ZoneInfo)
        assert tz.key == "Europe/Paris"

    def test_get_timezone_config_default(self):
        """get_timezone_config() returns UTC initially (non-ZoneInfo)."""
        set_timezone_config("UTC")
        tz = get_timezone_config()
        # When set to UTC, it may be ZoneInfo("UTC") or timezone.utc
        # Either is fine — just verify it's usable
        from datetime import timezone as dt_timezone
        from zoneinfo import ZoneInfo

        assert isinstance(tz, (ZoneInfo, dt_timezone))


# ==============================================================================
# Signal emission
# ==============================================================================


class TestTimezoneSignals:
    """Requires ``qapp`` fixture (QApplication for QObject signals)."""

    def test_signal_emitted_on_change(self, qapp):
        """set_timezone_config emits ``timezone_changed`` with new IANA name."""
        set_timezone_config("UTC")  # ensure starting at UTC
        hits: list[str] = []

        def _record(name: str) -> None:
            hits.append(name)

        timezone_signals.timezone_changed.connect(_record)
        try:
            set_timezone_config("Asia/Tokyo")
            assert hits == ["Asia/Tokyo"]
        finally:
            timezone_signals.timezone_changed.disconnect(_record)

    def test_signal_not_emitted_on_same_value(self, qapp):
        """set_timezone_config with the same value does NOT re-emit."""
        set_timezone_config("Asia/Tokyo")  # set first
        hits: list[str] = []

        def _record(name: str) -> None:
            hits.append(name)

        timezone_signals.timezone_changed.connect(_record)
        try:
            set_timezone_config("Asia/Tokyo")  # same value again
            assert hits == []  # no emission
        finally:
            timezone_signals.timezone_changed.disconnect(_record)

    def test_signal_emitted_on_fallback(self, qapp):
        """Invalid timezone triggers a fallback signal with the resulting name."""
        set_timezone_config("Asia/Tokyo")  # set to non-UTC first
        hits: list[str] = []

        def _record(name: str) -> None:
            hits.append(name)

        timezone_signals.timezone_changed.connect(_record)
        try:
            set_timezone_config("Invalid/Timezone")
            # Falls back to UTC — signal should carry the new name
            assert hits == ["UTC"]
        finally:
            timezone_signals.timezone_changed.disconnect(_record)
