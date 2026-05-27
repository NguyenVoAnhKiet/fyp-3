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

logger = logging.getLogger(__name__)

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
    """
    global _tz
    if not tz_name:
        _tz = timezone.utc
        return

    ZoneInfo = _load_zoneinfo()
    if ZoneInfo is None:
        logger.warning("zoneinfo not available (Python < 3.9), falling back to UTC")
        _tz = timezone.utc
        return

    try:
        _tz = ZoneInfo(tz_name)
    except (KeyError, OSError, TypeError):
        logger.warning("Unknown timezone '%s', falling back to UTC", tz_name)
        _tz = timezone.utc


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
