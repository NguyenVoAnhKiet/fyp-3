"""
Feedback loop for poor-light liveness rejection diagnosis.

This creates synthetic test data (simulated poor-light faces) and measures
the liveness model's rejection rate with different preprocessing approaches.

Usage:
    python scripts/test_poor_light_liveness.py

Output:
    - Rejection rates for standard vs. enhanced preprocessing
    - Comparison of CLAHE, gamma correction, and other techniques
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

_LIVENESS_IMG_SIZE = 128


def _create_synthetic_face(brightness: float = 1.0, contrast: float = 1.0) -> np.ndarray:
    """Create a synthetic face image with adjustable brightness/contrast.
    
    Args:
        brightness: Multiplier for pixel values (< 1.0 = darker)
        contrast: Multiplier for contrast (< 1.0 = lower contrast)
    
    Returns:
        H×W×3 uint8 RGB image
    """
    # Create a simple synthetic face: skin-tone rectangle with eyes
    img = np.ones((256, 256, 3), dtype=np.uint8)
    
    # Skin tone (RGB)
    skin_color = np.array([210, 180, 160], dtype=np.uint8)
    img[:, :] = skin_color
    
    # Eyes (darker)
    eye_color = np.array([50, 50, 50], dtype=np.uint8)
    cv2.circle(img, (100, 100), 15, tuple(eye_color.tolist()), -1)
    cv2.circle(img, (156, 100), 15, tuple(eye_color.tolist()), -1)
    
    # Mouth (darker)
    mouth_color = np.array([150, 80, 80], dtype=np.uint8)
    cv2.ellipse(img, (128, 180), (40, 20), 0, 0, 180, tuple(mouth_color.tolist()), -1)
    
    # Apply brightness/contrast
    img_float = img.astype(np.float32) / 255.0
    
    # Contrast: (x - 0.5) * contrast + 0.5
    img_float = (img_float - 0.5) * contrast + 0.5
    
    # Brightness: x * brightness
    img_float = img_float * brightness
    
    # Clamp and convert back
    img_float = np.clip(img_float, 0, 1)
    img = (img_float * 255).astype(np.uint8)
    
    return img


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
    """Preprocessing with CLAHE (contrast enhancement)."""
    lab = cv2.cvtColor(face_rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    face_rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

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
    """Preprocessing with gamma correction (brighten)."""
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
    face_rgb = cv2.LUT(face_rgb, table)

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
    model_path = Path("models/anti_spoof/best_model_quantized.onnx")
    
    if not model_path.exists():
        print(f"[ERROR] Model not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    # Load model
    print("Loading ONNX model...")
    session = ort.InferenceSession(str(model_path))
    input_name = session.get_inputs()[0].name

    # Test parameters
    import math
    threshold = 0.3
    p = max(1e-6, min(1 - 1e-6, threshold))
    logit_threshold = math.log(p / (1 - p))

    print(f"\n{'='*70}")
    print(f"  POOR-LIGHT LIVENESS REJECTION TEST")
    print(f"{'='*70}")
    print(f"  Threshold (probability): {threshold:.4f}")
    print(f"  Threshold (logit space): {logit_threshold:.6f}")
    print(f"{'='*70}\n")

    # Test with different brightness levels
    brightness_levels = [
        (1.0, "Normal lighting"),
        (0.7, "Dim lighting"),
        (0.5, "Poor lighting"),
        (0.3, "Very poor lighting"),
    ]

    results = {}

    for brightness, label in brightness_levels:
        print(f"\n[{label}] (brightness={brightness:.1f})")
        print(f"  {'-'*66}")
        
        # Create synthetic face
        face_rgb = _create_synthetic_face(brightness=brightness, contrast=1.0)
        
        # Test different preprocessing methods
        methods = [
            ("Standard", _preprocess_standard),
            ("With CLAHE", _preprocess_with_clahe),
            ("With Gamma 1.5", lambda x: _preprocess_with_gamma(x, 1.5)),
            ("With Gamma 2.0", lambda x: _preprocess_with_gamma(x, 2.0)),
        ]
        
        brightness_results = {}
        for method_name, preprocess_fn in methods:
            tensor = preprocess_fn(face_rgb)
            score = run_inference(session, input_name, tensor)
            is_real = score > logit_threshold
            decision = "REAL ✓" if is_real else "SPOOF ✗"
            print(f"    {method_name:<20} score={score:>8.4f}  {decision}")
            brightness_results[method_name] = (score, is_real)
        
        results[label] = brightness_results

    # Summary
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}\n")
    
    for brightness, label in brightness_levels:
        print(f"{label}:")
        for method_name, (score, is_real) in results[label].items():
            status = "✓ REAL" if is_real else "✗ SPOOF"
            print(f"  {method_name:<20} {status}")
        print()

    # Analysis
    print(f"{'='*70}")
    print(f"  ANALYSIS")
    print(f"{'='*70}\n")
    
    # Check if any method helps with poor lighting
    poor_light_results = results["Poor lighting"]
    standard_score, standard_real = poor_light_results["Standard"]
    
    improvements = []
    for method_name, (score, is_real) in poor_light_results.items():
        if method_name != "Standard":
            improvement = score - standard_score
            if improvement > 0:
                improvements.append((method_name, improvement, is_real))
    
    if improvements:
        print("Methods that improve poor-light detection:")
        for method_name, improvement, is_real in sorted(improvements, key=lambda x: x[1], reverse=True):
            status = "→ REAL ✓" if is_real else "→ still SPOOF"
            print(f"  {method_name:<20} +{improvement:.4f} {status}")
    else:
        print("No preprocessing method improves poor-light detection.")
        print("This suggests the model itself is the limitation.")
    
    print()


if __name__ == "__main__":
    main()
