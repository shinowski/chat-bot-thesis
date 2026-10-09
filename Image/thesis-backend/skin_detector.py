"""
skin_detector.py — Preliminary skin-content screening gate.

THESIS FRAMING:
This module does NOT detect skin lesions and does NOT diagnose disease.
It is a coarse, heuristic pre-filter that estimates whether an uploaded
image contains enough skin-like content to be worth sending to the
ResNet-50 disease classifier. Document it as a "preliminary
skin-content screening gate," not a lesion detector.

LIMITATIONS (state these explicitly in the thesis):
Because this is a color-based heuristic, it can produce false positives
(skin-toned backgrounds — walls, wood, sand) and false negatives
(heavily inflamed, discolored, or scaled lesions that no longer match
typical skin-tone ranges). Lighting, pigmentation, and image quality
all affect accuracy.

DESIGN — two detectors combined with OR:
  - YCrCb: the conventional skin-tone heuristic.
  - HSV:   a looser, red/orange-hue-leaning detector added specifically
           to reduce false negatives on erythematous / inflamed lesions
           (psoriasis, dermatitis, rosacea often present this way).
OR-combining favors recall over precision, which is the right tradeoff
for a pre-classifier gate: a false positive just gets passed on to
ResNet-50 anyway, while a false negative silently blocks a real lesion
photo before it's ever classified.

TODO BEFORE FINALIZING: the HSV bounds and SKIN_PIXEL_THRESHOLD below
are literature defaults, not tuned to this dataset. HSV in particular
tends to be broad and can inflate false positives if left unvalidated.
Validate/adjust both against the actual 2,400-image dataset (or a
labeled validation subset) before relying on them.
"""

import numpy as np
from PIL import Image

# ------------------------------------------------------------
# YCrCb thresholds (conventional skin-tone range)
# ------------------------------------------------------------
Y_MIN, Y_MAX = 0, 255
CR_MIN, CR_MAX = 135, 180
CB_MIN, CB_MAX = 85, 135

# ------------------------------------------------------------
# HSV thresholds — literature default, NOT yet validated on this
# dataset. Treat as a starting point only (see module TODO above).
# ------------------------------------------------------------
H_MIN, H_MAX = 0, 50
S_MIN, S_MAX = 20, 255
V_MIN, V_MAX = 40, 255

# ------------------------------------------------------------
# Minimum fraction of skin-like pixels required to pass the gate.
# Also needs empirical validation (see module TODO above).
# ------------------------------------------------------------
SKIN_PIXEL_THRESHOLD = 0.15


def _rgb_to_ycrcb(rgb_array: np.ndarray) -> np.ndarray:
    """Convert an RGB uint8 array to YCrCb (BT.601)."""
    rgb = rgb_array.astype(np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    y = 0.299 * r + 0.587 * g + 0.114 * b
    cr = (r - y) * 0.713 + 128
    cb = (b - y) * 0.564 + 128

    return np.stack([y, cr, cb], axis=-1)


def _rgb_to_hsv(rgb_array: np.ndarray) -> np.ndarray:
    """
    Convert an RGB uint8 array to HSV.

    Returns H in [0, 360), S in [0, 1], V in [0, 1].
    """
    rgb = rgb_array.astype(np.float32) / 255.0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    max_value = np.max(rgb, axis=-1)
    min_value = np.min(rgb, axis=-1)
    delta = max_value - min_value

    h = np.zeros_like(max_value)

    mask = (delta != 0) & (max_value == r)
    h[mask] = (60 * ((g[mask] - b[mask]) / delta[mask])) % 360

    mask = (delta != 0) & (max_value == g)
    h[mask] = 60 * ((b[mask] - r[mask]) / delta[mask] + 2)

    mask = (delta != 0) & (max_value == b)
    h[mask] = 60 * ((r[mask] - g[mask]) / delta[mask] + 4)

    s = np.zeros_like(max_value)
    nonzero_max = max_value != 0
    s[nonzero_max] = delta[nonzero_max] / max_value[nonzero_max]

    v = max_value

    return np.stack([h, s, v], axis=-1)


def estimate_skin_ratio(image: Image.Image) -> float:
    """
    Estimate the fraction of the image that is skin-like, combining
    the YCrCb and HSV detectors with OR — either detector counting a
    pixel as skin-like is enough. See module docstring for rationale.
    """
    small = image.convert("RGB").resize((128, 128))
    rgb_array = np.array(small)

    ycrcb = _rgb_to_ycrcb(rgb_array)
    y, cr, cb = ycrcb[..., 0], ycrcb[..., 1], ycrcb[..., 2]
    ycrcb_mask = (
        (y >= Y_MIN) & (y <= Y_MAX) &
        (cr >= CR_MIN) & (cr <= CR_MAX) &
        (cb >= CB_MIN) & (cb <= CB_MAX)
    )

    hsv = _rgb_to_hsv(rgb_array)
    h, s, v = hsv[..., 0], hsv[..., 1] * 255, hsv[..., 2] * 255
    hsv_mask = (
        (h >= H_MIN) & (h <= H_MAX) &
        (s >= S_MIN) & (s <= S_MAX) &
        (v >= V_MIN) & (v <= V_MAX)
    )

    combined_mask = ycrcb_mask | hsv_mask
    return float(combined_mask.mean())


def looks_like_skin(image: Image.Image) -> bool:
    """
    Preliminary skin-content screening gate. Returns True when the
    estimated skin-like pixel ratio meets SKIN_PIXEL_THRESHOLD.

    Heuristic pre-filter only — does not diagnose or classify disease.
    See module docstring for limitations.
    """
    return estimate_skin_ratio(image) >= SKIN_PIXEL_THRESHOLD