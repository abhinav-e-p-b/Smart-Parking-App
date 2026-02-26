"""
detection.py - License plate detection and OCR utilities
Supports Indian number plates (10-char: MH12AB1234) and legacy formats.
"""

import cv2
import numpy as np
import string
import logging
import re
from ultralytics import YOLO
import easyocr
import torch
import random

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Model loading (lazy, singleton)
# ─────────────────────────────────────────────
_plate_detector = None
_ocr_reader = None


def _get_detector() -> YOLO:
    global _plate_detector
    if _plate_detector is None:
        logger.info("Loading license plate detector model...")
        _plate_detector = YOLO("best.pt")
    return _plate_detector


def _get_reader() -> easyocr.Reader:
    global _ocr_reader
    if _ocr_reader is None:
        logger.info("Loading EasyOCR reader...")
        _ocr_reader = easyocr.Reader(['en'], gpu=False)  # set gpu=True if CUDA available
    return _ocr_reader


# ─────────────────────────────────────────────
# Character correction maps
# ─────────────────────────────────────────────
CHAR_TO_INT = {'O': '0', 'I': '1', 'J': '3', 'A': '4', 'G': '6', 'S': '5', 'B': '8', 'Z': '2'}
INT_TO_CHAR = {'0': 'O', '1': 'I', '3': 'J', '4': 'A', '6': 'G', '5': 'S', '8': 'B', '2': 'Z'}

# ─────────────────────────────────────────────
# Indian plate format patterns
# ─────────────────────────────────────────────
# Standard: MH12AB1234  (state)(district)(series)(number)
# BH-series: 22BH1234AA
# Old format: MH1234 (6 chars) — rare but exists
INDIAN_PLATE_PATTERNS = [
    re.compile(r'^[A-Z]{2}[0-9]{2}[A-Z]{1,3}[0-9]{4}$'),   # Standard: MH12AB1234 / MH12ABC1234
    re.compile(r'^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$'),           # BH-series: 22BH1234AA
    re.compile(r'^[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}$'),       # Exact 10-char standard
]


def _clean_ocr_text(text: str) -> str:
    """Strip spaces, hyphens, dots and uppercase."""
    return re.sub(r'[\s\-\.]', '', text.upper())


def _apply_corrections(text: str) -> str:
    """
    Apply position-aware character corrections for Indian plates.
    Pattern: LL DD L{1-3} DDDD
    Positions 0,1 = letters; 2,3 = digits; 4..n-4 = letters; last 4 = digits
    """
    if len(text) < 6:
        return text
    result = list(text)
    # State code (0,1) → must be letters
    for i in (0, 1):
        result[i] = INT_TO_CHAR.get(result[i], result[i])
    # District code (2,3) → must be digits
    for i in (2, 3):
        result[i] = CHAR_TO_INT.get(result[i], result[i])
    # Last 4 → must be digits
    for i in range(len(text) - 4, len(text)):
        result[i] = CHAR_TO_INT.get(result[i], result[i])
    # Middle characters → must be letters
    for i in range(4, len(text) - 4):
        result[i] = INT_TO_CHAR.get(result[i], result[i])
    return ''.join(result)


def _complies_format(text: str) -> bool:
    """
    Validate against known Indian plate patterns after basic correction attempt.
    More permissive than before — accepts 9 to 11 char plates.
    """
    if not (6 <= len(text) <= 11):
        return False
    corrected = _apply_corrections(text)
    for pattern in INDIAN_PLATE_PATTERNS:
        if pattern.match(corrected):
            return True
    return False


def _format_plate(text: str) -> str:
    """Apply corrections and return cleaned plate string."""
    return _apply_corrections(text)


# ─────────────────────────────────────────────
# Plate Detection
# ─────────────────────────────────────────────

