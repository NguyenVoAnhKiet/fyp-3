"""Unit tests for ``attendance_system.core.config``.

Covers resolution-order, defaults→DB seeding idempotency, init vs runtime
modes, and the immutability of the resolved :class:`SystemConfig`.
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

# --- Non-DB settings (paths, camera, feature flags): CLI > env > default ---


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


def test_db_wins_for_seedable_keys() -> None:
    """For seedable keys, DB value wins over env (env is not consulted)."""
    env = {"FACE_ANTISPOOF_CONFIDENCE_THRESHOLD": "0.5"}
    db = _db_with({"liveness_threshold": "0.7"})
    cfg = SettingsResolver().resolve(env=env, db_reader=db.get)
    assert cfg.liveness_threshold == pytest.approx(0.7)  # DB wins


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


def test_resolve_uses_db_for_seedable_keys() -> None:
    """DB value wins over defaults.py for seedable keys."""
    db = _db_with({"liveness_threshold": "0.42"})
    cfg = SettingsResolver().resolve(env={}, db_reader=db.get)
    assert cfg.liveness_threshold == pytest.approx(0.42)


def test_resolve_falls_back_to_defaults_py() -> None:
    """DB empty → defaults.py value used."""
    cfg = SettingsResolver().resolve(env={}, db_reader=None)
    assert cfg.liveness_threshold == defaults.DEFAULT_LIVENESS_THRESHOLD


def test_resolve_ignores_env_for_seedable_keys() -> None:
    """Env var set but ignored for seedable keys."""
    env = {"FACE_ANTISPOOF_CONFIDENCE_THRESHOLD": "0.99"}
    cfg = SettingsResolver().resolve(env=env, db_reader=None)
    assert cfg.liveness_threshold == defaults.DEFAULT_LIVENESS_THRESHOLD


def test_non_db_settings_still_use_env_override() -> None:
    """Paths, camera, feature flags still use CLI > env > default."""
    env = {"CAMERA_INDEX": "5"}
    cfg = SettingsResolver().resolve(env=env, db_reader=None)
    assert cfg.camera_index == 5


# ---------------------------------------------------------------------------
# Seeding: defaults.py → DB on first run, never overwrites existing
# ---------------------------------------------------------------------------


def test_all_seed_keys_have_defaults_constant() -> None:
    """Every ``_SEED_SETTINGS`` key has a matching ``DEFAULT_*`` in ``defaults.py``."""
    from attendance_system.core.config import _SEED_SETTINGS

    for db_key in _SEED_SETTINGS:
        const_name = f"DEFAULT_{db_key.upper()}"
        assert hasattr(defaults, const_name), f"Missing {const_name} for {db_key}"


def test_seed_db_from_defaults_writes_when_key_missing() -> None:
    """DB has no value — all 9 seed keys are written from defaults.py."""
    settings = _empty_db()
    SettingsResolver().seed_db_from_defaults(settings=settings)
    assert settings.set.called
    called_keys = {call.args[0] for call in settings.set.call_args_list}
    expected_keys = {
        "timezone",
        "liveness_threshold",
        "similarity_threshold",
        "attendance_freeze_seconds",
        "attendance_freeze_sound_enabled",
        "hybrid_voting_window",
        "hybrid_boost_amount",
        "hybrid_liveness_enabled",
        "recognition_interval",
    }
    assert called_keys == expected_keys, (
        f"Expected {expected_keys}, got {called_keys}"
    )


def test_seed_db_from_defaults_skips_when_key_exists() -> None:
    """All DB keys have values — seeding is skipped entirely."""
    settings = _db_with({
        "liveness_threshold": "0.5",
        "similarity_threshold": "0.6",
        "attendance_freeze_seconds": "4",
        "attendance_freeze_sound_enabled": "false",
        "hybrid_voting_window": "5",
        "hybrid_boost_amount": "0.1",
        "hybrid_liveness_enabled": "false",
        "recognition_interval": "5",
        "timezone": "Asia/Ho_Chi_Minh",
    })
    SettingsResolver().seed_db_from_defaults(settings=settings)
    settings.set.assert_not_called()


def test_seed_db_from_defaults_converts_db_types_to_strings() -> None:
    """``defaults.py`` float/bool/int values are stringified for DB storage.
    
    Uses real defaults from :mod:`attendance_system.core.defaults`.
    """
    settings = _empty_db()
    SettingsResolver().seed_db_from_defaults(settings=settings)
    called = {call.args[0]: call.args[1] for call in settings.set.call_args_list}
    assert called["liveness_threshold"] == "0.5"
    assert called["hybrid_liveness_enabled"] == (
        "true" if defaults.DEFAULT_HYBRID_LIVENESS_ENABLED else "false"
    )
    assert called["hybrid_voting_window"] == "5"


def test_seed_db_from_defaults_valid_zero_and_false_are_valid() -> None:
    """Bool seed values are valid and stringified instead of skipped."""
    settings = _empty_db()
    SettingsResolver().seed_db_from_defaults(settings=settings)
    called = {call.args[0]: call.args[1] for call in settings.set.call_args_list}
    assert called["hybrid_liveness_enabled"] == (
        "true" if defaults.DEFAULT_HYBRID_LIVENESS_ENABLED else "false"
    )


# ---------------------------------------------------------------------------
# Mode behaviour: runtime vs init
# ---------------------------------------------------------------------------


def test_bootstrap_mode_keeps_non_admin_settings_hermetic() -> None:
    """Init mode ignores non-admin env values passed through ``env``."""
    # When bootstrap.py is invoked, env may be polluted from the shell.
    # In init mode the resolver should still resolve the database path
    # from CLI args, but skip threshold/UX resolution.
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


def test_runtime_mode_consults_env_for_non_db_settings() -> None:
    """Runtime mode reads env vars for non-DB settings (camera index, paths)."""
    env = {"CAMERA_INDEX": "5"}
    cfg = SettingsResolver(mode="runtime").resolve(env=env, db_reader=None)
    assert cfg.camera_index == 5


def test_admin_credentials_are_resolved_from_process_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admin seed credentials come from process env after dotenv loading."""
    monkeypatch.setenv("ADMIN_USERNAME", "root")
    monkeypatch.setenv("ADMIN_PASSWORD", "Root@1234")

    cfg = SettingsResolver().resolve(env={}, db_reader=None)

    assert cfg.admin_username == "root"
    assert cfg.admin_password == "Root@1234"


