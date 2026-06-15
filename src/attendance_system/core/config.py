"""Centralized configuration resolution.

This module owns the **single source of truth** for configuration resolution
order (CLI > env > DB > default) and the one-time env→DB seeding pattern.

Architecture (see ``docs/plans/active/0005-system-config-resolver.md``):

* :class:`SystemConfig` — frozen dataclass of resolved tunables (data).
* :class:`SettingsResolver` — class that performs the resolution work
  (behavior).  Has two modes:

  - ``"runtime"`` (default) — full resolution: CLI > env > DB > default.
    Used by ``main.py``.
  - ``"init"`` — minimal resolution for ``attendance-storage-init``:
    only ``database_path`` matters; ``load_dotenv()`` is skipped so the
    init command does not pull in environment values meant for runtime.

* :func:`resolve_config` — convenience factory wiring up the typical
  runtime caller.

Defaults live in :mod:`attendance_system.core.defaults`.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import defaults

# Public re-exports
__all__ = [
    "ResolutionMode",
    "SystemConfig",
    "SettingsResolver",
    "resolve_config",
]


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

ResolutionMode = Literal["runtime", "init"]


class _SettingsServiceLike(Protocol):
    """Structural type for the DB layer used by the resolver.

    ``SettingsService`` satisfies this; tests can pass a fake.
    """

    def get(self, setting_key: str) -> str | None: ...
    def set(
        self, setting_key: str, setting_value: str, value_type: str | None = ...
    ) -> None: ...


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class SystemConfig:
    """Immutable, fully-resolved system configuration.

    Every tunable lives here, exactly once.  Constructed by
    :class:`SettingsResolver` at startup; passed to services and UI as a
    single injected value.  ``frozen=True`` makes it hashable and protects
    against accidental post-construction mutation.
    """

    # --- Paths ---
    database_path: Path
    detection_model_path: Path
    recognition_model_path: Path
    liveness_model_path: Path | None  # ``None`` when antispoof disabled
    headpose_model_path: Path

    # --- Camera / feature flags ---
    camera_index: int
    antispoof_enabled: bool
    headpose_enabled: bool

    # --- AI thresholds (resolved at startup; mutable via Admin UI later) ---
    liveness_threshold: float
    similarity_threshold: float

    # --- Hybrid liveness decider ---
    hybrid_voting_window: int
    hybrid_boost_amount: float
    hybrid_liveness_enabled: bool
    recognition_interval: int

    # --- Timezone (mutable via Admin UI) ---
    timezone: str

    # --- Attendance UX (mutable via Admin UI) ---
    attendance_freeze_seconds: int
    attendance_freeze_sound_enabled: bool


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


#: Env-var → DB-key mapping for seeded values.  Centralized so adding a new
#: tunable only touches one place.  Env-var names mirror ``.env.example``.
_SEEDABLE: tuple[tuple[str, str, str], ...] = (
    # (env_var, db_key, value_type)
    ("TIMEZONE", "timezone", "str"),
    ("FACE_ANTISPOOF_CONFIDENCE_THRESHOLD", "liveness_threshold", "float"),
    ("FACE_SIMILARITY_THRESHOLD", "similarity_threshold", "float"),
    ("ATTENDANCE_FREEZE_SECONDS", "attendance_freeze_seconds", "int"),
    ("ATTENDANCE_FREEZE_SOUND_ENABLED", "attendance_freeze_sound_enabled", "bool"),
    ("HYBRID_VOTING_WINDOW", "hybrid_voting_window", "int"),
    ("HYBRID_BOOST_AMOUNT", "hybrid_boost_amount", "float"),
    ("HYBRID_LIVENESS_ENABLED", "hybrid_liveness_enabled", "bool"),
    ("RECOGNITION_INTERVAL", "recognition_interval", "int"),
)


# Truthy / falsy string sets for env-var bool parsing
_BOOL_TRUE: frozenset[str] = frozenset({"1", "true", "yes", "on"})
_BOOL_FALSE: frozenset[str] = frozenset({"0", "false", "no", "off"})


class SettingsResolver:
    """Resolves :class:`SystemConfig` from CLI > env > DB > default.

    Args:
        mode: ``"runtime"`` (default) or ``"init"``.  In init mode the
            resolver only resolves ``database_path`` and skips env seeding
            (because ``bootstrap.py`` does not call ``load_dotenv()`` and
            should not mutate DB values from environment).

    Resolution precedence (per tunable):

    1. **CLI** — argparse value, if not ``None`` and (for strings) non-empty.
    2. **Env** — ``os.environ[key]`` if set and non-empty (with int/bool
       parsing handled here, not at call site).
    3. **DB** — ``db_reader(db_key)`` if a reader is provided and returns
       a value.  Allows tests to inject a fake or skip the DB layer.
    4. **Default** — from :mod:`attendance_system.core.defaults`.
    """

    def __init__(self, mode: ResolutionMode = "runtime") -> None:
        if mode not in ("runtime", "init"):
            raise ValueError(
                f"Invalid resolver mode: {mode!r}; expected 'runtime' or 'init'"
            )
        self._mode: ResolutionMode = mode

    @property
    def mode(self) -> ResolutionMode:
        """``"runtime"`` or ``"init"``."""
        return self._mode

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        cli: argparse.Namespace | None = None,
        env: Mapping[str, str] | None = None,
        db_reader: Callable[[str], str | None] | None = None,
    ) -> SystemConfig:
        """Build a :class:`SystemConfig` using CLI > env > DB > default.

        Args:
            cli: Parsed argparse ``Namespace`` (or ``None``).  String values
                are treated as missing if empty (``""``); ints as missing
                if ``None``.
            env: Environment mapping; defaults to :data:`os.environ` when
                ``None``.  Empty strings count as missing.
            db_reader: Callable that returns the DB value for a setting
                key (or ``None`` if absent).  Pass ``None`` to skip the
                DB layer entirely.

        Returns:
            Fully-resolved, immutable :class:`SystemConfig`.
        """
        env_map = os.environ if env is None else env
        cli_obj = cli if cli is not None else argparse.Namespace()
        read_db = db_reader if db_reader is not None else (lambda _k: None)

        # --- Paths (CLI > env > default; DB is not consulted for paths) ---
        database_path = self._resolve_path(
            getattr(cli_obj, "database_path", None),
            env_map.get("DATABASE_PATH"),
            defaults.DEFAULT_DATABASE_PATH,
        )
        recognition_model_path = self._resolve_path(
            getattr(cli_obj, "recognition_model", None),
            env_map.get("FACE_RECOGNITION_MODEL_PATH"),
            defaults.DEFAULT_RECOGNITION_MODEL_PATH,
        )
        detection_model_path = self._resolve_path(
            getattr(cli_obj, "detector_model", None),
            env_map.get("FACE_DETECTOR_MODEL_PATH"),
            defaults.DEFAULT_DETECTOR_MODEL_PATH,
        )
        headpose_model_path = self._resolve_path(
            getattr(cli_obj, "headpose_model", None),
            env_map.get("FACE_HEADPOSE_MODEL_PATH"),
            defaults.DEFAULT_HEADPOSE_MODEL_PATH,
        )

        # --- Feature flags (CLI > env > default; no DB layer for these) ---
        # ``--camera-index`` is the only CLI flag for these, so we resolve
        # it the same way as before: CLI > env > default.
        camera_index = self._resolve_int(
            getattr(cli_obj, "camera_index", None),
            env_map.get("CAMERA_INDEX"),
            None,  # DB is not consulted for camera_index
            defaults.DEFAULT_CAMERA_INDEX,
        )
        antispoof_enabled = self._resolve_bool(
            None,  # no CLI flag for this today
            env_map.get("FACE_ANTISPOOF_ENABLED"),
            None,  # DB is not consulted for feature flags
            defaults.DEFAULT_ANTISPOOF_ENABLED,
        )
        headpose_enabled = self._resolve_bool(
            None,
            env_map.get("FACE_HEADPOSE_ENABLED"),
            None,  # DB is not consulted for feature flags
            defaults.DEFAULT_HEADPOSE_ENABLED,
        )

        # In init mode we don't resolve the rest — bootstrap only needs
        # the database path.  Return early with sensible defaults for the
        # rest so callers can still construct a valid SystemConfig.
        if self._mode == "init":
            return SystemConfig(
                database_path=database_path,
                detection_model_path=detection_model_path,
                recognition_model_path=recognition_model_path,
                liveness_model_path=None,
                headpose_model_path=headpose_model_path,
                camera_index=camera_index,
                antispoof_enabled=antispoof_enabled,
                headpose_enabled=headpose_enabled,
                liveness_threshold=defaults.DEFAULT_LIVENESS_THRESHOLD,
                similarity_threshold=defaults.DEFAULT_SIMILARITY_THRESHOLD,
                timezone=defaults.DEFAULT_TIMEZONE,
                attendance_freeze_seconds=defaults.DEFAULT_ATTENDANCE_FREEZE_SECONDS,
                attendance_freeze_sound_enabled=(
                    defaults.DEFAULT_ATTENDANCE_FREEZE_SOUND_ENABLED
                ),
                hybrid_voting_window=defaults.DEFAULT_HYBRID_VOTING_WINDOW,
                hybrid_boost_amount=defaults.DEFAULT_HYBRID_BOOST_AMOUNT,
                hybrid_liveness_enabled=defaults.DEFAULT_HYBRID_LIVENESS_ENABLED,
                recognition_interval=defaults.DEFAULT_RECOGNITION_INTERVAL,
            )

        # --- Thresholds (CLI > env > DB > default) ---
        liveness_threshold = self._resolve_float(
            None,
            env_map.get("FACE_ANTISPOOF_CONFIDENCE_THRESHOLD"),
            read_db("liveness_threshold"),
            defaults.DEFAULT_LIVENESS_THRESHOLD,
        )
        similarity_threshold = self._resolve_float(
            None,
            env_map.get("FACE_SIMILARITY_THRESHOLD"),
            read_db("similarity_threshold"),
            defaults.DEFAULT_SIMILARITY_THRESHOLD,
        )

        # --- Hybrid liveness decider (CLI > env > DB > default) ---
        hybrid_voting_window = self._resolve_int(
            None,
            env_map.get("HYBRID_VOTING_WINDOW"),
            read_db("hybrid_voting_window"),
            defaults.DEFAULT_HYBRID_VOTING_WINDOW,
        )
        hybrid_boost_amount = self._resolve_float(
            None,
            env_map.get("HYBRID_BOOST_AMOUNT"),
            read_db("hybrid_boost_amount"),
            defaults.DEFAULT_HYBRID_BOOST_AMOUNT,
        )
        hybrid_liveness_enabled = self._resolve_bool(
            None,
            env_map.get("HYBRID_LIVENESS_ENABLED"),
            read_db("hybrid_liveness_enabled"),
            defaults.DEFAULT_HYBRID_LIVENESS_ENABLED,
        )
        recognition_interval = self._resolve_int(
            None,
            env_map.get("RECOGNITION_INTERVAL"),
            read_db("recognition_interval"),
            defaults.DEFAULT_RECOGNITION_INTERVAL,
        )

        # --- Timezone (DB > env > default; no CLI) ---
        timezone = self._resolve_timezone(
            env_map.get("TIMEZONE"),
            read_db("timezone"),
            defaults.DEFAULT_TIMEZONE,
        )

        # --- Attendance UX (CLI > env > DB > default) ---
        attendance_freeze_seconds = self._resolve_int(
            None,
            env_map.get("ATTENDANCE_FREEZE_SECONDS"),
            read_db("attendance_freeze_seconds"),
            defaults.DEFAULT_ATTENDANCE_FREEZE_SECONDS,
        )
        attendance_freeze_sound_enabled = self._resolve_bool(
            None,
            env_map.get("ATTENDANCE_FREEZE_SOUND_ENABLED"),
            read_db("attendance_freeze_sound_enabled"),
            defaults.DEFAULT_ATTENDANCE_FREEZE_SOUND_ENABLED,
        )

        # --- Derived: liveness model path is None when disabled ---
        liveness_model_path: Path | None = None
        if antispoof_enabled:
            liveness_model_path = self._resolve_path(
                getattr(cli_obj, "liveness_model", None),
                env_map.get("FACE_ANTISPOOF_MODEL_PATH"),
                defaults.DEFAULT_LIVENESS_MODEL_PATH,
            )

        return SystemConfig(
            database_path=database_path,
            detection_model_path=detection_model_path,
            recognition_model_path=recognition_model_path,
            liveness_model_path=liveness_model_path,
            headpose_model_path=headpose_model_path,
            camera_index=camera_index,
            antispoof_enabled=antispoof_enabled,
            headpose_enabled=headpose_enabled,
            liveness_threshold=liveness_threshold,
            similarity_threshold=similarity_threshold,
            timezone=timezone,
            attendance_freeze_seconds=attendance_freeze_seconds,
            attendance_freeze_sound_enabled=attendance_freeze_sound_enabled,
            hybrid_voting_window=hybrid_voting_window,
            hybrid_boost_amount=hybrid_boost_amount,
            hybrid_liveness_enabled=hybrid_liveness_enabled,
            recognition_interval=recognition_interval,
        )

    def seed_db_from_env(
        self,
        settings: _SettingsServiceLike,
        env: Mapping[str, str] | None = None,
    ) -> None:
        """Write env values to the DB on first run only.

        Idempotent: if the DB already has a value for a key, it is left
        untouched.  This preserves the legacy ``_seed_threshold`` /
        ``_seed_setting`` semantics: env seeds DB on first run, then the
        admin can change values via the UI and the env var will not
        overwrite them.

        Skipped entirely in ``"init"`` mode because ``bootstrap.py`` must
        not call ``load_dotenv()``.

        Args:
            settings: Object exposing ``get`` / ``set`` (i.e., a
                :class:`~attendance_system.services.settings_service.SettingsService`).
            env: Environment mapping.  Pass ``None`` (the default) to
                consult :data:`os.environ` at call time, or an explicit
                mapping for hermetic / test use.  Pass ``{}`` to skip
                environment entirely.
        """
        if self._mode == "init":
            return
        env_map = os.environ if env is None else env
        for env_key, db_key, value_type in _SEEDABLE:
            if settings.get(db_key) is not None:
                continue  # DB owns this value; do not overwrite
            raw = env_map.get(env_key)
            if not raw or not raw.strip():
                continue  # no env value to seed
            settings.set(db_key, raw.strip(), value_type)

    # ------------------------------------------------------------------
    # Per-type resolvers (CLI > env > [DB] > default)
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_path(
        cli_value: object, env_value: str | None, default: Path
    ) -> Path:
        """CLI > env > default.  Empty strings count as missing."""
        if cli_value is not None and str(cli_value) != "":
            return Path(str(cli_value))
        if env_value and env_value.strip():
            return Path(env_value.strip())
        return default

    @staticmethod
    def _resolve_int(
        cli_value: object,
        env_value: str | None,
        db_value: str | None,
        default: int,
    ) -> int:
        """CLI > env > DB > default.  First parseable value wins."""
        if cli_value is not None and cli_value != "":
            try:
                return int(cli_value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass
        if env_value and env_value.strip():
            try:
                return int(env_value.strip())
            except ValueError:
                pass
        if db_value and db_value.strip():
            try:
                return int(db_value.strip())
            except ValueError:
                pass
        return default

    @staticmethod
    def _resolve_float(
        cli_value: object, env_value: str | None, db_value: str | None, default: float
    ) -> float:
        """CLI > env > DB > default.  First parseable value wins."""
        if cli_value is not None and cli_value != "":
            try:
                return float(cli_value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass
        if env_value and env_value.strip():
            try:
                return float(env_value.strip())
            except ValueError:
                pass
        if db_value and db_value.strip():
            try:
                return float(db_value.strip())
            except ValueError:
                pass
        return default

    @staticmethod
    def _resolve_timezone(
        env_value: str | None,
        db_value: str | None,
        default: str,
    ) -> str:
        """DB > env > default.  Validates against :class:`zoneinfo.ZoneInfo`.

        Unlike int/float/bool resolvers, timezone is a string that must be a
        valid IANA name.  Invalid values fall back to the default.
        """
        for candidate in (db_value, env_value):
            if candidate and candidate.strip():
                try:
                    ZoneInfo(candidate.strip())
                    return candidate.strip()
                except ZoneInfoNotFoundError:
                    pass
        return default

    @staticmethod
    def _resolve_bool(
        cli_value: object,
        env_value: str | None,
        db_value: str | None,
        default: bool,
    ) -> bool:
        """CLI > env > DB > default.  Truthy strings are the documented set.

        Empty string ``""`` for CLI is treated as missing (consistent with
        the int/float resolvers) so a future bool CLI flag with default
        ``""`` falls through to env/DB/default like the other types.
        """
        if cli_value is not None and cli_value != "":
            if isinstance(cli_value, bool):
                return cli_value
            if isinstance(cli_value, str):
                return cli_value.strip().lower() in _BOOL_TRUE
        if env_value and env_value.strip():
            lowered = env_value.strip().lower()
            if lowered in _BOOL_TRUE:
                return True
            if lowered in _BOOL_FALSE:
                return False
        if db_value and db_value.strip():
            lowered = db_value.strip().lower()
            if lowered in _BOOL_TRUE:
                return True
            if lowered in _BOOL_FALSE:
                return False
        return default


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------


def resolve_config(
    cli_args: argparse.Namespace | None = None,
    env: Mapping[str, str] | None = None,
    settings_service: _SettingsServiceLike | None = None,
    mode: ResolutionMode = "runtime",
) -> SystemConfig:
    """Build a :class:`SystemConfig` for the given inputs.

    Thin convenience wrapper around :class:`SettingsResolver` that wires
    up ``SettingsService.get`` as the ``db_reader``.  This is the
    function ``main.py`` and ``bootstrap.py`` should call.

    Args:
        cli_args: Parsed argparse ``Namespace`` (or ``None``).
        env: Environment mapping; defaults to :data:`os.environ`.
        settings_service: A ``SettingsService`` (or compatible) for DB
            reads.  Pass ``None`` to skip the DB layer (e.g., init mode
            where the schema does not exist yet, or unit tests).
        mode: ``"runtime"`` (default) or ``"init"``.

    Returns:
        Fully-resolved, immutable :class:`SystemConfig`.
    """
    resolver = SettingsResolver(mode=mode)
    db_reader = settings_service.get if settings_service is not None else None
    return resolver.resolve(cli=cli_args, env=env, db_reader=db_reader)
