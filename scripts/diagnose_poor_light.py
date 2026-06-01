"""
Diagnostic harness for poor-light liveness rejection.

This script tests a single face image through the liveness pipeline
with different preprocessing variations to isolate the cause of
95% rejection rate in poor lighting.

Usage:
    python scripts/diagnose_poor_light.py --image poor_light_face.jpg

Output:
    - Raw liveness score (logit_diff)
    - Decision at current threshold (0.3)
    - Comparison across preprocessing variations
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

_LIVENESS_IMG_SIZE = 128


def _preprocess_standard(face_rgb: np.ndarray) -> np.ndarray:
    """Current preprocessing: letterbox + reflect-pad + normalize."""
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
    return arr[np.newaxis]


def _preprocess_with_clahe(face_rgb: np.ndarray) -> np.ndarray:
    """Preprocessing with CLAHE (contrast enhancement for poor light)."""
    # Apply CLAHE to improve contrast in poor lighting
    lab = cv2.cvtColor(face_rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    face_rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    # Then apply standard preprocessing
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
    return arr[np.newaxis]


def _preprocess_with_gamma(face_rgb: np.ndarray, gamma: float = 1.5) -> np.ndarray:
    """Preprocessing with gamma correction (brighten dark images)."""
    # Gamma correction: output = input^(1/gamma)
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
    face_rgb = cv2.LUT(face_rgb, table)

    # Then apply standard preprocessing
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
    return arr[np.newaxis]


def run_inference(session: ort.InferenceSession, input_name: str, tensor: np.ndarray) -> float:
    """Run liveness inference and return logit_diff score."""
    raw = session.run(None, {input_name: tensor})
    output = np.array(raw[0])
    logit_diff = float(output[0][0] - output[0][1])
    return logit_diff


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose poor-light liveness rejection."
    )
    parser.add_argument("--image", required=True, help="Path to face image (RGB or BGR).")
    parser.add_argument(
        "--liveness-model",
        default="models/anti_spoof/best_model_quantized.onnx",
        help="Path to MiniFASNet ONNX model.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        help="Liveness threshold (default: 0.3).",
    )
    args = parser.parse_args()

    # Validate inputs
    image_path = Path(args.image)
    model_path = Path(args.liveness_model)

    if not image_path.exists():
        print(f"[ERROR] Image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    if not model_path.exists():
        print(f"[ERROR] Model not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    # Load image
    print(f"Loading image: {image_path}")
    img_bgr = cv2.imread(str(image_path))
    if img_bgr is None:
        print(f"[ERROR] Failed to load image: {image_path}", file=sys.stderr)
        sys.exit(1)

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    print(f"  Image shape: {img_rgb.shape}")

    # Load model
    print(f"\nLoading ONNX model: {model_path}")
    session = ort.InferenceSession(str(model_path))
    input_name = session.get_inputs()[0].name
    print(f"  Input name: {input_name}")

    # Convert threshold to logit space
    import math
    p = max(1e-6, min(1 - 1e-6, args.threshold))
    logit_threshold = math.log(p / (1 - p))

    print(f"\n{'='*70}")
    print(f"  LIVENESS INFERENCE RESULTS")
    print(f"{'='*70}")
    print(f"  Threshold (probability): {args.threshold:.4f}")
    print(f"  Threshold (logit space): {logit_threshold:.6f}")
    print(f"{'='*70}\n")

    # Test 1: Standard preprocessing
    print("[1] Standard preprocessing (current)")
    tensor = _preprocess_standard(img_rgb)
    score = run_inference(session, input_name, tensor)
    decision = "REAL ✓" if score > logit_threshold else "SPOOF ✗"
    print(f"    Score: {score:.6f}")
    print(f"    Decision: {decision}")
    print()

    # Test 2: With CLAHE
    print("[2] With CLAHE (contrast enhancement)")
    tensor = _preprocess_with_clahe(img_rgb)
    score = run_inference(session, input_name, tensor)
    decision = "REAL ✓" if score > logit_threshold else "SPOOF ✗"
    print(f"    Score: {score:.6f}")
    print(f"    Decision: {decision}")
    print()

    # Test 3: With gamma correction
    print("[3] With gamma correction (brighten)")
    tensor = _preprocess_with_gamma(img_rgb, gamma=1.5)
    score = run_inference(session, input_name, tensor)
    decision = "REAL ✓" if score > logit_threshold else "SPOOF ✗"
    print(f"    Score: {score:.6f}")
    print(f"    Decision: {decision}")
    print()

    # Test 4: With stronger gamma
    print("[4] With stronger gamma correction (gamma=2.0)")
    tensor = _preprocess_with_gamma(img_rgb, gamma=2.0)
    score = run_inference(session, input_name, tensor)
    decision = "REAL ✓" if score > logit_threshold else "SPOOF ✗"
    print(f"    Score: {score:.6f}")
    print(f"    Decision: {decision}")
    print()

    print(f"{'='*70}")
    print("  INTERPRETATION")
    print(f"{'='*70}")
    print("  If all scores are negative (SPOOF), the model is rejecting the face.")
    print("  If CLAHE/gamma helps, preprocessing is the issue.")
    print("  If all are still SPOOF, the model itself is too strict for poor light.")
    print()


if __name__ == "__main__":
    main()
