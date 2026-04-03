"""
utils/preprocess.py — Image preprocessing for Indian number plate crops.

preprocess_plate(crop) returns a dict of named image variants.
Each caller iterates the dict, runs OCR on each variant, and picks
the first one that produces a valid plate reading.

FIX applied in this version
-----------------------------
- deskew() angle conversion bug: the original `if angle < -45: angle = 90 + angle`
  branch mapped OpenCV's (-90, 0] convention incorrectly near the boundary.
  OpenCV's minAreaRect returns the angle of the SHORTER side from horizontal,
  in the range (-90, 0]. The correct conversion to a signed skew angle is:
    • if angle < -45  → the rect is "standing up": true_angle = angle + 90
    • if angle >= -45 → the rect is "lying down":  true_angle = angle
  The old code did exactly this but the comment was misleading. The REAL bug
  was that `abs(angle) > max_angle` was checked AFTER conversion, but
  max_angle=45 was too generous — a plate legitimately rotated 44° was being
  "deskewed" in the wrong direction. Fix: clamp corrected angle to ±15° for
  realistic in-video skew, and use the proper two-step OpenCV convention.

Variants (ordered best-first):
  'gray'           — CLAHE-enhanced grayscale
  'deskewed'       — skew-corrected version of gray
  'sharp'          — sharpened grayscale
  'boosted'        — gray + edge overlay
  'otsu'           — Otsu binarisation
  'otsu_inv'       — Otsu inverted
  'adap'           — adaptive threshold
  'adap_inv'       — adaptive inverted
  'rot90_gray'     — 90° rotated gray (for sideways cameras)
  'rot180_gray'    — 180° rotated
  'rot270_gray'    — 270° rotated
  'rot90_deskewed' — 90° rotated then deskewed
  'rot270_deskewed'— 270° rotated then deskewed
  'rot90_otsu'     — 90° rotated + Otsu (last resort)
  'rot270_otsu'    — 270° rotated + Otsu (last resort)
"""

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Individual step functions
# ---------------------------------------------------------------------------

def upscale(img: np.ndarray, scale: float = 2.0) -> np.ndarray:
    h, w = img.shape[:2]
    return cv2.resize(img, (int(w * scale), int(h * scale)),
                      interpolation=cv2.INTER_CUBIC)


def to_gray(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def bilateral_denoise(gray: np.ndarray, d: int = 11, sigma: float = 17) -> np.ndarray:
    return cv2.bilateralFilter(gray, d, sigma, sigma)


def sharpen(img: np.ndarray) -> np.ndarray:
    kernel = np.array([[0, -1,  0],
                       [-1,  5, -1],
                       [0, -1,  0]])
    return cv2.filter2D(img, -1, kernel)


def adaptive_threshold(gray: np.ndarray, block_size: int = 31, c: int = 5) -> np.ndarray:
    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size, c,
    )


def adaptive_threshold_inv(gray: np.ndarray, block_size: int = 31, c: int = 5) -> np.ndarray:
    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        block_size, c,
    )


def otsu_threshold(gray: np.ndarray) -> np.ndarray:
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th


def otsu_threshold_inv(gray: np.ndarray) -> np.ndarray:
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return th


def morph_clean(binary: np.ndarray, k: int = 2) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    return cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)


# ---------------------------------------------------------------------------
# Deskew
# ---------------------------------------------------------------------------

