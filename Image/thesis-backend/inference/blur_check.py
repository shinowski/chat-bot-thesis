"""
blur_check.py — sharpness gate (Laplacian variance).

Two parts:
  1. blur_score(image) + blur_status(image)  -> import into the Flask app
  2. python blur_check.py <dataset_dir>      -> calibrate thresholds

Put this in inference/ next to skin_detector.py.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter

# Fixed size so scores are comparable across image resolutions
LONG_SIDE = 512

# Fill these in after running calibration (placeholders below)
BLUR_BLOCK_BELOW = 5.0   # below this -> reject (too_blurry)
BLUR_WARN_BELOW = 16.0 # between block and warn -> pass with a warning


def blur_score(image: Image.Image) -> float:
    """Variance of the Laplacian on a fixed-size grayscale image. Higher = sharper."""
    img = image.convert("L")
    w, h = img.size
    scale = LONG_SIDE / max(w, h)
    img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))))
    lap = cv2.Laplacian(np.array(img), cv2.CV_64F)
    return float(lap.var())


def blur_status(image: Image.Image) -> tuple[str, float]:
    """Returns ("blocked" | "warn" | "ok", score)."""
    s = blur_score(image)
    if s < BLUR_BLOCK_BELOW:
        return "blocked", s
    if s < BLUR_WARN_BELOW:
        return "warn", s
    return "ok", s


# ------------------------------------------------------------
# Calibration
# ------------------------------------------------------------
def _collect(folder: Path):
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    return [p for p in folder.rglob("*") if p.suffix.lower() in exts]


def calibrate(dataset_dir: str, sample_blur_n: int = 200):
    paths = _collect(Path(dataset_dir))
    if not paths:
        print("No images found.")
        return

    scores = []
    for p in paths:
        try:
            scores.append(blur_score(Image.open(p)))
        except Exception:
            pass
    scores = np.array(scores)

    print(f"\n{len(scores)} images")
    for q in (1, 2, 5, 10, 25, 50, 75):
        print(f"  p{q:<2}: {np.percentile(scores, q):8.1f}")

    block = float(np.percentile(scores, 2))
    warn = float(np.percentile(scores, 10))
    print(f"\nSuggested BLUR_BLOCK_BELOW ~ {block:.1f}  (p2)")
    print(f"Suggested BLUR_WARN_BELOW  ~ {warn:.1f}  (p10)")

    # Sanity check: synthetic blur should land below the block cutoff
    rng = np.random.default_rng(42)
    sample = rng.choice(len(paths), size=min(sample_blur_n, len(paths)), replace=False)
    for radius in (2, 4, 8):
        blurred = []
        for i in sample:
            try:
                im = Image.open(paths[i]).convert("RGB").filter(ImageFilter.GaussianBlur(radius))
                blurred.append(blur_score(im))
            except Exception:
                pass
        blurred = np.array(blurred)
        caught = (blurred < block).mean() * 100
        print(f"  Gaussian blur r={radius}: median {np.median(blurred):6.1f}, "
              f"{caught:.0f}% below block cutoff")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python blur_check.py <dataset_dir>")
        sys.exit(1)
    calibrate(sys.argv[1])