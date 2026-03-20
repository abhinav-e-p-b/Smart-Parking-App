"""
utils/ocr.py — OCR module for Indian number plates.
"""

import re
from typing import Optional, Union
import numpy as np

VALID_STATES = {
    "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DD",
    "DL", "DN", "GA", "GJ", "HR", "HP", "JK", "JH",
    "KA", "KL", "LA", "LD", "MP", "MH", "MN", "ML",
    "MZ", "NL", "OD", "PY", "PB", "RJ", "SK", "TN",
    "TS", "TR", "UP", "UK", "WB",
}

STANDARD_PATTERN = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$")
BH_PATTERN       = re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$")

LETTER_POS   = {0, 1, 4, 5}
DIGIT_POS    = {2, 3, 6, 7, 8, 9}
LETTER_FIXES = {"0": "O", "1": "I", "l": "I", "8": "B", "5": "S"}
DIGIT_FIXES  = {"O": "0", "I": "1", "l": "1", "B": "8", "S": "5"}


def fix_characters(raw: str) -> str:
    chars = list(raw)
    for i, ch in enumerate(chars):
        if i in LETTER_POS and ch in LETTER_FIXES:
            chars[i] = LETTER_FIXES[ch]
        elif i in DIGIT_POS and ch in DIGIT_FIXES:
            chars[i] = DIGIT_FIXES[ch]
    return "".join(chars)


def normalise_raw(raw: str) -> str:
    return raw.upper().replace(" ", "").replace("-", "").replace(".", "")


def validate_plate(plate: str) -> Optional[str]:
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
    return "".join(r[1] for r in sorted(results, key=lambda r: r[0][0][1]))


def _ocr_single(img: np.ndarray, reader, min_conf: float) -> tuple:
    if not isinstance(img, np.ndarray):
        return None, 0.0
    results  = reader.readtext(img, detail=1, paragraph=False)
    results  = [r for r in results if r[2] >= min_conf]
    if not results:
        return None, 0.0
    raw      = merge_multiline(results)
    raw      = normalise_raw(raw)
    avg_conf = sum(r[2] for r in results) / len(results)
    if len(raw) < 6:
        return None, 0.0
    fixed = fix_characters(raw)
    plate = validate_plate(fixed)
    return plate, avg_conf


class PlateReader:
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
        if isinstance(crop_or_variants, dict):
            images = list(crop_or_variants.values())
        elif isinstance(crop_or_variants, np.ndarray):
            images = [crop_or_variants]
        else:
            return None

        best_plate, best_conf = None, 0.0
        for img in images:
            plate, conf = _ocr_single(img, self.reader, min_conf)
            if plate:
                best_plate, best_conf = plate, conf
                break

        if detail:
            return best_plate, best_conf
        return best_plate


def read_plate(crop_or_variants, gpu: bool = True, min_conf: float = 0.15) -> Optional[str]:
    return PlateReader(gpu=gpu).read(crop_or_variants, min_conf=min_conf)
