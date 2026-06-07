# Project Status Summary — Face Attendance System

**Last Updated:** June 8, 2026  
**Project Phase:** Phase 4 (Threshold Tuning) — Implementation Complete, Validation Pending

---

## Executive Summary

A **production-ready Python desktop application** for automated face-based attendance with anti-spoofing detection. The system is **fully implemented** with all core features working. Current focus is on **threshold tuning** for optimal liveness detection accuracy.

### Key Metrics
- **Lines of Code:** ~3,500 (src/)
- **Test Coverage:** 280 tests (250 unit + 30 integration)
- **Test Pass Rate:** 100% ✅
- **Dependencies:** 7 core (PyQt5, ONNX Runtime, OpenCV, bcrypt, etc.)
- **Python Version:** 3.11+
- **Database:** SQLite3 with WAL journaling
- **UI Framework:** PyQt5 (desktop)
- **AI Models:** 4 ONNX models (face detection, recognition, liveness, head-pose)

---

## Architecture Overview

### Tech Stack
| Layer | Technology |
|-------|-----------|
| **UI** | PyQt5 (desktop) |
| **Backend** | Python 3.11+ |
| **Database** | SQLite3 (WAL mode) |
| **AI/ML** | ONNX Runtime (4 models) |
| **Security** | bcrypt (passwords), optional Fernet (embeddings) |
| **Deployment** | Offline, single-process desktop app |

### Core Components
1. **Face Detection** — YuNet (2023mar) ONNX model
2. **Face Recognition** — SFace (2021dec) ONNX model + embedding matching
3. **Liveness Detection (Anti-Spoofing)** — MiniFASNet V2 SE (INT8, 600 KB)
4. **Head Pose Estimation** — MobileNetV2 (optional, for enrollment)
5. **Temporal Smoothing** — LivenessTracker (EMA + hysteresis + IoU tracking)
6. **Database** — SQLite3 with schema migrations
7. **UI** — 11 PyQt5 widgets (login, admin dashboard, attendance view, enrollment, settings, history)

### Startup Sequence
```
load_dotenv() 
  → SettingsResolver.resolve() [CLI > env > DB > default]
  → set_timezone_config()
  → initialize_storage()
  → SettingsResolver.seed_db_from_env() [idempotent]
  → validate ONNX models
  → wire services
  → launch MainWindow
```

---

## Current Implementation Status

### ✅ Completed Features

#### Core Attendance System
- [x] Face detection from webcam (real-time)
- [x] Face recognition (embedding-based matching)
- [x] Liveness detection (anti-spoofing with MiniFASNet)
- [x] Attendance recording (with session management)
- [x] User management (CRUD)
- [x] Admin authentication (bcrypt)

#### Anti-Spoofing (Liveness Detection)
- [x] MiniFASNet V2 SE model integration (INT8, 600 KB)
- [x] Temporal smoothing (EMA α=0.4 + hysteresis T_HIGH=0.65, T_LOW=0.45)
- [x] IoU-based face tracking across frames
- [x] Configurable threshold (default 0.3, via env or Admin UI)
- [x] Circuit-breaker pattern (30-failure limit per ADR-0001)

#### Preprocessing Pipeline
- [x] FacePreprocessor (composable, model-agnostic)
- [x] PreprocessingConfig (frozen per-model configs)
- [x] Crop scaling (2.7 for liveness, 1.5 for head-pose)
- [x] Letterbox resizing (aspect-ratio preserving)
- [x] CLAHE toggle (OFF by default, per plan 0007)

#### Enrollment System
- [x] Face enrollment (capture + embedding storage)
- [x] Head-pose validation (optional, for enrollment quality)
- [x] Encrypted embedding storage (optional Fernet)
- [x] Caching face reference repository (with invalidation)

#### UI/UX
- [x] Login screen (admin/user modes)
- [x] Admin dashboard (user management, settings, history)
- [x] Attendance view (real-time camera, recognition feedback)
- [x] Enrollment widget (guided face capture)
- [x] Settings panel (threshold, timezone, model paths)
- [x] Attendance history (filterable table)
- [x] Timezone support (13 IANA zones, UTC storage)

#### Database
- [x] Schema with migrations
- [x] 7 repository classes (user, admin, session, attendance, recognition_event, system_setting, face_reference)
- [x] Caching wrapper for face references
- [x] Audit trail (recognition_events table)
- [x] Session management (open/close/status)

#### Testing
- [x] 22 unit test files (mocked DB)
- [x] 10 integration test files (real DB)
- [x] 280 total tests, 100% pass rate
- [x] conftest.py with ONNX-first import order

