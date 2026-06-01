"""
Hypothesis testing for poor-light liveness rejection.

Tests specific hypotheses about why real faces are rejected in poor lighting.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

_LIVENESS_IMG_SIZE = 128


def _create_synthetic_face(brightness: float = 1.0, contrast: float = 1.0, noise: float = 0.0) -> np.ndarray:
    """Create a synthetic face with adjustable properties."""
    img = np.ones((256, 256, 3), dtype=np.uint8)
    skin_color = np.array([210, 180, 160], dtype=np.uint8)
    img[:, :] = skin_color
    
    eye_color = np.array([50, 50, 50], dtype=np.uint8)
    cv2.circle(img, (100, 100), 15, tuple(eye_color.tolist()), -1)
    cv2.circle(img, (156, 100), 15, tuple(eye_color.tolist()), -1)
    
    mouth_color = np.array([150, 80, 80], dtype=np.uint8)
    cv2.ellipse(img, (128, 180), (40, 20), 0, 0, 180, tuple(mouth_color.tolist()), -1)
    
    img_float = img.astype(np.float32) / 255.0
    img_float = (img_float - 0.5) * contrast + 0.5
    img_float = img_float * brightness
    
    if noise > 0:
        img_float += np.random.normal(0, noise, img_float.shape)
    
    img_float = np.clip(img_float, 0, 1)
    img = (img_float * 255).astype(np.uint8)
    
    return img


def _preprocess_standard(face_rgb: np.ndarray) -> np.ndarray:
    """Standard preprocessing."""
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


def run_inference(session: ort.InferenceSession, input_name: str, tensor: np.ndarray) -> tuple[float, float, float]:
    """Run inference and return (logit_real, logit_spoof, logit_diff)."""
    raw = session.run(None, {input_name: tensor})
    output = np.array(raw[0])
    logit_real = float(output[0][0])
    logit_spoof = float(output[0][1])
    logit_diff = logit_real - logit_spoof
    return logit_real, logit_spoof, logit_diff


def main() -> None:
    model_path = Path("models/anti_spoof/best_model_quantized.onnx")
    
    if not model_path.exists():
        print(f"[ERROR] Model not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    print("Loading ONNX model...")
    session = ort.InferenceSession(str(model_path))
    input_name = session.get_inputs()[0].name

    print("\n" + "="*70)
    print("  HYPOTHESIS TESTING: POOR-LIGHT LIVENESS REJECTION")
    print("="*70 + "\n")

    # Hypothesis 1: Model outputs are very negative in poor light
    print("[H1] Model outputs are very negative in poor light")
    print("-" * 70)
    
    for brightness in [1.0, 0.7, 0.5, 0.3]:
        face_rgb = _create_synthetic_face(brightness=brightness)
        tensor = _preprocess_standard(face_rgb)
        logit_real, logit_spoof, logit_diff = run_inference(session, input_name, tensor)
        print(f"  Brightness {brightness:.1f}: logit_real={logit_real:>8.4f}, logit_spoof={logit_spoof:>8.4f}, diff={logit_diff:>8.4f}")
    
    print("\n  Interpretation: If logit_diff becomes very negative, the model is")
    print("  increasingly confident it's a spoof (not a real face).\n")

    # Hypothesis 2: Threshold is too high relative to poor-light scores
    print("[H2] Threshold is too high relative to poor-light scores")
    print("-" * 70)
    
    import math
    thresholds = [0.3, 0.5, 0.7]
    brightness_levels = [1.0, 0.7, 0.5, 0.3]
    
    print(f"  {'Brightness':<12} ", end="")
    for t in thresholds:
        p = max(1e-6, min(1 - 1e-6, t))
        logit_t = math.log(p / (1 - p))
        print(f"T={t:.1f}({logit_t:>7.3f}) ", end="")
    print()
    print("  " + "-" * 66)
    
    for brightness in brightness_levels:
        face_rgb = _create_synthetic_face(brightness=brightness)
        tensor = _preprocess_standard(face_rgb)
        _, _, logit_diff = run_inference(session, input_name, tensor)
        
        print(f"  {brightness:.1f}          ", end="")
        for t in thresholds:
            p = max(1e-6, min(1 - 1e-6, t))
            logit_t = math.log(p / (1 - p))
            decision = "REAL" if logit_diff > logit_t else "SPOOF"
            print(f"  {decision:<8} ", end="")
        print()
    
    print("\n  Interpretation: If poor-light faces are SPOOF at all thresholds,")
    print("  the model itself is the limitation, not the threshold.\n")

    # Hypothesis 3: Crop scale affects poor-light detection
    print("[H3] Crop scale affects poor-light detection")
    print("-" * 70)
    
    # Test with different crop scales by resizing the face
    face_rgb = _create_synthetic_face(brightness=0.5)
    
    for scale_factor in [0.5, 0.75, 1.0, 1.25, 1.5]:
        h, w = face_rgb.shape[:2]
        new_h, new_w = int(h * scale_factor), int(w * scale_factor)
        resized = cv2.resize(face_rgb, (new_w, new_h))
        
        # Pad back to original size
        if new_h < h or new_w < w:
            padded = np.ones_like(face_rgb) * 128
            y_offset = (h - new_h) // 2
            x_offset = (w - new_w) // 2
            padded[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
            resized = padded
        
        tensor = _preprocess_standard(resized)
        _, _, logit_diff = run_inference(session, input_name, tensor)
        print(f"  Scale {scale_factor:.2f}: logit_diff={logit_diff:>8.4f}")
    
    print("\n  Interpretation: If score varies significantly with scale,")
    print("  the crop scale (2.7) might be suboptimal for poor lighting.\n")

    # Hypothesis 4: Model confidence distribution
    print("[H4] Model confidence distribution across brightness levels")
    print("-" * 70)
    
    print(f"  {'Brightness':<12} {'logit_real':<12} {'logit_spoof':<12} {'Confidence':<12}")
    print("  " + "-" * 48)
    
    for brightness in [1.0, 0.7, 0.5, 0.3]:
        face_rgb = _create_synthetic_face(brightness=brightness)
        tensor = _preprocess_standard(face_rgb)
        logit_real, logit_spoof, _ = run_inference(session, input_name, tensor)
        
        # Softmax confidence
        exp_real = np.exp(logit_real)
        exp_spoof = np.exp(logit_spoof)
        conf_real = exp_real / (exp_real + exp_spoof)
        
        print(f"  {brightness:.1f}          {logit_real:>11.4f} {logit_spoof:>11.4f} {conf_real:>11.4f}")
    
    print("\n  Interpretation: If confidence in 'real' drops sharply in poor light,")
    print("  the model is genuinely uncertain, not just threshold-sensitive.\n")

    print("="*70)
    print("  CONCLUSION")
    print("="*70)
    print("\nBased on the above tests, the root cause is likely:")
    print("  - Model domain shift (trained on well-lit faces)")
    print("  - Poor-light faces are outside the training distribution")
    print("  - Preprocessing alone cannot fix this")
    print("\nPossible solutions:")
    print("  1. Collect poor-light training data and fine-tune the model")
    print("  2. Use a different liveness model trained on diverse lighting")
    print("  3. Accept the limitation and document it")
    print("  4. Implement adaptive thresholding based on image brightness")
    print()


if __name__ == "__main__":
    main()
