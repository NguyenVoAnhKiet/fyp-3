"""
Timezone-aware time utilities.

Storage layer always uses UTC (via ``utc_now_iso()``).
Presentation layer converts to the configured local timezone via
``utc_to_local()`` / ``local_now_iso()``.

Configure with ``TIMEZONE`` env var (e.g. ``Asia/Ho_Chi_Minh``).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class _TimezoneSignals(QObject):
    """Module-level signal bus for timezone changes."""

    timezone_changed = pyqtSignal(str)


# Module-level singleton — safe to create before QApplication (only widgets need it).
_signals = _TimezoneSignals()
timezone_signals = _signals  # public alias for external connection

# Module-level timezone: defaults to UTC, overridden by set_timezone_config()
_tz = timezone.utc


def _load_zoneinfo() -> type | None:
    """Return ``zoneinfo.ZoneInfo`` if available, else ``None``."""
    try:
        import zoneinfo  # Python 3.9+

        return zoneinfo.ZoneInfo  # type: ignore[return-value]
    except ImportError:
        return None


def set_timezone_config(tz_name: str | None) -> None:
    """Configure the local timezone from *tz_name*.

    Falls back to UTC when *tz_name* is empty or invalid.
    Logs a warning when the fallback is used.

    Emits :attr:`_TimezoneSignals.timezone_changed` when the effective
    timezone differs from the previous value.
    """
    global _tz
    old_tz = _tz

    if not tz_name:
        _tz = timezone.utc
    else:
        ZoneInfo = _load_zoneinfo()
        if ZoneInfo is None:
            logger.warning("zoneinfo not available (Python < 3.9), falling back to UTC")
            _tz = timezone.utc
        else:
            try:
                _tz = ZoneInfo(tz_name)
            except (KeyError, OSError, TypeError):
                logger.warning("Unknown timezone '%s', falling back to UTC", tz_name)
                _tz = timezone.utc

    # Emit signal when the resolved timezone changes
    old_name = str(old_tz.key) if hasattr(old_tz, "key") else "UTC"
    new_name = str(_tz.key) if hasattr(_tz, "key") else "UTC"
    if new_name != old_name:
        _signals.timezone_changed.emit(new_name)


# ---------------------------------------------------------------------------
# Getters
# ---------------------------------------------------------------------------


def get_timezone_name() -> str:
    """Return the current IANA timezone name (e.g. ``"Asia/Ho_Chi_Minh"``)."""
    return str(_tz.key) if hasattr(_tz, "key") else "UTC"


def get_timezone_config():
    """Return the current timezone object (a :class:`zoneinfo.ZoneInfo`)."""
    return _tz


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string.

    This is the **storage** clock — all database timestamps use UTC.
    Signature unchanged for backward compatibility.
    """
    return datetime.now(timezone.utc).isoformat()


def local_now_iso() -> str:
    """Return the current time in the configured local timezone as ISO-8601."""
    return datetime.now(_tz).isoformat()


def utc_to_local(iso_str: str) -> str:
    """Convert a UTC ISO-8601 string to the configured local timezone.

    Returns the input unchanged if it cannot be parsed (fail-safe).
    """
    try:
        dt = datetime.fromisoformat(iso_str)
        # Attach UTC tzinfo if naive (old data before timezone support)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_tz).isoformat()
    except (ValueError, TypeError):
        logger.warning("Cannot parse timestamp '%s', returning as-is", iso_str)
        return iso_str


def local_to_utc(iso_str: str) -> str:
    """Interpret *iso_str* as local time and convert to UTC ISO-8601.

    Used for date filtering: a UI date like ``2026-05-27T00:00:00``
    (meaning midnight VN time) is converted to the equivalent UTC moment.
    """
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_tz)
        return dt.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        logger.warning("Cannot parse timestamp '%s', returning as-is", iso_str)
        return iso_str
