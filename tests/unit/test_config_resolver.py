"""Unit tests for ``attendance_system.core.config``.

Covers the 10 behaviour tests listed in plan 0005 ("Testing" section):
resolution-order, env-seeding idempotency, init vs runtime modes, and
the immutability of the resolved :class:`SystemConfig`.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from attendance_system.core import defaults
from attendance_system.core.config import (
    SettingsResolver,
    SystemConfig,
    resolve_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_db() -> MagicMock:
    """Return a ``SettingsService``-like object that knows no keys."""
    svc = MagicMock()
    svc.get.return_value = None
    return svc


def _db_with(values: dict[str, str]) -> MagicMock:
    """Return a ``SettingsService``-like that returns the given values."""
    svc = MagicMock()
    svc.get.side_effect = lambda key: values.get(key)
    return svc


# ---------------------------------------------------------------------------
# Resolution order: CLI > env > DB > default
# ---------------------------------------------------------------------------


def test_cli_arg_overrides_env() -> None:
    """Both CLI and env set the same key — CLI wins."""
    args = argparse.Namespace(
        database_path=None,
        liveness_model=None,
        recognition_model=None,
        detector_model=None,
        headpose_model=None,
        camera_index=2,  # CLI sets camera=2
    )
    env = {"CAMERA_INDEX": "5"}  # env sets camera=5
    cfg = SettingsResolver().resolve(cli=args, env=env, db_reader=None)
    assert cfg.camera_index == 2  # CLI wins


def test_env_overrides_db() -> None:
    """Env set, DB has value — env wins (per plan 0005 precedence)."""
    env = {"FACE_ANTISPOOF_CONFIDENCE_THRESHOLD": "0.5"}
    db = _db_with({"liveness_threshold": "0.7"})
    cfg = SettingsResolver().resolve(env=env, db_reader=db.get)
    assert cfg.liveness_threshold == pytest.approx(0.5)  # env wins


def test_db_overrides_default() -> None:
    """DB set, no CLI, no env — DB wins."""
    db = _db_with({"liveness_threshold": "0.42"})
    cfg = SettingsResolver().resolve(env={}, db_reader=db.get)
    assert cfg.liveness_threshold == pytest.approx(0.42)


def test_default_used_when_nothing_set() -> None:
    """Nothing set, no DB, no env — defaults from ``defaults.py`` are used."""
    cfg = SettingsResolver().resolve(env={}, db_reader=None)
    assert cfg.liveness_threshold == defaults.DEFAULT_LIVENESS_THRESHOLD
    assert cfg.similarity_threshold == defaults.DEFAULT_SIMILARITY_THRESHOLD
    assert cfg.camera_index == defaults.DEFAULT_CAMERA_INDEX
    assert cfg.database_path == defaults.DEFAULT_DATABASE_PATH


# ---------------------------------------------------------------------------
# Seeding: env → DB on first run, never overwrites existing
# ---------------------------------------------------------------------------


def test_seeding_writes_env_to_db_on_first_run() -> None:
    """DB has no value, env has value — DB gets seeded with the env value."""
    settings = _empty_db()
    env = {"FACE_ANTISPOOF_CONFIDENCE_THRESHOLD": "0.5"}
    SettingsResolver().seed_db_from_env(env=env, settings=settings)
    # `set` should have been called for the liveness threshold.
    called = settings.set.call_args_list
    assert any(
        call.args[0] == "liveness_threshold" and call.args[1] == "0.5"
        for call in called
    ), f"Expected liveness_threshold seeding; got: {called}"


def test_seeding_does_not_overwrite_existing_db_value() -> None:
    """DB has a value, env has different value — DB is left untouched."""
    settings = _db_with({"liveness_threshold": "0.7"})
    env = {"FACE_ANTISPOOF_CONFIDENCE_THRESHOLD": "0.5"}
    SettingsResolver().seed_db_from_env(env=env, settings=settings)
    settings.set.assert_not_called()


# ---------------------------------------------------------------------------
# Mode behaviour: runtime vs init
# ---------------------------------------------------------------------------


def test_bootstrap_mode_skips_dotenv() -> None:
    """Init mode does not consult env (no ``load_dotenv()`` upstream)."""
    # When bootstrap.py is invoked, env may be polluted from the shell.
    # In init mode the resolver should still resolve the database path
    # from CLI args, but skip DB-seeding and threshold/UX resolution.
    env = {"FACE_ANTISPOOF_CONFIDENCE_THRESHOLD": "0.99"}  # would corrupt init
    args = argparse.Namespace(
        database_path="/tmp/explicit.db",
        liveness_model=None,
        recognition_model=None,
        detector_model=None,
        headpose_model=None,
        camera_index=None,
    )
    cfg = SettingsResolver(mode="init").resolve(cli=args, env=env, db_reader=None)
    assert cfg.database_path == Path("/tmp/explicit.db")
    # Init mode does not resolve thresholds from env — the default applies.
    assert cfg.liveness_threshold == defaults.DEFAULT_LIVENESS_THRESHOLD


def test_runtime_mode_consults_env() -> None:
    """Runtime mode reads env vars for thresholds (for env > DB precedence)."""
    env = {"FACE_ANTISPOOF_CONFIDENCE_THRESHOLD": "0.42"}
    cfg = SettingsResolver(mode="runtime").resolve(env=env, db_reader=None)
    assert cfg.liveness_threshold == pytest.approx(0.42)


def test_init_mode_skips_seeding() -> None:
    """Init mode is a no-op for seeding even if env has values."""
    settings = _empty_db()
    env = {
        "FACE_ANTISPOOF_CONFIDENCE_THRESHOLD": "0.5",
        "ATTENDANCE_FREEZE_SECONDS": "10",
    }
    SettingsResolver(mode="init").seed_db_from_env(env=env, settings=settings)
    settings.set.assert_not_called()


# ---------------------------------------------------------------------------
# SystemConfig immutability
# ---------------------------------------------------------------------------


def test_frozen_config_cannot_be_mutated() -> None:
    """``SystemConfig`` is ``frozen=True`` — assignments raise ``FrozenInstanceError``."""
    cfg = SettingsResolver().resolve(env={}, db_reader=None)
    with pytest.raises((AttributeError, Exception)):
        # ``FrozenInstanceError`` is a subclass of ``AttributeError`` in
        # the stdlib; ``Exception`` covers dataclasses' error class too.
        cfg.liveness_threshold = 0.99  # type: ignore[misc]


def test_config_has_all_required_fields() -> None:
    """Every documented tunable has a field; missing one is a startup error."""
    cfg = SettingsResolver().resolve(env={}, db_reader=None)
    required_fields = (
        "database_path",
        "detection_model_path",
        "recognition_model_path",
        "liveness_model_path",
        "headpose_model_path",
        "camera_index",
        "antispoof_enabled",
        "headpose_enabled",
        "liveness_threshold",
        "similarity_threshold",
        "attendance_freeze_seconds",
        "attendance_freeze_sound_enabled",
    )
    for field_name in required_fields:
        assert hasattr(cfg, field_name), f"SystemConfig missing field: {field_name}"


# ---------------------------------------------------------------------------
# Bonus: module-level resolve_config() factory
# ---------------------------------------------------------------------------


def test_resolve_config_factory_wires_settings_service() -> None:
    """``resolve_config`` reads DB via the supplied ``SettingsService``."""
    settings = _db_with({"liveness_threshold": "0.55"})
    cfg = resolve_config(
        cli_args=argparse.Namespace(
            database_path=None, liveness_model=None, recognition_model=None,
            detector_model=None, headpose_model=None, camera_index=None,
        ),
        env={},
        settings_service=settings,
        mode="runtime",
    )
    assert cfg.liveness_threshold == pytest.approx(0.55)
    # SettingsService.get was called with the liveness key at some point.
    called_keys = [call.args[0] for call in settings.get.call_args_list]
    assert "liveness_threshold" in called_keys
