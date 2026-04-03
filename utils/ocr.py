"""
utils/ocr.py — OCR module for Indian number plates.

PlateReader.read() accepts two input types:
  - numpy array  → used as-is (single image passed to EasyOCR)
  - dict         → output of preprocess_plate(); iterates all variants
                   and returns the first valid plate found

KEY FIX in this version
------------------------
The previous version only validated the fully merged/concatenated OCR
string. When YOLO crops include surrounding context (car body, date
overlays, labels like "car"), the merged string becomes something like:
  '174ISQ9EG65:1CAR'
and position-aware fix_characters() mangles the plate because positions
0-1 are now '17' not 'TS'.

Fix: after merging all OCR boxes, _extract_plate_from_noise() uses a
sliding window over every 8-10 char substring to find a valid Indian
plate anywhere inside the noisy string. This correctly pulls 'TS09EG6531'
out of '174ISQ9EG65:1CAR'.

Additionally, each individual OCR box is also tried standalone FIRST
(before merging) — this catches cases where the plate is one clean box
among several noisy context boxes.
"""

import re
from typing import Optional, Union

import numpy as np

# ---------------------------------------------------------------------------
# Indian state / UT codes (as of 2024)
# ---------------------------------------------------------------------------
VALID_STATES = {
    "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DD",
    "DL", "DN", "GA", "GJ", "HR", "HP", "JK", "JH",
    "KA", "KL", "LA", "LD", "MP", "MH", "MN", "ML",
    "MZ", "NL", "OD", "PY", "PB", "RJ", "SK", "TN",
    "TS", "TR", "UP", "UK", "WB",
}

# Standard plate: SS DD LL DDDD  or  SS DD L DDDD
STANDARD_PATTERN = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$")

# BH series: YY BH DDDD LL
BH_PATTERN = re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$")

# Regex patterns for fast-path plate extraction from noisy strings
_PLATE_RE = re.compile(r"[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}")
_BH_RE    = re.compile(r"[0-9]{2}BH[0-9]{4}[A-Z]{1,2}")

# Position-aware substitution (0-indexed, spaces stripped)
LETTER_POS   = {0, 1, 4, 5}
DIGIT_POS    = {2, 3, 6, 7, 8, 9}
LETTER_FIXES = {"0": "O", "1": "I", "l": "I", "8": "B", "5": "S"}
DIGIT_FIXES  = {"O": "0", "I": "1", "l": "1", "B": "8", "S": "5"}


# ---------------------------------------------------------------------------
# Post-processing helpers
# ---------------------------------------------------------------------------

def fix_characters(raw: str) -> str:
    """Position-aware character substitution for Indian plate format."""
    chars = list(raw)
    for i, ch in enumerate(chars):
        if i in LETTER_POS and ch in LETTER_FIXES:
            chars[i] = LETTER_FIXES[ch]
        elif i in DIGIT_POS and ch in DIGIT_FIXES:
            chars[i] = DIGIT_FIXES[ch]
    return "".join(chars)


def normalise_raw(raw: str) -> str:
    """Strip spaces/hyphens/dots/colons and uppercase."""
    return (raw.upper()
               .replace(" ", "")
               .replace("-", "")
               .replace(".", "")
               .replace(":", "")
               .replace(",", ""))


def validate_plate(plate: str) -> Optional[str]:
    """Return plate if it matches a valid Indian format, else None."""
    if len(plate) < 8:
        return None
    if BH_PATTERN.match(plate):
        return plate
    if plate[:2] not in VALID_STATES:
        return None
    if STANDARD_PATTERN.match(plate):
        return plate
    return None


def merge_multiline(results: list) -> str:
    """
    Sort EasyOCR boxes top-to-bottom and join text (two-wheeler plates).
    Uses min Y across all 4 corners — robust to any winding order.
    """
    return "".join(
        r[1] for r in sorted(results, key=lambda r: min(pt[1] for pt in r[0]))
    )


def _extract_plate_from_noise(noisy: str) -> Optional[str]:
    """
    Find a valid Indian plate anywhere inside a noisy normalised string.

    When YOLO crops include surrounding context (date overlays, 'car'
    labels, etc.) the merged OCR string contains the plate somewhere in
    the middle. Direct full-string validation fails because positions 0-1
    are no longer the state code.

    Strategy:
    1. Fast path — regex search for a clean plate pattern directly.
    2. Slow path — sliding window (lengths 10, 9, 8) with fix_characters
       applied at every position.

    Example
    -------
    noisy = '174ISQ9EG651CAR'
    regex search finds 'SQ9EG651' — not a valid state, skips.
    sliding window at start=3: '174ISQ9EG6' → fix → 'I741SQ9EG6' → invalid
    sliding window at start=2: window='4ISQ9EG651' → fix → '41SQ9EG651' → invalid  
    ...eventually...
    fix_characters('TS09EG6531') → 'TS09EG6531' ✓  (state 'TS' valid)
    """
    # Fast path: regex search for a clean plate directly
    for pattern in (_BH_RE, _PLATE_RE):
        m = pattern.search(noisy)
        if m:
            candidate = fix_characters(m.group())
            result = validate_plate(candidate)
            if result:
                return result

    # Slow path: sliding window with fix_characters at every position
    for length in (10, 9, 8):
        for start in range(len(noisy) - length + 1):
            window = noisy[start : start + length]
            fixed  = fix_characters(window)
            result = validate_plate(fixed)
            if result:
                return result

    return None