#### Documentation
- [x] CONTEXT.md (domain glossary)
- [x] AGENTS.md (wiring + gotchas)
- [x] CLAUDE.md (behavioral guidelines)
- [x] architecture.md (layers, threading, startup)
- [x] ai-pipeline.md (model details, preprocessing)
- [x] database.md (schema, ERD, access patterns)
- [x] modules.md (module-by-module reference)
- [x] 8 completed feature plans (archived)
- [x] 1 ADR (circuit-breaker pattern)

---

## Current Issues & Limitations

### Known Issues (Phase 4 Findings)

| Issue | Status | Impact | Notes |
|-------|--------|--------|-------|
| **Flicker** | ✅ Resolved | Low | Temporal smoothing reduced flicker from continuous to 2-3s intervals |
| **Fake Images Pass** | ⚠️ Pending | Medium | 5% of fake images pass at threshold 0.3; needs proper tuning |
| **Poor Lighting** | ⚠️ Model Limitation | Medium | 95% spoof rejection in poor light (MiniFASNet limitation, not preprocessing) |
| **Threshold Instability** | ⚠️ Pending | Medium | Threshold 0.5 was near decision boundary; moved to 0.3 as quick fix |

### Model Limitations
- **MiniFASNet:** 2D texture classifier (not 3D liveness detection)
- **Best Performance:** Well-lit, frontal faces, angle < 30°
- **Quantization:** INT8 shows no accuracy drop on benchmark
- **Training Data:** CelebA-Spoof (may have domain shift with real-world data)

### Known Gotchas (from AGENTS.md)
- `onnxruntime` must import BEFORE `PyQt5` (Windows DLL conflict)
- `CAMERA_INDEX=` (empty string) defaults to 0
- `_crop_face` scale: 2.7 for liveness, 1.5 for head-pose
- `_COOLDOWN_SECONDS = 3.0` per-user cooldown (in-memory, resets on thread restart)
- `_AI_FRAME_SKIP = 3` (full pipeline every 3rd frame, ~10 Hz at 30 fps)
- Enrollment frame is horizontally flipped; attendance frame is not
- `CachingFaceReferenceRepository` owns cache; invalidation enforced by wrapper

---

## Phase 4: Threshold Tuning (Current)

### What Was Done
1. ✅ Implemented temporal smoothing (LivenessTracker with EMA + hysteresis)
2. ✅ Reduced threshold from 0.5 → 0.3 (quick fix)
3. ✅ Created threshold tuning script (`scripts/tune_liveness_threshold.py`)
4. ✅ Updated all config files (.env.example, UI defaults)
5. ✅ All 280 tests passing

### Results at Threshold 0.3
- **Good lighting:** Flicker improved (2-3s intervals) ✅
- **Poor lighting:** 95% spoof rejection (model limitation) ⚠️
- **Fake images:** 95% spoof rejection (5% pass rate, too high) ⚠️

### Next Steps (Pending User Action)
1. **Collect validation data:**
   - Real face videos (15-20s, multiple lighting: good/poor/backlit)
   - Fake face videos (15-20s, printed photo or phone screen)
2. **Run threshold tuning script:**
   ```bash
   python scripts/tune_liveness_threshold.py \
     --real-video real_face.mp4 \
     --fake-video fake_face.mp4 \
     --output-dir ./threshold_tuning_results
   ```
3. **Review histogram + recommended threshold**
4. **Update threshold to optimal value** (target: FAR < 1%, FRR < 5%)
5. **Test with real attendance session**

---

## File Structure

