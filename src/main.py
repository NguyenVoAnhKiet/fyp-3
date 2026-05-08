"""
Entry point for the Face Attendance application.

Bootstraps the database, loads AI models (YuNet detector, SFace recognizer,
MiniFASNet liveness), and launches the PyQt5 main window.

Configuration priority: CLI arguments > environment variables > defaults.
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
from attendance_system.core.db import Database, DatabaseConfig
from attendance_system.repositories.admin_repository import AdminRepository
from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker
from attendance_system.services.attendance_service import AttendanceService
from attendance_system.services.authentication_service import AuthenticationService
from attendance_system.services.settings_service import SettingsService
from attendance_system.ui.main_window import MainWindow

# ---------------------------------------------------------------------------
# Default paths — used when neither CLI args nor env vars are provided
# ---------------------------------------------------------------------------
DEFAULT_DATABASE_PATH = Path("attendance.db")
DEFAULT_LIVENESS_MODEL = Path("models/anti_spoof/best_model_quantized.onnx")
DEFAULT_RECOGNITION_MODEL = Path("models/face_recognition/face_recognition_sface_2021dec.onnx")
DEFAULT_DETECTOR_MODEL = Path("models/face_detection/face_detection_yunet_2023mar.onnx")


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    All defaults are ``None`` so that resolution happens *after*
    ``load_dotenv()`` is called — see :func:`main`.
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
    parser.add_argument("--camera-index", type=int, default=None,
                        help="OpenCV camera device index (default: 0).")
    return parser


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _resolve_path(cli_value: str | None, env_key: str, default: Path) -> Path:
    """Return the first non-empty value from CLI arg, env var, or default."""
    return Path(cli_value or os.getenv(env_key) or str(default))


def _resolve_camera_index(cli_value: int | None) -> int:
    """Return camera index from CLI arg, env var, or 0.

    Handles the edge case where ``CAMERA_INDEX=`` (empty string) is set
    in ``.env``, which would crash ``int()`` without this guard.
    """
    if cli_value is not None:
        return cli_value

    raw = os.getenv("CAMERA_INDEX")
    if raw and raw.strip():
        return int(raw)

    return 0


def _validate_model(path: Path, label: str) -> str | None:
    """Return an error message if *path* does not exist, else ``None``."""
    if not path.exists():
        return f"{label} model not found:\n{path}"
    return None


def _seed_threshold(
    settings: SettingsService, env_key: str, setting_key: str,
) -> None:
    """Write an env-var value into the DB settings table on first run only.

    Once a value exists in the DB it is never overwritten, allowing the
    admin to change thresholds at runtime without the env var resetting them.
    """
    value = os.getenv(env_key)
    if value and settings.get(setting_key) is None:
        settings.set(setting_key, value, "float")


# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Launch the attendance application. Returns a process exit code."""

    # --- Phase 1: Environment & CLI -------------------------------------------
    load_dotenv()  # must run before any os.getenv() call
    args = build_parser().parse_args(argv)

    # --- Phase 2: Resolve configuration (CLI > env > default) -----------------
    database_path = _resolve_path(
        args.database_path, "DATABASE_PATH", DEFAULT_DATABASE_PATH,
    )
    recognition_model_path = _resolve_path(
        args.recognition_model, "FACE_RECOGNITION_MODEL_PATH", DEFAULT_RECOGNITION_MODEL,
    )
    detector_model_path = _resolve_path(
        args.detector_model, "FACE_DETECTOR_MODEL_PATH", DEFAULT_DETECTOR_MODEL,
    )
    camera_index = _resolve_camera_index(args.camera_index)

    # Liveness model is optional — disabled when FACE_ANTISPOOF_ENABLED=false
    antispoof_enabled = (
        os.getenv("FACE_ANTISPOOF_ENABLED", "true").strip().lower() == "true"
    )
    liveness_model_path: Path | None = None
    if antispoof_enabled:
        liveness_model_path = _resolve_path(
            args.liveness_model, "FACE_ANTISPOOF_MODEL_PATH", DEFAULT_LIVENESS_MODEL,
        )

    # --- Phase 3: Bootstrap database ------------------------------------------
    initialize_storage(database_path)

    # --- Phase 4: Start Qt application ----------------------------------------
    # Pass consistent argv so that test harnesses work correctly.
    qt_argv = sys.argv if argv is None else [sys.argv[0], *list(argv)]
    app = QApplication(qt_argv)

    # Validate all required model files before proceeding
    model_checks = [
        (recognition_model_path, "Recognition (SFace)"),
        (detector_model_path, "Detector (YuNet)"),
    ]
    if antispoof_enabled and liveness_model_path is not None:
        model_checks.append((liveness_model_path, "Liveness (MiniFASNet)"))

    for path, label in model_checks:
        error = _validate_model(path, label)
        if error:
            QMessageBox.critical(None, "Model Not Found", error)
            return 1

    # --- Phase 5: Wire up services & launch UI --------------------------------
    db = Database(DatabaseConfig(path=database_path))
    attendance_service = AttendanceService(db)
    settings_service = SettingsService(db)
    authentication_service = AuthenticationService(AdminRepository(db))

    # Seed default thresholds from .env on first run (DB values take precedence)
    _seed_threshold(settings_service, "FACE_ANTISPOOF_CONFIDENCE_THRESHOLD", "liveness_threshold")
    _seed_threshold(settings_service, "FACE_SIMILARITY_THRESHOLD", "similarity_threshold")

    # Seed camera index so the Settings UI shows the correct startup value
    if settings_service.get("camera_index") is None:
        settings_service.set("camera_index", str(camera_index), "int")

    # Build AI components
    liveness_checker = LivenessChecker(liveness_model_path)
    face_recognizer = FaceRecognizer(db, recognition_model_path)

    # Show the main window
    window = MainWindow(
        attendance_service=attendance_service,
        settings_service=settings_service,
        authentication_service=authentication_service,
        liveness_checker=liveness_checker,
        face_recognizer=face_recognizer,
        camera_index=camera_index,
        detector_model_path=detector_model_path,
    )
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