def _preprocess_crop(crop: np.ndarray) -> np.ndarray:
    """Convert crop to grayscale + adaptive threshold for better OCR."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    # Upscale for better OCR
    scale = max(1, 200 // gray.shape[0])
    if scale > 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    # Adaptive threshold handles varied lighting better than fixed 64
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )
    return thresh


def detect_plate(frame: np.ndarray, n_passes: int = 5,
                 consistency_threshold: float = 0.6) -> np.ndarray | None:
    """
    Run YOLOv8 detection N times.
    YOLOv8 doesn't use Dropout, so we add slight augmentation jitter
    across passes instead to simulate stochastic behaviour.
    Only accept boxes seen in >= consistency_threshold fraction of passes.
    """
    detector = _get_detector()
    detection_counts: dict[tuple, int] = {}
    detection_boxes: dict[tuple, list[float]] = {}

    for i in range(n_passes):
        # Slight brightness/contrast jitter to simulate varied conditions
        if i > 0:
            alpha = random.uniform(0.85, 1.15)
            beta = random.randint(-15, 15)
            jittered = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
        else:
            jittered = frame

        results = detector(jittered, verbose=False, conf=0.4, iou=0.45)[0]

        for box in results.boxes.data.tolist():
            x1, y1, x2, y2, score, cls = box
            if score < 0.4:
                continue
            # Quantize to 20px grid to group nearby boxes
            key = (round(x1 / 20), round(y1 / 20),
                   round(x2 / 20), round(y2 / 20))
            detection_counts[key] = detection_counts.get(key, 0) + 1
            detection_boxes.setdefault(key, []).append([x1, y1, x2, y2, score])

    # Filter: keep only boxes seen in >= threshold fraction of passes
    stable_boxes = {
        k: v for k, v in detection_counts.items()
        if v / n_passes >= consistency_threshold
    }

    if not stable_boxes:
        return None

    # Use the most consistent detection; average its coordinates
    best_key = max(stable_boxes, key=stable_boxes.get)
    raw_boxes = detection_boxes[best_key]
    x1 = int(np.mean([b[0] for b in raw_boxes]))
    y1 = int(np.mean([b[1] for b in raw_boxes]))
    x2 = int(np.mean([b[2] for b in raw_boxes]))
    y2 = int(np.mean([b[3] for b in raw_boxes]))

    h, w = frame.shape[:2]
    x1 = max(0, min(w, x1))
    y1 = max(0, min(h, y1))
    x2 = max(0, min(w, x2))
    y2 = max(0, min(h, y2))

    if x2 <= x1 or y2 <= y1:
        return None

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    best_conf = stable_boxes[best_key] / n_passes
    logger.debug(f"Plate detected, consistency={best_conf:.2f}")
    return _preprocess_crop(crop)


# ─────────────────────────────────────────────
# OCR
# ─────────────────────────────────────────────

def read_plate(plate_crop: np.ndarray, n_variants: int = 5) -> tuple[str | None, float]:
    """
    Run OCR on N augmented variants of the plate crop.
    Returns the plate text only if a majority of variants agree.
    """
    reader = _get_reader()
    votes: dict[str, list[float]] = {}

    augmentations = [
        lambda img: img,                                                   # original
        lambda img: cv2.GaussianBlur(img, (3, 3), 0),                    # slight blur
        lambda img: cv2.resize(img, None, fx=1.5, fy=1.5,
                               interpolation=cv2.INTER_CUBIC),            # upscale
        lambda img: cv2.equalizeHist(img),                                # histogram equalize
        lambda img: cv2.dilate(img, np.ones((2, 2), np.uint8)),           # dilate
        lambda img: cv2.erode(img, np.ones((2, 2), np.uint8)),            # erode
        lambda img: cv2.medianBlur(img, 3),                               # median blur
    ]

    chosen = random.sample(augmentations, min(n_variants, len(augmentations)))

    for aug in chosen:
        try:
            variant = aug(plate_crop)
            detections = reader.readtext(variant, detail=1, paragraph=False)
            for (_, text, score) in detections:
                text = _clean_ocr_text(text)
                if len(text) < 4:
                    continue
                if _complies_format(text):
                    formatted = _format_plate(text)
                    votes.setdefault(formatted, []).append(score)
        except Exception as e:
            logger.debug(f"OCR augmentation failed: {e}")
            continue

    if not votes:
        return None, 0.0

    # Require majority vote
    majority = max(2, n_variants // 2 + 1)
    confident_plates = {
        plate: scores for plate, scores in votes.items()
        if len(scores) >= majority
    }

    if not confident_plates:
        # Fallback: return best single-vote result if confidence is high enough
        best = max(votes, key=lambda p: max(votes[p]))
        best_conf = max(votes[best])
        if best_conf >= 0.85:
            logger.debug(f"Fallback single-vote plate: {best} ({best_conf:.2f})")
            return best, best_conf
        return None, 0.0

    best = max(confident_plates, key=lambda p: sum(confident_plates[p]))
    avg_conf = sum(confident_plates[best]) / len(confident_plates[best])
    return best, avg_conf