### Source Code (`src/`)
```
src/
├── main.py                                    # GUI entry point
└── attendance_system/
    ├── core/                                  # Database, config, bootstrap
    │   ├── config.py                          # SettingsResolver + SystemConfig
    │   ├── db.py                              # SQLite connection
    │   ├── schema.py                          # DDL + migrations
    │   ├── bootstrap.py                       # CLI entry point
    │   ├── storage_manager.py                 # Orchestrator
    │   ├── defaults.py                        # Default values
    │   └── liveness_tracker.py                # Backward-compat re-export
    ├── models/                                # Entity dataclasses
    │   └── entities.py
    ├── repositories/                          # Data access layer (7 repos)
    │   ├── base_repository.py
    │   ├── user_repository.py
    │   ├── admin_repository.py
    │   ├── session_repository.py
    │   ├── attendance_repository.py
    │   ├── recognition_event_repository.py
    │   ├── system_setting_repository.py
    │   ├── face_reference_repository.py
    │   └── caching_face_reference_repository.py
    ├── services/                              # Business logic (8 services)
    │   ├── ai_pipeline.py                     # Orchestrates liveness + recognition
    │   ├── pipeline_result.py                 # Structured AI output
    │   ├── liveness_tracker.py                # EMA + hysteresis + IoU tracking
    │   ├── face_preprocessor.py               # Composable preprocessing
    │   ├── preprocessing_configs.py           # Per-model configs
    │   ├── head_pose.py                       # Head-pose estimation
    │   ├── enrollment_service.py              # Enrollment logic
    │   ├── attendance_service.py              # Attendance business logic
    │   ├── authentication_service.py          # Login auth
    │   ├── settings_service.py                # Settings management
    │   └── exceptions.py                      # Custom exceptions
    ├── ui/                                    # PyQt5 widgets (11 modules)
    │   ├── main_window.py                     # App shell
    │   ├── login_widget.py                    # Login screen
    │   ├── admin_dashboard_view.py            # Admin dashboard
    │   ├── user_mode_view.py                  # Attendance camera view
    │   ├── enrollment_widget.py               # Face enrollment
    │   ├── settings_widget.py                 # Admin settings
    │   ├── attendance_history_widget.py       # History table
    │   ├── user_management_widget.py          # User management
    │   ├── camera_worker_base.py              # Base classes (CameraThreadBase, AIWorkerBase)
    │   ├── camera_thread.py                   # Attendance camera thread
    │   ├── enrollment_camera_thread.py        # Enrollment camera thread
    │   ├── enrollment_ai_worker.py            # Enrollment AI worker
    │   ├── styles.py                          # Qt stylesheets
    │   └── constants.py                       # UI constants
    └── utils/                                 # Utilities (2 modules)
        ├── time_utils.py                      # Timezone conversion + signals
        └── face_utils.py                      # Face crop/draw helpers
```

### Tests (`tests/`)
```
tests/
├── conftest.py                                # Shared fixtures
├── unit/                                      # 22 unit test files
│   ├── test_ai_pipeline.py
│   ├── test_ai_pipeline_orchestrator.py
│   ├── test_attendance_audit.py
│   ├── test_attendance_callbacks.py
│   ├── test_attendance_history_service.py
│   ├── test_attendance_service.py
│   ├── test_authentication.py
│   ├── test_caching_face_reference_repository.py
│   ├── test_camera_thread.py
│   ├── test_camera_thread_pause.py
│   ├── test_camera_worker_base.py
│   ├── test_config_resolver.py
│   ├── test_enrollment_ai_worker.py
│   ├── test_enrollment_and_settings_unit.py
│   ├── test_face_preprocessor.py
│   ├── test_head_pose.py
│   ├── test_liveness_tracker.py
│   ├── test_pipeline_result.py
│   ├── test_recognition_event_repository.py
│   ├── test_storage_repositories.py
│   ├── test_time_utils.py
│   └── test_user_mode_freeze.py
└── integration/                               # 10 integration test files
    ├── test_attendance_audit_legacy.py
    ├── test_attendance_history.py
    ├── test_bootstrap_entry_point.py
    ├── test_database_init.py
    ├── test_face_reference_cache_invalidation.py
    ├── test_head_pose_enrollment.py
    ├── test_offline_behavior.py
    ├── test_performance.py
    ├── test_settings_and_enrollment_integration.py
    └── test_storage_bootstrap.py
```

### Documentation (`docs/`)
```
docs/
├── README.md                                  # Doc index
├── architecture.md                            # System architecture
├── ai-pipeline.md                             # AI model details
├── database.md                                # Schema + ERD
├── modules.md                                 # Module reference
├── adr/
│   └── 0001-onnx-circuit-breaker.md          # Circuit-breaker ADR
├── agents/
│   ├── domain.md                              # Agent domain conventions
│   ├── issue-tracker.md                       # Issue tracking
│   └── triage-labels.md                       # Triage labels
├── plans/
│   ├── README.md                              # Plan conventions
│   └── archive/                               # 8 completed plans
└── srs/
    ├── fyp.md                                 # Original SRS (template)
    └── srs_2.md                               # Software Requirements Spec (Vietnamese)
```

### Configuration
```
.env                                           # Active config
.env.example                                   # Template (70 vars, 4 sections)
pyproject.toml                                 # Build config + entry points
AGENTS.md                                      # Agent wiring + gotchas
CLAUDE.md                                      # Behavioral guidelines
CONTEXT.md                                     # Domain glossary
codemap.md                                     # Root codemap
```

---

## Entry Points

### CLI Commands
```bash
# GUI application
attendance-app

# Database initialization
attendance-storage-init
attendance-storage-init --database-path <path>
```

### Development Commands
```bash
# Install
pip install -e .
pip install pytest

# Lint
ruff check src/

# Test
pytest tests/
pytest tests/unit/ -v
pytest tests/integration/ -v

# Run (dev)
PYTHONPATH=src python src/main.py
$env:PYTHONPATH='src'; python src/main.py  # Windows
```

---

## Configuration

### Environment Variables (70 total, 4 sections)

