"""
utils/ocr.py — OCR module for Indian number plates.

PlateReader.read() accepts two input types:
  - numpy array  → used as-is (single image passed to PaddleOCR)
  - dict         → output of preprocess_plate(); iterates all variants
                   and returns the first valid plate found

PaddleOCR v3+ API notes
------------------------
The v3 release (paddleocr >= 3.0) broke several constructor arguments:
  REMOVED : use_gpu, use_angle_cls, show_log, lang
  NEW     : device="cpu"/"gpu"   (angle cls and English are on by default)

This module auto-detects which API generation is installed and builds
the reader accordingly, so it works on both v2 and v3.

The validation / fix_characters / noise-extraction logic is unchanged.
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

STANDARD_PATTERN = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$")
BH_PATTERN       = re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$")
_PLATE_RE        = re.compile(r"[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}")
_BH_RE           = re.compile(r"[0-9]{2}BH[0-9]{4}[A-Z]{1,2}")

LETTER_POS   = {0, 1, 4, 5}
DIGIT_POS    = {2, 3, 6, 7, 8, 9}
LETTER_FIXES = {"0": "O", "1": "I", "l": "I", "8": "B", "5": "S"}
DIGIT_FIXES  = {"O": "0", "I": "1", "l": "1", "B": "8", "S": "5"}


# ---------------------------------------------------------------------------
# Post-processing helpers  (unchanged)
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
               .replace(" ", "").replace("-", "")
               .replace(".", "").replace(":", "").replace(",", ""))


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


def _extract_plate_from_noise(noisy: str) -> Optional[str]:
    """Find a valid Indian plate buried anywhere inside a noisy string."""
    for pattern in (_BH_RE, _PLATE_RE):
        m = pattern.search(noisy)
        if m:
            candidate = fix_characters(m.group())
            result = validate_plate(candidate)
            if result:
                return result
    for length in (10, 9, 8):
        for start in range(len(noisy) - length + 1):
            window = noisy[start : start + length]
            fixed  = fix_characters(window)
            result = validate_plate(fixed)
            if result:
                return result
    return None


# ---------------------------------------------------------------------------
# PaddleOCR version detection and reader factory
# ---------------------------------------------------------------------------

def _detect_paddle_api_version() -> int:
    """
    Return 3 if paddleocr >= 3.0 is installed (new API), else 2 (old API).

    Strategy (most-reliable first):
    1. Check paddleocr.__version__ directly.
    2. Walk the full MRO to collect all constructor params — v3 uses
       inheritance heavily so 'use_gpu' / 'device' may live in a base class.
    3. Fall back to 2 if anything goes wrong.
    """
    try:
        import paddleocr
        ver_str = getattr(paddleocr, "__version__", "") or ""
        major = int(ver_str.split(".")[0]) if ver_str and ver_str[0].isdigit() else 0
        if major >= 3:
            return 3
        if major == 2:
            return 2
    except Exception:
        pass

    # Fallback: inspect full MRO for 'use_gpu' presence
    try:
        import inspect
        from paddleocr import PaddleOCR
        all_params: set = set()
        for cls in type.mro(PaddleOCR):
            try:
                all_params.update(inspect.signature(cls.__init__).parameters.keys())
            except (ValueError, TypeError):
                continue
        if "use_gpu" not in all_params:
            return 3
        return 2
    except Exception:
        return 2


def _make_paddle_reader(gpu: bool):
    """
    Construct a PaddleOCR instance compatible with the installed version.

    v2 constructor: PaddleOCR(use_angle_cls, lang, use_gpu, show_log)
    v3 constructor: PaddleOCR(device)   — angle cls + English are defaults

    A runtime ValueError on unknown args triggers an automatic retry with
    the opposite API so a wrong static detection never hard-crashes.
    """
    import os
    # Suppress PaddleOCR's "checking connectivity" banner on startup
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

    from paddleocr import PaddleOCR

    api_ver = _detect_paddle_api_version()

    def _try_v3():
        return PaddleOCR(device="gpu" if gpu else "cpu")

    def _try_v2():
        return PaddleOCR(
            use_angle_cls = True,
            lang          = "en",
            use_gpu       = gpu,
            show_log      = False,
        )

    if api_ver >= 3:
        try:
            return _try_v3()
        except (TypeError, ValueError):
            # Static detection was wrong; fall back to v2
            return _try_v2()
    else:
        try:
            return _try_v2()
        except (TypeError, ValueError):
            # Static detection was wrong; fall back to v3
            return _try_v3()


# ---------------------------------------------------------------------------
# Result parsing — handles both v2 and v3 output shapes
# ---------------------------------------------------------------------------

def _parse_paddle_results(raw) -> list:
    """
    Normalise PaddleOCR output to a flat list of (box, text, conf) triples.

    v2 output structure:
        [ [ [box_quad, (text, conf)], ... ] ]   ← page-wrapped list
    v3 output structure:
        Same page-wrapped list, but entries may also be dicts or objects.
    In both versions raw is None (not []) when nothing is detected.

    Returns [] when raw is None or contains nothing usable.
    """
    if raw is None:
        return []

    parsed = []
    for page in raw:
        if page is None:
            continue
        for entry in page:
            try:
                # Standard list/tuple entry: [box, (text, conf)]
                if isinstance(entry, (list, tuple)) and len(entry) == 2:
                    box      = entry[0]
                    text_obj = entry[1]
                    if isinstance(text_obj, (list, tuple)) and len(text_obj) == 2:
                        text = str(text_obj[0])
                        conf = float(text_obj[1])
                    elif hasattr(text_obj, "text"):
                        # v3 object-style result
                        text = str(text_obj.text)
                        conf = float(getattr(text_obj, "score", 1.0))
                    else:
                        continue
                    parsed.append((box, text, conf))

                # v3 dict-style entry: {"bbox": ..., "text": ..., "score": ...}
                elif isinstance(entry, dict):
                    box  = entry.get("bbox") or entry.get("box")
                    text = str(entry.get("text", ""))
                    conf = float(entry.get("score", entry.get("conf", 1.0)))
                    if box is not None and text:
                        parsed.append((box, text, conf))

            except Exception:
                continue

    return parsed


def _ensure_bgr(img: np.ndarray) -> np.ndarray:
    """PaddleOCR expects BGR; convert grayscale if needed."""
    if img is None:
        return img
    if len(img.shape) == 2:
        import cv2
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


# ---------------------------------------------------------------------------
# Internal: run OCR on a single numpy image
# ---------------------------------------------------------------------------

def _ocr_single(img: np.ndarray, reader, min_conf: float) -> tuple:
    """
    Run PaddleOCR on one image array.
    Returns (validated_plate_or_None, avg_confidence).

    Strategy:
    1. Try each individual OCR box standalone (catches clean reads among noisy ones).
    2. Try the full merged string with direct validation.
    3. Try _extract_plate_from_noise() on the merged string.
    """
    if not isinstance(img, np.ndarray):
        return None, 0.0

    img_bgr = _ensure_bgr(img)

    try:
        # v2 API — cls= enables angle classification
        raw = reader.ocr(img_bgr, cls=True)
    except TypeError:
        # v3 removed the cls= argument; angle cls is always on
        raw = reader.ocr(img_bgr)

    results = _parse_paddle_results(raw)
    results = [r for r in results if r[2] >= min_conf]

    if not results:
        return None, 0.0

    avg_conf = sum(r[2] for r in results) / len(results)

    # --- Strategy 1: per-box ---
    for _box, text, conf in results:
        norm = normalise_raw(text)
        if len(norm) < 6:
            continue
        plate = validate_plate(fix_characters(norm))
        if plate:
            return plate, conf
        plate = _extract_plate_from_noise(norm)
        if plate:
            return plate, conf

    # --- Strategy 2: merge boxes top-to-bottom, direct validate ---
    try:
        merged = "".join(
            t for _, t, _ in
            sorted(results, key=lambda r: min(pt[1] for pt in r[0]))
        )
    except (TypeError, IndexError):
        # Fallback if box coords have unexpected shape
        merged = "".join(t for _, t, _ in results)

    norm = normalise_raw(merged)

    if len(norm) >= 8:
        plate = validate_plate(fix_characters(norm))
        if plate:
            return plate, avg_conf

        # --- Strategy 3: sliding-window noise extraction ---
        plate = _extract_plate_from_noise(norm)
        if plate:
            return plate, avg_conf

    return None, 0.0


# ---------------------------------------------------------------------------
# PlateReader
# ---------------------------------------------------------------------------

class PlateReader:
    """
    Wrapper around PaddleOCR with full Indian plate post-processing.
    Compatible with PaddleOCR v2 and v3.

        reader = PlateReader(gpu=False)
        plate  = reader.read(crop)                    # raw numpy array
        plate  = reader.read(preprocess_plate(crop))  # dict of variants
    """

    def __init__(self, gpu: bool = True, languages: list = None):
        # languages= accepted for API compat with old EasyOCR callers; ignored.
        _ = languages
        self.reader = _make_paddle_reader(gpu)

    def read(
        self,
        crop_or_variants: Union[np.ndarray, dict],
        min_conf: float = 0.15,
        detail: bool    = False,
    ) -> Optional[str]:
        """
        Run OCR and return a validated plate string, or None.

        Args:
            crop_or_variants: numpy array OR dict from preprocess_plate().
            min_conf:         Minimum per-detection confidence to keep.
            detail:           If True, return (plate, conf) tuple.
        """
        if isinstance(crop_or_variants, dict):
            images = list(crop_or_variants.values())
        elif isinstance(crop_or_variants, np.ndarray):
            images = [crop_or_variants]
        else:
            return (None, 0.0) if detail else None

        best_plate = None
        best_conf  = 0.0

        for img in images:
            plate, conf = _ocr_single(img, self.reader, min_conf)
            if plate:
                best_plate = plate
                best_conf  = conf
                break

        return (best_plate, best_conf) if detail else best_plate


# ---------------------------------------------------------------------------
# Convenience one-shot function
# ---------------------------------------------------------------------------

def read_plate(
    crop_or_variants: Union[np.ndarray, dict],
    gpu: bool       = True,
    min_conf: float = 0.15,
) -> Optional[str]:
    """One-shot helper. For repeated use, keep a PlateReader instance."""
    reader = PlateReader(gpu=gpu)
    return reader.read(crop_or_variants, min_conf=min_conf)
