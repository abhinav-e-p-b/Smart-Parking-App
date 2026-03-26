"""
utils/preprocess.py — Image preprocessing for Indian number plate crops.

preprocess_plate(crop) returns a dict of named image variants.
Each caller iterates the dict, runs OCR on each variant, and picks
the first one that produces a valid plate reading.

Key additions vs previous version
-----------------------------------
1. deskew()  — corrects skew angle using minAreaRect on the text mask.
               This fixes the "EasyOCR reads single characters" problem
               that occurs when plates appear at an angle in portrait
               video (phone/parking camera footage).

2. try_rotations() — when the standard pipeline fails, the crop is also
               tried at 90°/180°/270° rotations. This handles cameras
               mounted sideways or upside-down.

3. All rotation variants are included in the returned dict so the OCR
   caller automatically tries them without any changes to ocr.py.

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
# NEW: Deskew
# ---------------------------------------------------------------------------

def deskew(gray: np.ndarray, max_angle: float = 45.0) -> np.ndarray:
    """
    Correct skew in a grayscale plate crop.

    Detects the dominant text angle using minAreaRect on thresholded
    contours and rotates the image to horizontal.  Only corrects angles
    within ±max_angle degrees — larger angles are likely a rotation
    issue (handled by try_rotations) rather than skew.

    Returns the deskewed image (same size, black fill on borders).
    """
    # Threshold to get a binary mask of dark regions (text)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Find contours of text blobs
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return gray

    # Keep only reasonably sized contours (not tiny noise, not the whole image)
    h, w = gray.shape
    min_area = (h * w) * 0.001   # at least 0.1% of image
    max_area = (h * w) * 0.80    # at most 80% of image
    valid = [c for c in contours
             if min_area < cv2.contourArea(c) < max_area]

    if not valid:
        return gray

    # Combine all valid contours and fit a rotated bounding rect
    all_pts = np.vstack(valid)
    rect    = cv2.minAreaRect(all_pts)
    angle   = rect[2]   # OpenCV returns angle in (-90, 0]

    # Convert to a signed angle: positive = clockwise, negative = counter-clockwise
    if angle < -45:
        angle = 90 + angle   # e.g. -80 → +10
    # angle is now in range (-45, +45)

    if abs(angle) < 1.0 or abs(angle) > max_angle:
        return gray   # nothing to correct

    # Rotate around centre
    centre = (w / 2, h / 2)
    M      = cv2.getRotationMatrix2D(centre, angle, 1.0)
    rotated = cv2.warpAffine(
        gray, M, (w, h),
        flags       = cv2.INTER_CUBIC,
        borderMode  = cv2.BORDER_REPLICATE,
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
        "gray":           gray_enhanced,
        "deskewed":       gray_deskewed,
        "sharp":          sharp,
        "boosted":        boosted,
        "otsu":           otsu_threshold(sharp),
        "otsu_inv":       otsu_threshold_inv(sharp),
        "adap":           adaptive_threshold(sharp, 31, 5),
        "adap_inv":       adaptive_threshold_inv(sharp, 31, 5),
        # --- Rotated variants (handles portrait/sideways cameras) ---
        "rot90_gray":     rot90,
        "rot90_deskewed": rot90_deskewed,
        "rot180_gray":    rot180,
        "rot270_gray":    rot270,
        "rot270_deskewed":rot270_deskewed,
        # --- Rotated + binarised (last resort) ---
        "rot90_otsu":     otsu_threshold(rot90),
        "rot270_otsu":    otsu_threshold(rot270),
    }
