"""
Entry point for the Face Attendance application.

Bootstraps the database, loads AI models (YuNet detector, SFace recognizer,
MiniFASNet liveness), and launches the PyQt5 main window.

Configuration priority: CLI arguments > environment variables > database
> defaults.  Resolution is centralised in
:class:`attendance_system.core.config.SettingsResolver`; this module
only handles the bootstrap orchestration.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# IMPORTANT: onnxruntime must be imported BEFORE PyQt5.
# On Windows, both libraries load conflicting native DLLs. Loading onnxruntime
# first ensures its DLLs are resolved correctly in the process address space.
import onnxruntime  # noqa: F401

from dotenv import load_dotenv
from PyQt5.QtWidgets import QApplication, QMessageBox

from attendance_system.core.bootstrap import initialize_storage
from attendance_system.core.config import (
    SettingsResolver,
    resolve_config,
)
from attendance_system.core.db import Database, DatabaseConfig
from attendance_system.repositories.admin_repository import AdminRepository
from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker
from attendance_system.services.head_pose import HeadPoseEstimator
from attendance_system.services.attendance_service import AttendanceService
from attendance_system.services.authentication_service import AuthenticationService
from attendance_system.services.settings_service import SettingsService
from attendance_system.utils.time_utils import set_timezone_config
from attendance_system.ui.main_window import MainWindow


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    All defaults are ``None`` so that resolution happens *after*
    ``load_dotenv()`` is called and the
    :class:`~attendance_system.core.config.SettingsResolver` runs — see
    :func:`main`.
    """
    parser = argparse.ArgumentParser(
        prog="attendance-app",
        description="Launch the face attendance system.",
    )
    parser.add_argument("--database-path", default=None,
                        help="Path to the SQLite database file.")
    parser.add_argument("--liveness-model", default=None,
                        help="Path to MiniFASNet ONNX model.")
    parser.add_argument("--recognition-model", default=None,
                        help="Path to SFace ONNX model.")
    parser.add_argument("--detector-model", default=None,
                        help="Path to YuNet ONNX model.")
    parser.add_argument("--headpose-model", default=None,
                        help="Path to head-pose ONNX model.")
    parser.add_argument("--camera-index", type=int, default=None,
                        help="OpenCV camera device index (default: 0).")
    return parser


# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------


def _validate_model(path: Path, label: str) -> str | None:
    """Return an error message if *path* does not exist, else ``None``."""
    if not path.exists():
        return f"{label} model not found:\n{path}"
    return None


def main(argv: list[str] | None = None) -> int:
    """Launch the attendance application. Returns a process exit code."""

    # --- Phase 1: Environment & CLI -------------------------------------------
    load_dotenv()  # must run before the resolver reads env
    args = build_parser().parse_args(argv)

    # --- Phase 2: Resolve configuration (CLI > env > DB > default) -------------
    # ``resolve_config`` is called twice:
    #   (a) now, with ``db_reader=None`` because the schema does not exist yet
    #   (b) after DB init + seeding, to fold the seeded values in
    # The first pass gives us ``database_path`` (needed to init the schema);
    # the second pass yields the final, DB-aware ``SystemConfig``.
    resolver = SettingsResolver(mode="runtime")
    provisional = resolver.resolve(cli=args, env=None, db_reader=None)
    set_timezone_config(os.getenv("TIMEZONE"))
    # NOTE: set_timezone_config takes the env value directly — it predates
    # this refactor and is not a tunable in SystemConfig.

    # --- Phase 3: Bootstrap database ------------------------------------------
    try:
        initialize_storage(provisional.database_path)
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Database Initialization Failed",
            f"A database migration error occurred:\n\n{exc}\n\nThe application cannot start.",
        )
        return 1

    # --- Phase 4: Start Qt application ----------------------------------------
    # Pass consistent argv so that test harnesses work correctly.
    qt_argv = sys.argv if argv is None else [sys.argv[0], *list(argv)]
    app = QApplication(qt_argv)

    # --- Phase 5: Wire up services & launch UI --------------------------------
    db = Database(DatabaseConfig(path=provisional.database_path))
    settings_service = SettingsService(db)
    resolver.seed_db_from_env(env=None, settings=settings_service)

    # Now the DB is seeded — resolve the final SystemConfig that includes DB.
    config = resolve_config(
        cli_args=args,
        env=None,
        settings_service=settings_service,
        mode="runtime",
    )

    # Validate all required model files before proceeding.
    model_checks = [
        (config.recognition_model_path, "Recognition (SFace)"),
        (config.detection_model_path, "Detector (YuNet)"),
    ]
    if config.antispoof_enabled and config.liveness_model_path is not None:
        model_checks.append((config.liveness_model_path, "Liveness (MiniFASNet)"))

    for path, label in model_checks:
        error = _validate_model(path, label)
        if error:
            QMessageBox.critical(None, "Model Not Found", error)
            return 1

    # Optional: head-pose estimator (falls back to legacy mode on error).
    head_pose_estimator: HeadPoseEstimator | None = None
    head_pose_warning: str | None = None
    if config.headpose_enabled:
        if not config.headpose_model_path.exists():
            head_pose_warning = (
                f"Head pose model not found:\n{config.headpose_model_path}\n\n"
                "Enrollment will continue in legacy mode."
            )
        else:
            try:
                head_pose_estimator = HeadPoseEstimator(config.headpose_model_path)
            except Exception as exc:  # pragma: no cover - startup fallback path
                head_pose_warning = (
                    "Head pose guidance could not be initialized.\n\n"
                    f"{exc}\n\n"
                    "Enrollment will continue in legacy mode."
                )

    # Build services
    attendance_service = AttendanceService(db)
    authentication_service = AuthenticationService(AdminRepository(db))
    liveness_checker = LivenessChecker(config.liveness_model_path)
    face_recognizer = FaceRecognizer(db, config.recognition_model_path)

    if head_pose_warning is not None:
        QMessageBox.warning(None, "Head Pose Guidance Disabled", head_pose_warning)

    # Show the main window
    window = MainWindow(
        attendance_service=attendance_service,
        settings_service=settings_service,
        authentication_service=authentication_service,
        liveness_checker=liveness_checker,
        face_recognizer=face_recognizer,
        head_pose_estimator=head_pose_estimator,
        database=db,
        config=config,
    )
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