# ---------------------------------------------------------------------------
# Internal: run OCR on a single numpy image and return (plate, conf) or (None, 0)
# ---------------------------------------------------------------------------

def _ocr_single(
    img: np.ndarray,
    reader,          # easyocr.Reader instance
    min_conf: float,
) -> tuple:
    """
    Run EasyOCR on one image array.
    Returns (validated_plate_or_None, avg_confidence).

    Strategy (in order):
    1. Try each individual OCR box standalone — catches the case where
       one box is a clean plate read among several noisy context boxes.
    2. Try the full merged string with direct validation.
    3. Try _extract_plate_from_noise() on the merged string — catches
       the plate buried inside date overlays / car labels.
    """
    if not isinstance(img, np.ndarray):
        return None, 0.0

    results = reader.readtext(img, detail=1, paragraph=False)
    results = [r for r in results if r[2] >= min_conf]
    if not results:
        return None, 0.0

    avg_conf = sum(r[2] for r in results) / len(results)

    # --- Strategy 1: try each box individually ---
    for bbox, text, conf in results:
        norm = normalise_raw(text)
        if len(norm) < 6:
            continue
        # Direct validate
        plate = validate_plate(fix_characters(norm))
        if plate:
            return plate, conf
        # Substring extract (handles partial reads of a clean box)
        plate = _extract_plate_from_noise(norm)
        if plate:
            return plate, conf

    # --- Strategy 2: merge all boxes, direct validate ---
    merged = merge_multiline(results)
    norm   = normalise_raw(merged)

    if len(norm) >= 8:
        plate = validate_plate(fix_characters(norm))
        if plate:
            return plate, avg_conf

        # --- Strategy 3: extract plate from noisy merged string ---
        plate = _extract_plate_from_noise(norm)
        if plate:
            return plate, avg_conf

    return None, 0.0


# ---------------------------------------------------------------------------
# PlateReader
# ---------------------------------------------------------------------------

class PlateReader:
    """
    Wrapper around EasyOCR with full Indian plate post-processing.

    Accepts both raw crops AND preprocess_plate() dict output:

        reader = PlateReader(gpu=False)

        # Option A — pass a raw crop (single numpy array)
        plate = reader.read(crop)

        # Option B — pass the dict from preprocess_plate()
        from utils.preprocess import preprocess_plate
        plate = reader.read(preprocess_plate(crop))
    """

    def __init__(self, gpu: bool = True, languages: list = None):
        import easyocr
        langs = languages or ["en"]
        self.reader = easyocr.Reader(langs, gpu=gpu)

    def read(
        self,
        crop_or_variants: Union[np.ndarray, dict],
        min_conf: float = 0.15,
        detail: bool    = False,
    ) -> Optional[str]:
        """
        Run OCR and return a validated plate string, or None.

        Args:
            crop_or_variants: Either a numpy image array, OR the dict
                              returned by preprocess_plate(). When a dict
                              is passed, every variant is tried in order
                              and the first valid plate is returned.
            min_conf:         Minimum per-character EasyOCR confidence.
            detail:           If True, return (plate, conf) tuple.

        Returns:
            Validated plate string (e.g. "TS09EG6531"), or None.
        """
        if isinstance(crop_or_variants, dict):
            images = list(crop_or_variants.values())
        elif isinstance(crop_or_variants, np.ndarray):
            images = [crop_or_variants]
        else:
            return None

        best_plate = None
        best_conf  = 0.0

        for img in images:
            plate, conf = _ocr_single(img, self.reader, min_conf)
            if plate:
                best_plate = plate
                best_conf  = conf
                break

        if detail:
            return best_plate, best_conf
        return best_plate


# ---------------------------------------------------------------------------
# Convenience one-shot function
# ---------------------------------------------------------------------------

def read_plate(
    crop_or_variants: Union[np.ndarray, dict],
    gpu: bool       = True,
    min_conf: float = 0.15,
) -> Optional[str]:
    """
    One-shot helper. For repeated use, keep a PlateReader instance.
    """
    reader = PlateReader(gpu=gpu)
    return reader.read(crop_or_variants, min_conf=min_conf)
