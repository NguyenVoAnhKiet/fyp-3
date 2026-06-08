# scripts/

## Responsibility

Standalone utility scripts for maintenance, debugging, database management, and AI-model diagnostics. These are not part of the main application entry points (`attendance-app`, `attendance-storage-init`) and are intended to be run manually by a developer or administrator.

## Scripts

### `reset_users.py`

**Purpose:** Deletes all users and face references from the database while preserving attendance records and recognition events for historical tracking.

**Usage:**
```bash
PYTHONPATH=src python scripts/reset_users.py
```

**Behavior:**
1. Reads `DATABASE_PATH` from `.env` (defaults to `attendance.db`).
2. Prints a summary of what will be deleted vs. preserved.
3. Prompts for interactive confirmation (must type `YES`).
4. Deletes rows from `face_references` first (to respect the FK constraint against `users`), then from `users`.
5. Attendance/recognition tables are left untouched.

---

### `diagnose_poor_light.py`

**Purpose:** First-line diagnostic harness for the known ~95% liveness-rejection rate of real faces in poor lighting. Runs a single face image through the MiniFASNet liveness pipeline with several preprocessing variations (standard, CLAHE, gamma correction) to isolate whether the root cause is preprocessing or the model itself.

**Usage:**
```bash
python scripts/diagnose_poor_light.py --image path/to/face.jpg
```

**Behavior:**
1. Loads a single face image and a MiniFASNet ONNX model (default `models/anti_spoof/best_model_quantized.onnx`).
2. Runs inference with four preprocessing configurations: standard (current), CLAHE contrast enhancement, gamma=1.5, gamma=2.0.
3. Reports each score as logit_diff and a REAL/SPOOF decision at the current threshold (default 0.3).
4. Prints interpretation guidance based on which (if any) preprocessing variant crosses the threshold.

**Related to:** `test_poor_light_liveness.py` (batch variant), `hypothesis_test_poor_light.py` (root-cause analysis), `tune_liveness_threshold.py` (threshold calibration).

---

### `test_poor_light_liveness.py`

**Purpose:** Batch diagnostic that tests the liveness model against synthetic face images at multiple brightness levels (normal, dim, poor, very poor) with multiple preprocessing methods. Produces a comparison table showing which preprocessing technique (CLAHE, gamma 1.5, gamma 2.0) best recovers poor-light faces.

**Usage:**
```bash
python scripts/test_poor_light_liveness.py
```

**Behavior:**
1. Generates synthetic face images (skin-tone rectangle with eyes and mouth) at brightness levels 1.0, 0.7, 0.5, 0.3.
2. For each brightness level, runs inference with standard, CLAHE, gamma=1.5, and gamma=2.0 preprocessing.
3. Prints a tabular summary of REAL/SPOOF status per method and brightness level.
4. Analyzes which preprocessing methods improve scores over the baseline.

**Relationship:** Batch counterpart to `diagnose_poor_light.py` — tests systematically across a brightness sweep instead of a single image. Uses synthetic faces rather than real images to control lighting precisely.

---

### `hypothesis_test_poor_light.py`

**Purpose:** Deeper root-cause investigation of poor-light liveness rejection. Tests four specific hypotheses using synthetic faces with controlled properties (brightness, contrast, noise, crop scale) to understand *why* the model rejects dark images.

**Usage:**
```bash
python scripts/hypothesis_test_poor_light.py
```

**Hypotheses tested:**
1. **H1 — Score collapse:** Model logit_real and logit_diff become very negative as brightness decreases.
2. **H2 — Threshold sensitivity:** Whether reducing the threshold (0.3 → 0.5 → 0.7) recovers poor-light faces.
3. **H3 — Crop scale:** Whether the crop scale factor (currently 2.7) is suboptimal for poor lighting.
4. **H4 — Confidence distribution:** How softmax confidence in "real" degrades with brightness.

**Output:** Tabular results per hypothesis with interpretation text suggesting likely root cause (domain shift, training-distribution mismatch).

**Relationship:** Follows `diagnose_poor_light.py` or `test_poor_light_liveness.py` — once rejection is confirmed, this script diagnoses *why*. Designed to inform whether the fix should be preprocessing changes, threshold tuning, or model retraining.

---

### `tune_liveness_threshold.py`

**Purpose:** Data-driven threshold calibration tool. Processes real-face and spoof-attack video recordings, runs the full liveness pipeline frame-by-frame, collects score distributions, and finds the optimal logit-diff threshold that minimizes false-acceptance rate (FAR) at a configurable target (default 1%).

**Usage:**
```bash
python scripts/tune_liveness_threshold.py ^
    --real-video real_face.mp4 ^
    --fake-video fake_face.mp4 ^
    --output-dir ./threshold_tuning_results
```

**Behavior:**
1. Loads two video files (real face and spoof attack) and the MiniFASNet liveness model.
2. For every N-th frame (configurable via `--every-n`), detects faces with YuNet, crops at scale 2.7, preprocesses, and runs inference.
3. Writes all scores (with label and frame index) to a CSV file.
4. Computes distribution statistics (mean, std, min, max) for real and spoof scores.
5. Finds the optimal threshold where FAR ≤ `--far-target` (default 0.01).
6. Outputs a histogram plot (requires `matplotlib`) and a text report with the recommended `.env` setting.

**Output files** (in `--output-dir`):
- `liveness_scores.csv` — all per-frame scores with labels.
- `recommended_threshold.txt` — statistics, optimal threshold, and the `.env` variable to set.
- `liveness_histogram.png` — overlayed real/spoof score histogram (if matplotlib available).

**Relationship:** Complementary to the diagnostic scripts — those identify *that* poor-light rejection exists; this one calibrates the threshold to balance real-vs-spoof tradeoffs. The recommended threshold can be set via `FACE_ANTISPOOF_CONFIDENCE_THRESHOLD` in `.env` or the Admin UI.

---

## Script relationships summary

```
diagnose_poor_light.py          Single-image diagnosis (real photo)
        │
        ├── test_poor_light_liveness.py     Synthetic brightness sweep
        │
        └── hypothesis_test_poor_light.py   Root-cause investigation

tune_liveness_threshold.py      Data-driven threshold calibration (real + spoof video)
```

The diagnostic triplet (`diagnose`, `test`, `hypothesis_test`) all investigate the same known limitation — MiniFASNet's rejection of ~95% of real faces in poor lighting. They form an investigative pipeline from symptom detection → systematic measurement → root-cause analysis. The tuning script is independent: it solves a different problem (optimal threshold selection using ground-truth video pairs) and feeds its result back into the application configuration.