def test_admin_credentials_have_no_hardcoded_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing admin env values stay empty so storage init can fail fast."""
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

    cfg = SettingsResolver().resolve(env={}, db_reader=None)

    assert cfg.admin_username == ""
    assert cfg.admin_password == ""


def test_empty_admin_env_values_do_not_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank env values remain blank; no default admin is substituted."""
    monkeypatch.setenv("ADMIN_USERNAME", "")
    monkeypatch.setenv("ADMIN_PASSWORD", "")

    cfg = SettingsResolver().resolve(env={}, db_reader=None)

    assert cfg.admin_username == ""
    assert cfg.admin_password == ""


def test_init_mode_skips_defaults_seeding() -> None:
    """Init mode is a no-op for seeding (bootstrap does not seed DB)."""
    settings = _empty_db()
    SettingsResolver(mode="init").seed_db_from_defaults(settings=settings)
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
        "hybrid_voting_window",
        "hybrid_boost_amount",
        "hybrid_liveness_enabled",
        "recognition_interval",
        "timezone",
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
            database_path=None,
            liveness_model=None,
            recognition_model=None,
            detector_model=None,
            headpose_model=None,
            camera_index=None,
        ),
        env={},
        settings_service=settings,
        mode="runtime",
    )
    assert cfg.liveness_threshold == pytest.approx(0.55)
    # SettingsService.get was called with the liveness key at some point.
    called_keys = [call.args[0] for call in settings.get.call_args_list]
    assert "liveness_threshold" in called_keys