def deskew(gray: np.ndarray, max_skew: float = 15.0) -> np.ndarray:
    """
    Correct small skew in a grayscale plate crop.

    OpenCV's minAreaRect returns an angle in (-90, 0]:
      - angle in [-45, 0)  → rect lies horizontally; skew = angle  (negative = CCW tilt)
      - angle in (-90, -45) → rect stands vertically; skew = angle + 90  (positive = CW tilt)

    We only correct skew within ±max_skew degrees.  Larger deviations are
    likely a 90°/180°/270° camera rotation, handled by try_rotations().

    FIX: Previous code used max_angle=45 which was too permissive and could
    apply a large unwanted rotation. Clamped to 15° for realistic plate skew.
    """
    # Threshold to get a binary mask of dark regions (text)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return gray

    h, w = gray.shape
    min_area = (h * w) * 0.001   # at least 0.1% of image
    max_area = (h * w) * 0.80    # at most 80% of image
    valid = [c for c in contours
             if min_area < cv2.contourArea(c) < max_area]

    if not valid:
        return gray

    all_pts = np.vstack(valid)
    rect    = cv2.minAreaRect(all_pts)
    angle   = rect[2]   # OpenCV returns angle in (-90, 0]

    # Convert OpenCV angle convention to signed skew angle
    # (-90, -45): rect is "vertical" → true skew = angle + 90  (small positive)
    # [-45,  0):  rect is "horizontal" → true skew = angle      (small negative)
    if angle < -45.0:
        skew_angle = angle + 90.0
    else:
        skew_angle = angle
    # skew_angle is now in roughly (-45, +45); realistic plate skew is < 15°

    if abs(skew_angle) < 0.5 or abs(skew_angle) > max_skew:
        return gray   # nothing to correct, or too large (rotation, not skew)

    centre = (w / 2.0, h / 2.0)
    M      = cv2.getRotationMatrix2D(centre, skew_angle, 1.0)
    rotated = cv2.warpAffine(
        gray, M, (w, h),
        flags      = cv2.INTER_CUBIC,
        borderMode = cv2.BORDER_REPLICATE,
    )
    return rotated


def rotate90(img: np.ndarray, k: int = 1) -> np.ndarray:
    """Rotate image 90*k degrees counter-clockwise."""
    return np.rot90(img, k)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def preprocess_plate(crop: np.ndarray) -> dict:
    """
    Run the full preprocessing pipeline on a plate crop.

    Args:
        crop: BGR or grayscale image (any size — upscaled internally).

    Returns:
        Ordered dict of {variant_name: image_array}.
        Pass each image to EasyOCR and stop at first valid plate reading.

    Variant order (best-first):
        Standard orientation variants first, then rotations.
        Deskewed variants are tried early because skew is the most
        common failure mode in portrait/parking-cam footage.
    """
    up    = upscale(crop, 2.0)
    gray  = to_gray(up)

    clahe         = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray_enhanced = clahe.apply(gray)

    # Deskewed version
    gray_deskewed = deskew(gray_enhanced)

    sharp   = sharpen(gray_enhanced)
    edges   = cv2.Canny(sharp, 50, 150)
    boosted = cv2.addWeighted(sharp, 0.8, edges, 0.2, 0)

    # Rotated variants (for sideways / inverted cameras)
    rot90  = rotate90(gray_enhanced, 1)
    rot180 = rotate90(gray_enhanced, 2)
    rot270 = rotate90(gray_enhanced, 3)

    # Deskew the most likely rotation candidates too
    rot90_deskewed  = deskew(rot90)
    rot270_deskewed = deskew(rot270)

    return {
        # --- Standard orientation, best preprocessing first ---
        "gray":            gray_enhanced,
        "deskewed":        gray_deskewed,
        "sharp":           sharp,
        "boosted":         boosted,
        "otsu":            otsu_threshold(sharp),
        "otsu_inv":        otsu_threshold_inv(sharp),
        "adap":            adaptive_threshold(sharp, 31, 5),
        "adap_inv":        adaptive_threshold_inv(sharp, 31, 5),
        # --- Rotated variants (handles portrait/sideways cameras) ---
        "rot90_gray":      rot90,
        "rot90_deskewed":  rot90_deskewed,
        "rot180_gray":     rot180,
        "rot270_gray":     rot270,
        "rot270_deskewed": rot270_deskewed,
        # --- Rotated + binarised (last resort) ---
        "rot90_otsu":      otsu_threshold(rot90),
        "rot270_otsu":     otsu_threshold(rot270),
    }
