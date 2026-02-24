"""
detection.py - License plate detection and OCR utilities
"""

import cv2
import numpy as np
import string
import logging
from ultralytics import YOLO
import easyocr
import re

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
        _plate_detector = YOLO("license_plate_detector.pt")
    return _plate_detector


def _get_reader() -> easyocr.Reader:
    global _ocr_reader
    if _ocr_reader is None:
        logger.info("Loading EasyOCR reader...")
        _ocr_reader = easyocr.Reader(['en'], gpu=True)
    return _ocr_reader


# ─────────────────────────────────────────────
# Character correction maps (UK-style plates)
# Adjust for your country's plate format
# ─────────────────────────────────────────────
CHAR_TO_INT = {'O': '0', 'I': '1', 'J': '3', 'A': '4', 'G': '6', 'S': '5'}
INT_TO_CHAR = {v: k for k, v in CHAR_TO_INT.items()}


def detect_plate(frame: np.ndarray) -> np.ndarray | None:
    """
    Run the YOLOv8 license plate detector on a single frame.

    Returns:
        Cropped grayscale + thresholded plate image, or None if not found.
    """
    detector = _get_detector()
    results = detector(frame, verbose=False)[0]

    best_conf = 0.0
    best_crop = None

    for box in results.boxes.data.tolist():
        x1, y1, x2, y2, score, _ = box
        if score > best_conf:
            best_conf = score
            crop = frame[int(y1):int(y2), int(x1):int(x2)]
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 64, 255, cv2.THRESH_BINARY_INV)
            best_crop = thresh

    if best_crop is None:
        return None

    logger.debug(f"Plate detected with detector confidence {best_conf:.2f}")
    return best_crop


'''def _complies_format(text: str) -> bool:
    """
    Validate license plate format.
    Default: 7-char UK-style (e.g. AB12CDE).
    Customize this for your country's format.
    """
    if len(text) != 7:
        return False
    uppers = string.ascii_uppercase
    digits = string.digits
    return (
        (text[0] in uppers or text[0] in INT_TO_CHAR) and
        (text[1] in uppers or text[1] in INT_TO_CHAR) and
        (text[2] in digits or text[2] in CHAR_TO_INT) and
        (text[3] in digits or text[3] in CHAR_TO_INT) and
        (text[4] in uppers or text[4] in INT_TO_CHAR) and
        (text[5] in uppers or text[5] in INT_TO_CHAR) and
        (text[6] in uppers or text[6] in INT_TO_CHAR)
    )'''
def _complies_format(text: str) -> bool:
    """
    Validate license plate format.
    Indian format: 2 letters + 2 digits + 2 letters + 4 digits = 10 chars
    Example: MH12AB1234
    Allows OCR look-alike chars (O↔0, I↔1, etc.) before correction is applied.
    """
    if len(text) != 10:
        return False

    uppers = string.ascii_uppercase
    digits = string.digits

    return (
        # State code — positions 0, 1 must be letters or letter-substitutable
        (text[0] in uppers or text[0] in INT_TO_CHAR) and
        (text[1] in uppers or text[1] in INT_TO_CHAR) and

        # District code — positions 2, 3 must be digits or digit-substitutable
        (text[2] in digits or text[2] in CHAR_TO_INT) and
        (text[3] in digits or text[3] in CHAR_TO_INT) and

        # Series — positions 4, 5 must be letters or letter-substitutable
        (text[4] in uppers or text[4] in INT_TO_CHAR) and
        (text[5] in uppers or text[5] in INT_TO_CHAR) and

        # Unique number — positions 6–9 must be digits or digit-substitutable
        (text[6] in digits or text[6] in CHAR_TO_INT) and
        (text[7] in digits or text[7] in CHAR_TO_INT) and
        (text[8] in digits or text[8] in CHAR_TO_INT) and
        (text[9] in digits or text[9] in CHAR_TO_INT)
    )


'''def _format_plate(text: str) -> str:
    """Apply character substitution mapping to correct common OCR errors."""
    mapping = {
        0: INT_TO_CHAR, 1: INT_TO_CHAR,       # positions 0,1 must be letters
        2: CHAR_TO_INT, 3: CHAR_TO_INT,        # positions 2,3 must be digits
        4: INT_TO_CHAR, 5: INT_TO_CHAR, 6: INT_TO_CHAR  # positions 4-6 must be letters
    }
    result = ""
    for i, ch in enumerate(text):
        result += mapping[i].get(ch, ch)
    return result'''
    
def _format_plate(text: str) -> str:
    """
    Apply character substitution for Indian plate format.
    Positions 0,1,4,5  → must be letters (apply INT_TO_CHAR)
    Positions 2,3,6-9  → must be digits  (apply CHAR_TO_INT)
    """
    letter_positions = {0, 1, 4, 5}
    digit_positions  = {2, 3, 6, 7, 8, 9}

    result = ""
    for i, ch in enumerate(text):
        if i in letter_positions:
            result += INT_TO_CHAR.get(ch, ch)
        elif i in digit_positions:
            result += CHAR_TO_INT.get(ch, ch)
        else:
            result += ch
    return result


def read_plate(plate_crop: np.ndarray) -> tuple[str | None, float]:
    """
    Run EasyOCR on the plate crop, validate and correct the text.

    Returns:
        (plate_text, confidence) or (None, 0.0) if no valid reading found.
    """
    reader = _get_reader()
    detections = reader.readtext(plate_crop)

    for (_, text, score) in detections:
        text = text.upper().replace(" ", "").replace("-", "")
        if _complies_format(text):
            formatted = _format_plate(text)
            logger.debug(f"Valid plate: {formatted} (score={score:.2f})")
            return formatted, score

    return None, 0.0
