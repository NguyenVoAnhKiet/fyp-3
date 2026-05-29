"""
Tune the liveness threshold using real & spoof video recordings.

Usage
-----
    python scripts/tune_liveness_threshold.py ^
        --real-video real_face.mp4 ^
        --fake-video fake_face.mp4 ^
        --output-dir ./threshold_tuning_results

This script:
    1. Extracts all frames from both videos.
    2. Runs the MiniFASNet liveness model on every detected face.
    3. Collects raw logit-diff scores into a CSV.
    4. Computes statistics and finds an optimal threshold where
       the false-acceptance rate (FAR) on spoof samples < 1 %.
    5. Produces a histogram plot (requires ``matplotlib``).
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from pathlib import Path

# All heavy imports (cv2, numpy, onnxruntime, matplotlib) are deferred
# to the functions that need them so that --help works without them.

_LIVENESS_IMG_SIZE = 128


# ---------------------------------------------------------------------------
# Liveness preprocessing — matches attendance_system.services.ai_pipeline
# ---------------------------------------------------------------------------


def _preprocess_liveness(face_rgb):
    """Letterbox-resize and normalise a face crop for MiniFASNet.

    Pipeline::

        1. Resize longest side to 128 px (keep aspect ratio).
        2. Reflect-pad to 128×128.
        3. HWC → CHW, normalise to [0, 1].

    Returns array of shape ``[1, 3, 128, 128]`` (float32).
    """
    import cv2
    import numpy as np

    old_size = face_rgb.shape[:2]
    ratio = float(_LIVENESS_IMG_SIZE) / max(old_size)
    scaled_shape = (int(old_size[0] * ratio), int(old_size[1] * ratio))
    interp = cv2.INTER_LANCZOS4 if ratio > 1.0 else cv2.INTER_AREA
    img = cv2.resize(
        face_rgb, (scaled_shape[1], scaled_shape[0]), interpolation=interp
    )

    delta_h = _LIVENESS_IMG_SIZE - scaled_shape[0]
    delta_w = _LIVENESS_IMG_SIZE - scaled_shape[1]
    top, bottom = delta_h // 2, delta_h - (delta_h // 2)
    left, right = delta_w // 2, delta_w - (delta_w // 2)
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_REFLECT_101)

    arr = img.transpose(2, 0, 1).astype(np.float32) / 255.0
    return arr[np.newaxis]  # [1, 3, H, W]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_detector(model_path, input_size=(640, 480), score_threshold=0.8,
                     nms_threshold=0.3):
    """Create a YuNet face detector."""
    import cv2
    return cv2.FaceDetectorYN.create(
        str(model_path), "", input_size, score_threshold, nms_threshold
    )


def _frame_generator(video_path, every_n=1):
    """Yield ``(frame_index, bgr_frame)`` for every *every_n*-th frame."""
    import cv2
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % every_n == 0:
            yield idx, frame
        idx += 1
    cap.release()


def _face_bboxes(detector, frame_bgr):
    """Run detector and return list of ``(x, y, w, h)`` tuples."""
    import numpy as np
    _, faces = detector.detect(frame_bgr)
    if faces is None:
        return []
    bboxes = []
    for face in faces:
        x, y, w, h = face[:4].astype(int)
        bboxes.append((x, y, w, h))
    return bboxes


def _crop_face(frame_rgb, bbox, scale=2.7):
    """Center-crop a face from the RGB frame (same logic as ``face_utils``)."""
    x, y, w, h = bbox
    cx, cy = x + w // 2, y + h // 2
    side = int(max(w, h) * scale)
    half = side // 2
    fh, fw = frame_rgb.shape[:2]
    x1, y1 = max(0, cx - half), max(0, cy - half)
    x2, y2 = min(fw, cx + half), min(fh, cy + half)
    return frame_rgb[y1:y2, x1:x2]


def _classify_threshold(scores_real, scores_spoof, far_target=0.01):
    """Find the optimal score threshold where FAR ≤ *far_target*.

    Returns ``(best_threshold, stats_dict)``.
    """
    import numpy as np

    all_scores = sorted(set(scores_real + scores_spoof))
    best_thresh = None
    best_far = float("inf")

    for thresh in all_scores:
        # FAR = proportion of spoof samples accepted as real
        far = sum(1 for s in scores_spoof if s >= thresh) / max(len(scores_spoof), 1)

        # Prefer the *lowest* threshold that brings FAR ≤ far_target.
        # Using strict < ensures we keep the first (lowest) match.
        if far <= far_target and (best_thresh is None or far < best_far):
            best_far = far
            best_thresh = thresh

    # Fallback if no threshold achieves FAR ≤ far_target
    if best_thresh is None:
        # Pick the threshold that gives the minimum FAR
        best_thresh = min(all_scores, key=lambda t: (
            sum(1 for s in scores_spoof if s >= t) / max(len(scores_spoof), 1), t
        ))

    # Compute final stats at best_thresh
    far = sum(1 for s in scores_spoof if s >= best_thresh) / max(len(scores_spoof), 1)
    frr = sum(1 for s in scores_real if s < best_thresh) / max(len(scores_real), 1)

    stats = {
        "threshold": best_thresh,
        "far": far,
        "frr": frr,
        "real_count": len(scores_real),
        "spoof_count": len(scores_spoof),
        "real_mean": float(np.mean(scores_real)),
        "real_std": float(np.std(scores_real)),
        "real_min": float(np.min(scores_real)),
        "real_max": float(np.max(scores_real)),
        "spoof_mean": float(np.mean(scores_spoof)),
        "spoof_std": float(np.std(scores_spoof)),
        "spoof_min": float(np.min(scores_spoof)),
        "spoof_max": float(np.max(scores_spoof)),
    }
    return best_thresh, stats


# ---------------------------------------------------------------------------
# Plotting (optional — requires matplotlib)
# ---------------------------------------------------------------------------


def _plot_histogram(scores_real, scores_spoof, threshold, output_path):
    """Plot overlayed histograms of real and spoof score distributions."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print(
            "[WARN] matplotlib not installed — skipping histogram plot. "
            "Install with: pip install matplotlib"
        )
        return

    import numpy as np

    fig, ax = plt.subplots(figsize=(10, 6))

    bins = np.linspace(
        min(min(scores_real), min(scores_spoof)),
        max(max(scores_real), max(scores_spoof)),
        60,
    )

    ax.hist(
        scores_real,
        bins=bins,
        alpha=0.6,
        color="green",
        label=f"Real (n={len(scores_real)})",
    )
    ax.hist(
        scores_spoof,
        bins=bins,
        alpha=0.6,
        color="red",
        label=f"Spoof (n={len(scores_spoof)})",
    )
    ax.axvline(threshold, color="blue", linestyle="--", linewidth=2,
               label=f"Threshold = {threshold:.4f}")

    ax.set_xlabel("Liveness Score (logit_diff)")
    ax.set_ylabel("Frame Count")
    ax.set_title("Real vs Spoof Liveness Score Distribution")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(str(output_path), dpi=150)
    plt.close(fig)
    print(f"  Histogram saved → {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tune liveness threshold from real & spoof video recordings.",
    )
    parser.add_argument(
        "--real-video", required=True,
        help="Path to video of a real (live) person.",
    )
    parser.add_argument(
        "--fake-video", required=True,
        help="Path to video of a spoof (photo / screen) attack.",
    )
    parser.add_argument(
        "--output-dir", default="./threshold_tuning_results",
        help="Directory for output CSV, plot, and report (default: ./threshold_tuning_results).",
    )
    parser.add_argument(
        "--liveness-model",
        default="models/anti_spoof/best_model_quantized.onnx",
        help="Path to MiniFASNet ONNX model (default: models/anti_spoof/best_model_quantized.onnx).",
    )
    parser.add_argument(
        "--detector-model",
        default="models/face_detection/face_detection_yunet_2023mar.onnx",
        help="Path to YuNet ONNX model (default: models/face_detection/face_detection_yunet_2023mar.onnx).",
    )
    parser.add_argument(
        "--every-n", type=int, default=1,
        help="Process every N-th frame (default: 1 = every frame).",
    )
    parser.add_argument(
        "--far-target", type=float, default=0.01,
        help="Target false-acceptance rate (default: 0.01 = 1%%).",
    )
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = build_parser().parse_args()

    # Resolve paths ---------------------------------------------------------
    real_video = Path(args.real_video)
    fake_video = Path(args.fake_video)
    output_dir = Path(args.output_dir)
    liveness_model_path = Path(args.liveness_model)
    detector_model_path = Path(args.detector_model)
    every_n = args.every_n
    far_target = args.far_target

    # Validate inputs -------------------------------------------------------
    for p, label in [
        (real_video, "Real video"),
        (fake_video, "Fake video"),
        (liveness_model_path, "Liveness model"),
        (detector_model_path, "Detector model"),
    ]:
        if not p.exists():
            print(f"[ERROR] {label} not found: {p}", file=sys.stderr)
            sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load ONNX liveness model ----------------------------------------------
    print("Loading ONNX Runtime...")
    import onnxruntime as ort

    print(f"  Liveness model : {liveness_model_path}")
    session = ort.InferenceSession(str(liveness_model_path))
    input_name = session.get_inputs()[0].name

    # Process videos --------------------------------------------------------
    import cv2
    import numpy as np

    detector = _create_detector(detector_model_path)

    csv_path = output_dir / "liveness_scores.csv"
    csv_file = open(csv_path, "w", newline="")
    writer = csv.writer(csv_file)
    writer.writerow(["label", "frame_index", "score"])

    scores_real: list[float] = []
    scores_spoof: list[float] = []

    for label, video_path in [("real", real_video), ("spoof", fake_video)]:
        print(f"\nProcessing {label} video: {video_path.name}")
        frame_count = 0
        face_count = 0
        t0 = time.perf_counter()

        for frame_idx, frame_bgr in _frame_generator(video_path, every_n):
            frame_count += 1

            # Detect faces
            bboxes = _face_bboxes(detector, frame_bgr)
            if not bboxes:
                continue

            # Convert to RGB once
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

            for bbox in bboxes:
                face_crop = _crop_face(frame_rgb, bbox, scale=2.7)
                if face_crop.size == 0:
                    continue

                # Preprocess & run inference
                tensor = _preprocess_liveness(face_crop)
                raw = session.run(None, {input_name: tensor})
                output: np.ndarray = np.array(raw[0])
                # logit_diff = real_logit - spoof_logit
                logit_diff = float(output[0][0] - output[0][1])

                if label == "real":
                    scores_real.append(logit_diff)
                else:
                    scores_spoof.append(logit_diff)
                writer.writerow([label, frame_idx, f"{logit_diff:.6f}"])
                face_count += 1

                # Only use the highest-confidence face per frame
                break

            if frame_idx % 100 == 0 and frame_idx > 0:
                elapsed = time.perf_counter() - t0
                print(f"    ... {frame_idx} frames, {face_count} faces ({elapsed:.1f}s)")

        elapsed = time.perf_counter() - t0
        print(f"  Done — {frame_count} frames, {face_count} faces in {elapsed:.1f}s")

    csv_file.close()
    print(f"\n  Scores CSV → {csv_path}")

    # Analyse scores --------------------------------------------------------
    print(f"\n{'='*60}")
    print("  ANALYSIS")
    print(f"{'='*60}")

    if not scores_real:
        print("[ERROR] No real face scores collected.", file=sys.stderr)
        sys.exit(1)
    if not scores_spoof:
        print("[ERROR] No spoof face scores collected.", file=sys.stderr)
        sys.exit(1)

    print(f"\n  Real  frames with face: {len(scores_real)}")
    print(f"  Spoof frames with face: {len(scores_spoof)}")

    best_thresh, stats = _classify_threshold(scores_real, scores_spoof, far_target)

    print(f"\n  {'Statistic':<25} {'Real':<18} {'Spoof':<18}")
    print(f"  {'─'*59}")
    for stat in ["mean", "std", "min", "max"]:
        rval = stats[f"real_{stat}"]
        sval = stats[f"spoof_{stat}"]
        print(f"  {stat:<25} {rval:<18.6f} {sval:<18.6f}")

    print(f"\n  Optimal threshold (FAR ≤ {far_target:.0%}):")
    print(f"    threshold = {stats['threshold']:.6f}")
    print(f"    FAR       = {stats['far']:.4%}  (spoof falsely accepted)")
    print(f"    FRR       = {stats['frr']:.4%}  (real falsely rejected)")

    # Reference thresholds --------------------------------------------------
    def prob_to_logit(p: float) -> float:
        p = max(1e-6, min(1 - 1e-6, p))
        return math.log(p / (1 - p))

    print(f"\n  Reference:")
    print(f"    Current app default (prob=0.30) → logit = {prob_to_logit(0.30):.6f}")
    print(f"    Current app default (prob=0.50) → logit = {prob_to_logit(0.50):.6f}")

    # Save report -----------------------------------------------------------
    report_path = output_dir / "recommended_threshold.txt"
    with open(report_path, "w") as f:
        f.write("Liveness Threshold Tuning Report\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Real video: {real_video}\n")
        f.write(f"Fake video: {fake_video}\n\n")
        f.write(f"Real samples: {stats['real_count']}\n")
        f.write(f"Spoof samples: {stats['spoof_count']}\n\n")
        f.write(f"   {'Statistic':<20} {'Real':<18} {'Spoof':<18}\n")
        f.write(f"   {'─'*54}\n")
        for stat in ["mean", "std", "min", "max"]:
            rval = stats[f"real_{stat}"]
            sval = stats[f"spoof_{stat}"]
            f.write(f"   {stat:<20} {rval:<18.6f} {sval:<18.6f}\n")
        f.write(f"\n\nOptimal threshold (FAR ≤ {far_target:.0%}):\n")
        f.write(f"  logit_diff  = {stats['threshold']:.6f}\n")
        f.write(f"  FAR         = {stats['far']:.4%}\n")
        f.write(f"  FRR         = {stats['frr']:.4%}\n\n")
        f.write(f"To apply, set in .env:\n")
        f.write(f"  FACE_ANTISPOOF_CONFIDENCE_THRESHOLD={stats['threshold']:.6f}\n")
        f.write(f"Or via the Admin Settings UI (applies on restart).\n")
    print(f"\n  Report → {report_path}")

    # Plot (optional) -------------------------------------------------------
    plot_path = output_dir / "liveness_histogram.png"
    _plot_histogram(scores_real, scores_spoof, best_thresh, plot_path)

    print(f"\n  All outputs saved under: {output_dir.resolve()}")
    print("  Done.")


if __name__ == "__main__":
    main()