#### Security & Encryption
- `FACE_EMBEDDING_FERNET_KEY` — Optional encryption key for embeddings
- `ADMIN_USERNAME` — Admin login username
- `ADMIN_PASSWORD` — Admin login password

#### Database & Hardware
- `DATABASE_PATH` — SQLite database file path
- `TIMEZONE` — IANA timezone (default: `Asia/Ho_Chi_Minh`)
- `CAMERA_INDEX` — Webcam index (default: 0)

#### AI Pipeline Models
- `FACE_DETECTION_MODEL_PATH` — YuNet model path
- `FACE_RECOGNITION_MODEL_PATH` — SFace model path
- `FACE_ANTISPOOF_MODEL_PATH` — MiniFASNet model path
- `FACE_HEADPOSE_MODEL_PATH` — MobileNetV2 model path
- `FACE_ANTISPOOF_ENABLED` — Enable liveness detection (default: true)
- `FACE_HEADPOSE_ENABLED` — Enable head-pose estimation (default: false)
- `FACE_ANTISPOOF_CONFIDENCE_THRESHOLD` — Liveness threshold (default: 0.3)

#### Attendance UX
- `ATTENDANCE_FREEZE_SECONDS` — Freeze duration after recognition (default: 3.0)
- `ATTENDANCE_FREEZE_SOUND_ENABLED` — Play sound on recognition (default: true)

---

## Deployment

### System Requirements
- **OS:** Windows, macOS, Linux
- **Python:** 3.11+
- **RAM:** 4 GB minimum (8 GB recommended)
- **Disk:** 500 MB (models + DB)
- **Webcam:** USB or built-in

### Installation
```bash
# Clone repo
git clone <repo-url>
cd fyp-3

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
attendance-storage-init

# Launch application
attendance-app
```

### ONNX Models
Models are gitignored. Download separately:
- `models/face_detection/yunet_2023mar.onnx`
- `models/face_recognition/sface_2021dec.onnx`
- `models/anti_spoof/minifasnet_v2_se_int8.onnx`
- `models/head_pose/mobileNetV2_head_pose.onnx`

---

## Next Steps (Roadmap)

### Immediate (Phase 4 Completion)
1. **Collect validation data** (real + fake face videos)
2. **Run threshold tuning script** and review results
3. **Update threshold** to optimal value
4. **Test with real attendance session**

### Future Enhancements (Out of Scope)
- [ ] Multi-camera support
- [ ] Batch attendance import/export
- [ ] Advanced analytics dashboard
- [ ] Mobile app companion
- [ ] Cloud sync (optional)
- [ ] 3D liveness detection (upgrade from 2D)
- [ ] Mask detection
- [ ] Age/gender estimation

---

## Key Contacts & Resources

### Documentation
- **Architecture:** `docs/architecture.md`
- **AI Pipeline:** `docs/ai-pipeline.md`
- **Database:** `docs/database.md`
- **Modules:** `docs/modules.md`

### Code References
- **Entry Point:** `src/main.py`
- **Config:** `src/attendance_system/core/config.py`
- **AI Pipeline:** `src/attendance_system/services/ai_pipeline.py`
- **Liveness:** `src/attendance_system/services/liveness_tracker.py`
- **UI:** `src/attendance_system/ui/`

### Testing
- **Unit Tests:** `tests/unit/`
- **Integration Tests:** `tests/integration/`
- **Test Fixtures:** `tests/conftest.py`

---

## Glossary

- **Liveness Detection** — Detecting if a face is real (not a photo/video/mask)
- **Anti-Spoofing** — Preventing spoofing attacks (same as liveness detection)
- **Face Embedding** — Vector representation of a face (512-dim for SFace)
- **Temporal Smoothing** — Aggregating decisions over multiple frames (EMA + hysteresis)
- **Circuit-Breaker** — Stopping inference after 30 consecutive failures
- **Preprocessing** — Crop, resize, normalize before model inference
- **Enrollment** — Capturing and storing a user's face embedding
- **Recognition** — Matching a live face against stored embeddings
- **Session** — A period of attendance recording (open/close/status)

---

## Version History

| Date | Version | Status | Notes |
|------|---------|--------|-------|
| 2026-06-08 | 0.1.0 | Phase 4 | Threshold tuning in progress, all features implemented |
| 2026-06-07 | 0.1.0 | Phase 4 | UI polish review cleanups completed |
| 2026-06-06 | 0.1.0 | Phase 4 | Cache invalidation enforced, architecture deepening 4/5 done |
| 2026-06-04 | 0.1.0 | Phase 3 | CameraWorkerBase extracted, temporal smoothing integrated |
| 2026-06-03 | 0.1.0 | Phase 3 | AIPipeline orchestrator + FacePreprocessor extracted |
| 2026-06-02 | 0.1.0 | Phase 2 | Attendance freeze feedback implemented |

